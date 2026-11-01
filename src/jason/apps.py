"""Launch installed Windows apps without evaluating model text in a shell."""
import asyncio
import os
from pathlib import Path
import re
import shutil
import subprocess
from .shells import child_env
from .winprocess import Job

class Apps:
    def __init__(self,root):
        self.root=Path(root)
        self.terminals={}
    def shortcuts(self):
        found={}
        for base in (os.getenv('PROGRAMDATA'),os.getenv('APPDATA')):
            if base:
                menu=Path(base)/'Microsoft/Windows/Start Menu/Programs'
                if menu.exists():
                    for p in menu.rglob('*.lnk'):
                        found.setdefault(p.stem.casefold(),p)
        return found
    def list(self):
        return sorted(set(['notepad','calculator','vscode','explorer','edge','powershell']+list(self.shortcuts())))[:300]
    def resolve(self,name):
        if not name.strip() or re.search(r'[&|;<>\n\r]',name):
            raise ValueError('Use an installed app name or executable path, not a shell command.')
        alias={'notepad':'notepad.exe','calculator':'calc.exe','calc':'calc.exe','vscode':'code','visual studio code':'code','explorer':'explorer.exe','edge':'msedge.exe','powershell':'pwsh'}
        target=alias.get(name.casefold(),name)
        resolved=shutil.which(target)
        if target=='code' and resolved:
            exe=Path(resolved).parent.parent/'Code.exe'
            if exe.exists(): resolved=str(exe)
        if not resolved and target=='msedge.exe':
            p=Path(os.getenv('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe'
            if p.exists(): resolved=str(p)
        if resolved and Path(resolved).suffix.lower()=='.exe': return Path(resolved)
        p=Path(target).expanduser()
        if p.is_file() and p.suffix.lower()=='.exe': return p.resolve()
        shortcut=self.shortcuts().get(name.casefold())
        if shortcut: return shortcut
        raise ValueError('App not found. Use list_apps or provide its installed .exe path.')
    def open(self,name):
        p=self.resolve(name)
        if p.suffix.lower()=='.lnk':
            os.startfile(str(p))
            return {'status':'launch_requested','app':name}
        args=[str(p)]
        if p.name.casefold()=='code.exe': args+=['--new-window',str(self.root)]
        elif p.name.casefold()=='explorer.exe': args.append(str(self.root))
        process=subprocess.Popen(args,cwd=self.root,env=child_env())
        return {'status':'launch_requested','app':name,'launcher_pid':process.pid}
    def open_terminal(self,owner='local'):
        for pid,(p,job,_) in list(self.terminals.items()):
            if p.poll() is not None:
                job.close()
                del self.terminals[pid]
        if len(self.terminals)>=3: raise ValueError('Three visible terminals already exist; close one first.')
        exe=self.resolve('powershell')
        p=subprocess.Popen([str(exe),'-NoLogo','-NoProfile','-NoExit'],cwd=self.root,
            env=child_env(),creationflags=subprocess.CREATE_NEW_CONSOLE)
        try: job=Job(p.pid)
        except BaseException:
            p.terminate()
            raise
        self.terminals[p.pid]=(p,job,owner)
        return {'status':'running','pid':p.pid,'owner':'JASON','note':'Visible terminal; managed command sessions use terminal_create/shell_run.'}
    async def stop(self,owner='all'):
        for pid,(p,job,task) in list(self.terminals.items()):
            if owner=='all' or owner==task:
                await asyncio.to_thread(job.close)
                self.terminals.pop(pid,None)
    async def close(self):
        await self.stop()
