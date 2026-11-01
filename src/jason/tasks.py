import asyncio
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from .config import Settings
from .store import Store
from .policy import Policy, PolicyError
from .quota import Quota, QuotaWait
from .models import Gemini, TOOL_FIELDS, ProviderTransient
from .workspace import Workspace
from .shells import Shells
from .browser import Browser
from .apps import Apps
from .browser import origin

class Runtime:
    def __init__(self, settings, state, emit=print, stream_output=None):
        self.s,self.emit=settings,emit
        self.stream_output=stream_output
        self.store=Store(Path(state)/"state.db")
        self.policy=Policy(settings.root,settings.public_demo,any_folder=settings.any_folder)
        self.workspace=Workspace(self.policy,Path(state)/"backups")
        self.shells=Shells(self.policy.root)
        self.browser=Browser(settings.origins)
        self.config_origins=set(self.browser.origins)
        self.browser.authorize_origin=lambda destination: destination in self.config_origins or self.store.allowed('origin',hashlib.sha256(destination.encode()).hexdigest())
        self.apps=Apps(self.policy.root)
        self.quota=Quota(self.store,{settings.lite_model:settings.limits("lite"),settings.flash_model:settings.limits("flash")})
        key=os.getenv("GEMINI_API_KEY","")
        self.model=Gemini(settings,self.quota,self.policy,key) if key and settings.ai_ready else None
        self.jobs={}
        self.approvals={}
        self.history=[]
        self.action_lock=asyncio.Lock()
        self.paused=asyncio.Event()
        self.paused.set()
        self.closed=False
    async def require(self,kind,identity,description):
        if self.store.allowed(kind,identity): return
        aid=uuid.uuid4().hex[:8]
        future=asyncio.get_running_loop().create_future()
        self.approvals[aid]=(kind,identity,future)
        owner=next((tid for tid,job in self.jobs.items() if job is asyncio.current_task()),None)
        record=next((r for r in self.store.tasks() if r['id']==owner),None)
        if record: self.store.task(owner,'WAITING_FOR_APPROVAL',record['summary'])
        self.emit(f"Approval {aid}: {description}\nUse /approve {aid} or /deny {aid}.")
        try:
            if not await future: raise PolicyError("User denied action.")
            if not self.store.allowed(kind,identity): raise PolicyError("Grant revoked.")
        finally:
            self.approvals.pop(aid,None)
            if record: self.store.task(owner,'RUNNING',record['summary'])
    def approve(self,aid,yes=True):
        kind,identity,future=self.approvals[aid]
        if yes: self.store.grant(kind,identity)
        if not future.done(): future.set_result(yes)
    def submit(self,text,route=None):
        if self.closed: raise PolicyError("Runtime is closing.")
        text=text.strip()
        if not text: raise ValueError('Enter a task; an empty request cannot run.')
        self.policy.public_text(text)
        tid=uuid.uuid4().hex[:8]
        self.store.task(tid,"QUEUED",text)
        self.jobs[tid]=asyncio.create_task(self.run(tid,text,route))
        return tid
    async def run(self,tid,text,route):
        from google.genai import types
        route=route or ("flash" if any(w in text.lower() for w in ("code","file","browser","run","fix","project","build","test","open","create","make","write","install","launch","terminal","rag")) else "lite")
        contents=list(self.history[-12:])+[types.Content(role="user",parts=[types.Part(text=text)])]
        evidence=[]
        try:
            if not self.model: raise PolicyError("AI offline: configure a verified Free project, actual quotas and your local GEMINI_API_KEY.")
            for step in range(20):
                await self.paused.wait()
                self.store.task(tid,"RUNNING",text)
                failures=0
                while True:
                    parts=[]
                    try:
                        async for chunk in self.model.stream(contents,route):
                            if chunk.candidates and chunk.candidates[0].content:
                                for part in chunk.candidates[0].content.parts or []:
                                    parts.append(part)
                                if part.text:
                                    if self.stream_output: self.stream_output(tid,part.text)
                                    else: self.emit(f"[{tid}] {part.text}")
                        if self.stream_output: self.stream_output(tid,None)
                        break
                    except ProviderTransient as e:
                        failures+=1
                        if failures>4:
                            raise PolicyError("Gemini service retry limit reached; your task has stopped safely. Try again shortly. No paid fallback was used.")
                        delay=max(0,e.retry_at-time.time())*(2**(failures-1))
                        self.store.task(tid,"WAITING_FOR_PROVIDER",text)
                        self.emit(f"[{tid}] {e} Retrying in {delay:.0f}s (attempt {failures}/4); /stop {tid} cancels.")
                        await asyncio.sleep(delay)
                    except QuotaWait as e:
                        self.store.task(tid,"WAITING_FOR_QUOTA",text)
                        self.emit(f"[{tid}] {e}")
                        if e.retry_at is None:
                            raise PolicyError("Quota configuration/context requires correction; resubmit after fixing it.")
                        if "Provider" in str(e) or "provider" in str(e):
                            failures+=1
                            if failures>4:
                                from .quota import pacific_reset
                                e.retry_at=pacific_reset(time.time())
                                failures=0
                                self.emit(f"[{tid}] Repeated exhaustion: waiting until next Pacific daily reset; no paid fallback.")
                        await asyncio.sleep(max(1,e.retry_at-time.time()))
                if not parts: raise PolicyError("Empty/blocked model response; no actions executed.")
                contents.append(types.Content(role="model",parts=parts))
                calls=[p.function_call for p in parts if p.function_call]
                if not calls:
                    summary=''.join(p.text for p in parts if p.text)
                    if evidence: summary+='\nObserved tool evidence: '+json.dumps(evidence,ensure_ascii=False)[-6000:]
                    # Only complete dialogue pairs cross turns; truncating tool protocol breaks the API.
                    self.history=(self.history+[types.Content(role='user',parts=[types.Part(text=text)]),types.Content(role='model',parts=[types.Part(text=summary)])])[-12:]
                    self.store.task(tid,"SUCCEEDED",text)
                    return
                if route!="flash":
                    route='flash'
                    self.emit(f'[{tid}] Continuing with action tools; existing permissions still apply.')
                responses=[]
                for index,call in enumerate(calls):
                    await self.paused.wait()
                    oid=f"{tid}:{step}:{index}"
                    try:
                        result=await self.dispatch(tid,call.name,dict(call.args or {}),oid)
                        if call.name=='shell_output':
                            result['output']=result['output'].replace(str(self.policy.root),'<WORKSPACE>').replace(str(Path.home()),'<HOME>')
                        safe=self.policy.public_text(json.dumps(result,ensure_ascii=False))
                        if call.name in ("search_files","shell_output","browser_navigate","browser_inspect","browser_click","browser_fill"):
                            await self.require("public_excerpt",hashlib.sha256(safe.encode()).hexdigest(),"Review/classify this exact tool excerpt as non-sensitive public/demo before Gemini receives it:\n"+safe)
                        result=json.loads(safe)
                    except (PolicyError,ValueError,OSError) as e:
                        result={"status":"blocked","reason":str(e)}
                        try: self.policy.public_text(json.dumps(result))
                        except PolicyError: result={"status":"blocked","reason":"Sensitive tool evidence withheld locally."}
                    responses.append(types.Part.from_function_response(name=call.name,response=result))
                    evidence.append({'tool':call.name,'arguments':dict(call.args or {}),'result':result})
                contents.append(types.Content(role="user",parts=responses))
            raise PolicyError("Task reached its 20-step budget. Review progress before continuing.")
        except asyncio.CancelledError:
            self.store.task(tid,"CANCELLED",text)
            raise
        except Exception as e:
            self.store.task(tid,"FAILED",text)
            self.emit(f"[{tid}] {e}")
    async def dispatch(self,tid,name,args,oid):
        if name not in TOOL_FIELDS: raise PolicyError("Unknown tool.")
        fields=TOOL_FIELDS[name]
        if set(args)!=set(fields): raise PolicyError("Invalid tool argument fields.")
        for key,kind in fields.items():
            if not isinstance(args[key],int if kind=="integer" else str) or isinstance(args[key],bool):
                raise PolicyError("Invalid tool argument type.")
        self.policy.public_text(json.dumps(args))
        previous=self.store.operation_result(oid)
        if previous:
            if previous["state"]=="completed": return json.loads(previous["result"])
            raise PolicyError("Operation outcome uncertain; inspect before retrying.")
        root_id=hashlib.sha256(('folder:'+str(self.policy.root)).encode()).hexdigest()
        if name=='open_app':
            app_path=self.apps.resolve(args['name'])
            app_id=hashlib.sha256((str(app_path)+str(app_path.stat().st_mtime_ns)).encode()).hexdigest()
        if name=="write_file":
            target=self.policy.path(args["path"])
            root_id=hashlib.sha256(("folder:"+str(target.parent)).encode()).hexdigest()
        required=[]
        if name.startswith('browser_'):
            url=args.get('url') or (self.browser.page.url if self.browser.page else '')
            if url:
                destination=origin(url)
                if destination not in self.config_origins:
                    origin_id=hashlib.sha256(destination.encode()).hexdigest()
                    await self.require('origin',origin_id,'Allow this browser origin for non-sensitive workflows: '+destination+'?')
                    required.append(('origin',origin_id))
        if name=='open_app':
            await self.require('app',app_id,'Allow launching this installed application: '+str(app_path)+'?')
            required.append(('app',app_id))
        if name=="read_file":
            preview=self.workspace.read(args["path"])
            public_id=hashlib.sha256(json.dumps(preview,sort_keys=True).encode()).hexdigest()
            await self.require("public_file",public_id,"Classify this exact file version as non-sensitive public/demo:\n"+json.dumps(preview,ensure_ascii=False))
            required.append(("public_file",public_id))
        if name in ("write_file","open_vscode"):
            await self.require("workspace",root_id,"Allow reversible edits/open VS Code in this local folder: "+str(target.parent if name=="write_file" else self.policy.root)+"? Cloud file contents still require public classification.")
            required.append(("workspace",root_id))
        if name=="shell_run":
            identity=self.policy.command_identity(args["command"])
            await self.require("command",identity,"Run this exact trusted command under your Windows account (not OS-isolated): "+args["command"])
            if identity!=self.policy.command_identity(args["command"]):
                raise PolicyError("Project script identities changed; review command again.")
            required.append(("command",identity))
        if name.startswith("browser_") and name not in ("browser_navigate","browser_inspect"):
            identity=hashlib.sha256(json.dumps([self.browser.revision,self.browser.page.url if self.browser.page else "",name,args],sort_keys=True).encode()).hexdigest()
            await self.require("browser_effect",identity,"Allow this demo browser effect: "+json.dumps(args))
            required.append(("browser_effect",identity))
        await self.paused.wait()
        async with self.action_lock:
            if not self.paused.is_set():
                raise PolicyError("Dispatch paused while waiting for resource lock; retry after resume.")
            if any(not self.store.allowed(k,v) for k,v in required):
                raise PolicyError("Grant revoked before dispatch.")
            if name=='browser_navigate': self.browser.origins.add(origin(args['url']))
            if name=='open_app' and hashlib.sha256((str(self.apps.resolve(args['name']))+str(self.apps.resolve(args['name']).stat().st_mtime_ns)).encode()).hexdigest()!=app_id:
                raise PolicyError('Application changed after approval.')
            if name=="read_file" and hashlib.sha256(json.dumps(self.workspace.read(args["path"]),sort_keys=True).encode()).hexdigest()!=public_id:
                raise PolicyError("File changed after public classification.")
            if name=="shell_run" and identity!=self.policy.command_identity(args["command"]):
                raise PolicyError("Script changed before dispatch.")
            if name.startswith("browser_") and name not in ("browser_navigate","browser_inspect"):
                current=hashlib.sha256(json.dumps([self.browser.revision,self.browser.page.url if self.browser.page else "",name,args],sort_keys=True).encode()).hexdigest()
                if current!=identity: raise PolicyError("Browser page changed after approval.")
            existing=self.store.operation_result(oid)
            if existing:
                if existing["state"]=="completed": return json.loads(existing["result"])
                raise PolicyError("Operation outcome uncertain; inspect before retrying.")
            if name=="shell_run":
                # Arbitrary PowerShell dependencies cannot be fully fingerprinted.
                # One-use approval avoids reusing authority after unseen script edits.
                self.store.consume("command",identity)
            self.store.operation(oid,"dispatched")
            try:
                if name=='list_apps': result={'apps':self.apps.list()}
                elif name=='open_app': result=await asyncio.to_thread(self.apps.open,args['name'])
                elif name=='open_terminal': result=self.apps.open_terminal(tid)
                elif name=='terminal_create': result=await self.shells.run(args['slot'],'Write-Output "JASON session ready"',tid)
                elif name=='task_status': result={'tasks':self.store.tasks(),'terminals':self.shells.status()}
                elif name=="list_files": result={"files":self.workspace.list(args["path"])}
                elif name=="search_files": result={"matches":self.workspace.search(args["path"],args["query"])}
                elif name=="read_file": result=self.workspace.read(args["path"])
                elif name=="write_file": result=self.workspace.write(args["path"],args["content"],args["expected_hash"])
                elif name=="open_vscode": result=self.workspace.open_vscode()
                elif name=="shell_run": result=await self.shells.run(args["slot"],args["command"],tid)
                elif name=="shell_output": result={"output":self.shells.output(args["slot"]),"sessions":self.shells.status()}
                elif name=="shell_stop":
                    await self.shells.stop(args["slot"])
                    result={"status":"stopped","session":args["slot"]}
                elif name=="browser_navigate": result=await self.browser.navigate(args["url"])
                elif name=="browser_inspect": result=await self.browser.inspect()
                elif name=="browser_click": result=await self.browser.interact(args["role"],args["name"])
                elif name=="browser_fill": result=await self.browser.interact(args["role"],args["name"],args["text"])
                self.store.operation(oid,"completed",json.dumps(result))
                return result
            except BaseException:
                self.store.operation(oid,"uncertain")
                raise
    async def stop(self,tid):
        ids=list(self.jobs) if tid=="all" else [tid]
        if tid=="all": self.paused.clear()
        cancelled=[]
        for jobid in ids:
            task=self.jobs.get(jobid)
            if task and not task.done():
                task.cancel()
                cancelled.append(task)
        await asyncio.gather(*cancelled,return_exceptions=True)
        for slot,session in list(self.shells.sessions.items()):
            if tid=="all" or session.owner==tid: await self.shells.stop(slot)
        await self.apps.stop(tid)
    async def close(self):
        self.closed=True
        await self.stop("all")
        await self.browser.close()
        await self.shells.close()
        await self.apps.close()
        if self.model: await self.model.close()
        self.store.db.close()

    def status_text(self):
        rows=self.store.tasks()[-10:]
        return '\n'.join(f"{r['id']}  {r['state']}  {r['summary'][:100]}" for r in rows) or 'No tasks yet.'

    async def watch(self):
        previous={}
        while not self.closed:
            for slot,status in self.shells.status().items():
                before=previous.get(slot)
                if before and (before['busy'] and not status['busy'] or before['running'] and not status['running']):
                    self.emit(f"[PS-{slot}] state changed: "+json.dumps(status))
                previous[slot]=status
            await asyncio.sleep(1)

