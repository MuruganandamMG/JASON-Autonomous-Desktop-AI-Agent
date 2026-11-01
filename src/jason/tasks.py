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
from .models import Gemini, TOOL_FIELDS
from .workspace import Workspace
from .shells import Shells
from .browser import Browser

class Runtime:
    def __init__(self, settings, state, emit=print):
        self.s,self.emit=settings,emit
        self.store=Store(Path(state)/"state.db")
        self.policy=Policy(settings.root,settings.public_demo)
        self.workspace=Workspace(self.policy,Path(state)/"backups")
        self.shells=Shells(self.policy.root)
        self.browser=Browser(settings.origins)
        self.quota=Quota(self.store,{settings.lite_model:settings.limits("lite"),settings.flash_model:settings.limits("flash")})
        key=os.getenv("GEMINI_API_KEY","")
        self.model=Gemini(settings,self.quota,self.policy,key) if key and settings.ai_ready else None
        self.jobs={}
        self.approvals={}
        self.history=[]
        self.action_lock=asyncio.Lock()
        self.capacity=asyncio.Semaphore(2)
        self.paused=asyncio.Event()
        self.paused.set()
        self.closed=False
    async def require(self,kind,identity,description):
        if self.store.allowed(kind,identity): return
        aid=uuid.uuid4().hex[:8]
        future=asyncio.get_running_loop().create_future()
        self.approvals[aid]=(kind,identity,future)
        self.emit(f"Approval {aid}: {description}\nUse /approve {aid} or /deny {aid}.")
        try:
            if not await future: raise PolicyError("User denied action.")
            if not self.store.allowed(kind,identity): raise PolicyError("Grant revoked.")
        finally:
            self.approvals.pop(aid,None)
    def approve(self,aid,yes=True):
        kind,identity,future=self.approvals[aid]
        if yes: self.store.grant(kind,identity)
        if not future.done(): future.set_result(yes)
    def submit(self,text,route=None):
        if self.closed: raise PolicyError("Runtime is closing.")
        self.policy.public_text(text)
        tid=uuid.uuid4().hex[:8]
        self.store.task(tid,"QUEUED",text)
        self.jobs[tid]=asyncio.create_task(self.run(tid,text,route))
        return tid
    async def run(self,tid,text,route):
        from google.genai import types
        route=route or ("flash" if any(w in text.lower() for w in ("code","file","browser","run","fix","project","build","test","open")) else "lite")
        contents=list(self.history[-12:])+[types.Content(role="user",parts=[types.Part(text=text)])]
        try:
            async with self.capacity:
                if not self.model: raise PolicyError("AI offline: configure a verified Free project, actual quotas and your local GEMINI_API_KEY.")
                await self.require("public_chat",hashlib.sha256(text.encode()).hexdigest(),"Classify this exact input as non-sensitive public/demo text for free Gemini: "+text)
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
                                        if part.text: self.emit(f"[{tid}] {part.text}")
                            break
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
                        self.history=(contents[-12:])
                        self.store.task(tid,"SUCCEEDED",text)
                        return
                    if route!="flash":
                        raise PolicyError("Action requested on light route. Resubmit with /flash for autonomous tools.")
                    responses=[]
                    for index,call in enumerate(calls):
                        await self.paused.wait()
                        oid=f"{tid}:{step}:{index}"
                        try:
                            result=await self.dispatch(tid,call.name,dict(call.args or {}),oid)
                            safe=self.policy.public_text(json.dumps(result,ensure_ascii=False))
                            if call.name in ("search_files","shell_output","browser_navigate","browser_inspect","browser_click","browser_fill"):
                                await self.require("public_excerpt",hashlib.sha256(safe.encode()).hexdigest(),"Review/classify this exact tool excerpt as non-sensitive public/demo before Gemini receives it:\n"+safe)
                            result=json.loads(safe)
                        except (PolicyError,ValueError,OSError) as e:
                            result={"status":"blocked","reason":str(e)}
                            try: self.policy.public_text(json.dumps(result))
                            except PolicyError: result={"status":"blocked","reason":"Sensitive tool evidence withheld locally."}
                        responses.append(types.Part.from_function_response(name=call.name,response=result))
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
        root_id=hashlib.sha256(str(self.policy.root).encode()).hexdigest()
        required=[]
        if name=="read_file":
            preview=self.workspace.read(args["path"])
            public_id=hashlib.sha256(json.dumps(preview,sort_keys=True).encode()).hexdigest()
            await self.require("public_file",public_id,"Classify this exact file version as non-sensitive public/demo:\n"+json.dumps(preview,ensure_ascii=False))
            required.append(("public_file",public_id))
        if name in ("write_file","open_vscode"):
            await self.require("workspace",root_id,"Allow reversible edits/open VS Code in the configured PUBLIC/DEMO project?")
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
                if name=="list_files": result={"files":self.workspace.list(args["path"])}
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
    async def close(self):
        self.closed=True
        await self.stop("all")
        await self.browser.close()
        await self.shells.close()
        if self.model: await self.model.close()
        self.store.db.close()

    async def watch(self):
        previous={}
        while not self.closed:
            for slot,status in self.shells.status().items():
                before=previous.get(slot)
                if before and (before['busy'] and not status['busy'] or before['running'] and not status['running']):
                    self.emit(f"[PS-{slot}] state changed: "+json.dumps(status))
                previous[slot]=status
            await asyncio.sleep(1)

