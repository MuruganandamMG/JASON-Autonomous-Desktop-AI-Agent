import asyncio
import base64
from collections import deque
from dataclasses import dataclass, field
import os
import re
import shutil
import threading
import uuid
import sys
from pathlib import Path
from contextlib import suppress
from .winprocess import Job

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")

def child_env():
    keys = {"systemroot","windir","path","pathext","temp","tmp","comspec","programfiles","programfiles(x86)","userprofile","localappdata","appdata"}
    env={k:v for k,v in os.environ.items() if k.lower() in keys}
    path_key=next((k for k in env if k.lower()=='path'),'PATH')
    env[path_key]=str(Path(sys.executable).parent)+os.pathsep+env.get(path_key,'')
    return env

@dataclass
class Session:
    process: object
    job: Job
    owner: str
    chunks: deque = field(default_factory=lambda: deque(maxlen=256))
    done: threading.Event = field(default_factory=threading.Event)
    marker: str = ""
    exit_code: int | None = None
    busy: bool = False

class Shells:
    def __init__(self, root, executable=None):
        self.root=str(root)
        self.executable=executable or shutil.which("pwsh")
        self.sessions={}
    def _spawn(self, owner):
        if not self.executable: raise RuntimeError("Install standalone PowerShell 7 (pwsh).")
        from winpty import PtyProcess
        p=PtyProcess.spawn([self.executable,"-NoLogo","-NoProfile","-NoExit","-Command","Remove-Module PSReadLine -ErrorAction SilentlyContinue"],cwd=self.root,env=child_env(),dimensions=(30,160))
        try:
            job=Job(p.pid)
        except BaseException:
            p.terminate(force=True)
            raise
        s=Session(p,job,owner)
        def reader():
            pending=""
            try:
                while p.isalive():
                    chunk=p.read(4096)
                    if not chunk: continue
                    clean=ANSI.sub("",chunk)
                    s.chunks.append(clean[-8192:])
                    pending=(pending+clean)[-32768:]
                    if s.marker:
                        match=re.search(re.escape(s.marker)+r":(-?\d+)",pending)
                        if match:
                            s.exit_code=int(match.group(1))
                            s.busy=False
                            s.done.set()
            except (EOFError,OSError):
                pass
            finally:
                s.done.set()
        threading.Thread(target=reader,daemon=True).start()
        return s
    async def run(self, slot, command, owner):
        if slot not in (1,2,3): raise ValueError("Only PS-1, PS-2 and PS-3 exist.")
        s=self.sessions.get(slot)
        if s and s.busy: raise ValueError("Session is occupied. Inspect its output or choose another slot.")
        if s and s.owner!=owner:
            if s.job.count()>1: raise ValueError("Another task still owns background children in this session.")
            await self.stop(slot)
            s=None
        if not s:
            spawning=asyncio.create_task(asyncio.to_thread(self._spawn,owner))
            try:
                s=await asyncio.shield(spawning)
            except asyncio.CancelledError:
                # to_thread cannot be cancelled: collect and clean its eventual result.
                created=await spawning
                await asyncio.to_thread(created.job.close)
                with suppress(OSError):
                    await asyncio.to_thread(created.process.terminate,True)
                raise
            self.sessions[slot]=s
        s.marker="JASON_END_"+uuid.uuid4().hex
        s.done.clear()
        s.busy=True
        script=("$global:LASTEXITCODE=0; $ErrorActionPreference='Stop'; try { . { "+command+
                " }; $jasonCode=0; if ($LASTEXITCODE) { $jasonCode=$LASTEXITCODE } } catch { Write-Output $_; $jasonCode=1 }; "+
                "[Console]::WriteLine('"+s.marker+":'+$jasonCode)")
        encoded=base64.b64encode(script.encode("utf-16-le")).decode()
        line=". ([ScriptBlock]::Create([Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('"+encoded+"'))))\r\n"
        await asyncio.to_thread(s.process.write,line)
        # Return without waiting: long-lived servers must not block conversation.
        return {"session":slot,"state":"running","owner":owner}
    def output(self,slot):
        s=self.sessions.get(slot)
        if not s: return "Session does not exist."
        return "".join(s.chunks)[-24000:]
    def status(self):
        return {i:{"owner":s.owner,"running":s.process.isalive(),"busy":s.busy,"exit_code":s.exit_code} for i,s in self.sessions.items()}
    async def stop(self,slot):
        s=self.sessions.pop(slot,None)
        if not s: return
        try:
            await asyncio.to_thread(s.process.write,"\x03")
            await asyncio.to_thread(s.done.wait,5)
        finally:
            await asyncio.to_thread(s.job.close)
            with suppress(OSError):
                await asyncio.to_thread(s.process.terminate,True)
    async def close(self):
        for slot in list(self.sessions): await self.stop(slot)

