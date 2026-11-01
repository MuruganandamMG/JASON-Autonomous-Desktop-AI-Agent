import argparse
import asyncio
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from .config import Settings
from .tasks import Runtime

HELP="""Describe what you want; chat and action tools work without manual routing.
/flash or /lite changes mode; /flash TEXT or /lite TEXT runs that request.
/tasks  /terminals  /logs SLOT  /quota  /permissions
/approve ID  /deny ID  /revoke  /pause  /resume  /stop TASK-ID|all
/new clears conversation; /exit stops JASON-owned jobs.
/apps lists installed applications; /app NAME launches one; /terminal opens PowerShell.
/cd PATH changes the working folder for files and future terminals; /retry TASK-ID reattempts work.
Only public/demo content may be submitted. Local commands work with no API key."""

async def interact(settings,state):
    active_stream=None
    def stream_output(tid,text):
        nonlocal active_stream
        if text is None:
            if active_stream is not None: print(flush=True)
            active_stream=None
        else:
            if active_stream!=tid:
                if active_stream is not None: print(flush=True)
                print('['+tid+'] ',end='',flush=True)
                active_stream=tid
            print(text,end='',flush=True)
    runtime=Runtime(settings,state,stream_output=stream_output)
    watcher=asyncio.create_task(runtime.watch())
    interactive=sys.stdin.isatty() and sys.stdout.isatty()
    class PipePrompt:
        async def prompt_async(self,prompt):
            line=await asyncio.to_thread(sys.stdin.readline)
            if not line: raise EOFError
            return line
    session=PromptSession() if interactive else PipePrompt()
    print("JASON 0.1 — live terminal agent. "+("Gemini enabled." if runtime.model else "AI offline; configure Free-tier setup."))
    print(HELP)
    mode=None
    try:
        with patch_stdout() if interactive else nullcontext():
            while True:
                try:
                    text=(await session.prompt_async("You > ")).strip()
                except KeyboardInterrupt:
                    # Cancel current inference tasks; explicitly preserve shells.
                    for task in runtime.jobs.values():
                        if not task.done(): task.cancel()
                    print("Responses cancelled. Shells remain; /stop all stops jobs.")
                    continue
                except EOFError: break
                if not text: continue
                cmd,_,arg=text.partition(" ")
                try:
                    if cmd=="/exit": break
                    elif cmd=="/help": print(HELP)
                    elif cmd=="/tasks" or text.lower().strip('!?. ') in ('status','is it done','are you done','done','the work is completed or not','is the work completed','what is the status'):
                        print(runtime.status_text())
                    elif cmd=="/terminals": print(json.dumps(runtime.shells.status(),indent=2))
                    elif cmd=="/logs": print(runtime.shells.output(int(arg)))
                    elif cmd=="/quota": print("LOCAL ESTIMATES ONLY; verify actual remaining quota in AI Studio.\n"+json.dumps(runtime.store.usage()[-20:],indent=2))
                    elif cmd=="/permissions": print("Pending approvals: "+str(list(runtime.approvals))+"; /revoke clears standing grants.")
                    elif cmd in ("/approve","/deny"): runtime.approve(arg,cmd=="/approve")
                    elif cmd=="/revoke": runtime.store.revoke(); print("Standing grants revoked.")
                    elif cmd=="/pause": runtime.paused.clear(); print("New action dispatch paused; running servers remain.")
                    elif cmd=="/resume": runtime.paused.set(); print("Dispatch resumed. Interrupted/failed tasks require a fresh instruction.")
                    elif cmd=="/stop":
                        if not arg.strip(): print('Usage: /stop TASK-ID or /stop all')
                        else: await runtime.stop(arg.strip()); print('Stop completed for '+arg.strip())
                    elif text.lower()=="stop everything": await runtime.stop("all")
                    elif cmd=="/new": runtime.history.clear(); print("Conversation cleared.")
                    elif cmd in ("/flash","/lite"):
                        if arg.strip(): print('Task '+runtime.submit(arg,cmd[1:]))
                        else:
                            mode=cmd[1:]
                            print(mode.title()+' mode selected. Enter your task; action tools remain available.')
                    elif cmd=='/auto': mode=None; print('Automatic mode selected.')
                    elif cmd=='/apps': print('\n'.join(runtime.apps.list()))
                    elif cmd=='/app':
                        if not arg.strip(): print('Usage: /app NAME')
                        else: print(json.dumps(await asyncio.to_thread(runtime.apps.open,arg.strip())))
                    elif cmd=='/terminal': print(json.dumps(runtime.apps.open_terminal()))
                    elif cmd=='/cd':
                        destination=runtime.policy.path(arg)
                        if not arg or not destination.is_dir(): print('Usage: /cd EXISTING-FOLDER')
                        else:
                            runtime.policy.root=destination
                            runtime.apps.root=destination
                            runtime.shells.root=str(destination)
                            print('Working folder: '+str(destination)+'; existing shell sessions retain their folders.')
                    elif cmd=='/retry':
                        row=next((r for r in runtime.store.tasks() if r['id']==arg.strip()),None)
                        if not row: print('Usage: /retry TASK-ID; inspect /tasks first.')
                        else: print('Task '+runtime.submit('Inspect existing state before making changes; an earlier attempt may have effects. Reattempt: '+row['summary'],'flash'))
                    elif cmd.startswith("/"): print("Unknown control. /help")
                    else: print("Task "+runtime.submit(text,mode))
                except Exception as e:
                    print(str(e))
    finally:
        watcher.cancel()
        await asyncio.gather(watcher,return_exceptions=True)
        await runtime.close()

def main():
    parser=argparse.ArgumentParser(description="JASON: Windows terminal agent (Gemini free-tier only)")
    parser.add_argument("--config",default="config.toml")
    parser.add_argument("--state",default=".jason")
    args=parser.parse_args()
    # .env is explicit local configuration, never read by agent file tools.
    from dotenv import load_dotenv
    load_dotenv(override=False)
    settings=Settings.load(args.config)
    settings.root=str(Path(settings.root).resolve())
    asyncio.run(interact(settings,args.state))

if __name__=="__main__": main()

