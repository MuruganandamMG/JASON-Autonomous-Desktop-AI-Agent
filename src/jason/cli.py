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

HELP="""Natural language starts a task; /flash TEXT or /lite TEXT selects a route.
/tasks  /terminals  /logs SLOT  /quota  /permissions
/approve ID  /deny ID  /revoke  /pause  /resume  /stop TASK-ID|all
/new clears conversation; /exit stops JASON-owned jobs.
Only public/demo content may be submitted. Local commands work with no API key."""

async def interact(settings,state):
    runtime=Runtime(settings,state)
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
                    elif cmd=="/tasks": print(json.dumps(runtime.store.tasks(),indent=2))
                    elif cmd=="/terminals": print(json.dumps(runtime.shells.status(),indent=2))
                    elif cmd=="/logs": print(runtime.shells.output(int(arg)))
                    elif cmd=="/quota": print("LOCAL ESTIMATES ONLY; verify actual remaining quota in AI Studio.\n"+json.dumps(runtime.store.usage()[-20:],indent=2))
                    elif cmd=="/permissions": print("Pending approvals: "+str(list(runtime.approvals))+"; /revoke clears standing grants.")
                    elif cmd in ("/approve","/deny"): runtime.approve(arg,cmd=="/approve")
                    elif cmd=="/revoke": runtime.store.revoke(); print("Standing grants revoked.")
                    elif cmd=="/pause": runtime.paused.clear(); print("New action dispatch paused; running servers remain.")
                    elif cmd=="/resume": runtime.paused.set(); print("Dispatch resumed. Interrupted/failed tasks require a fresh instruction.")
                    elif cmd=="/stop": await runtime.stop(arg)
                    elif text.lower()=="stop everything": await runtime.stop("all")
                    elif cmd=="/new": runtime.history.clear(); print("Conversation cleared.")
                    elif cmd in ("/flash","/lite"): print("Task "+runtime.submit(arg,cmd[1:]))
                    elif cmd.startswith("/"): print("Unknown control. /help")
                    else: print("Task "+runtime.submit(text))
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

