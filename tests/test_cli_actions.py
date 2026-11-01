import asyncio
import subprocess
import sys
from google.genai import types
from jason.config import Settings
from jason.tasks import Runtime
from jason.apps import Apps
from test_model_flow import Model, finish_with_approvals

async def test_create_request_can_use_tools_on_automatic_light_route(tmp_path):
    r=Runtime(Settings(root=str(tmp_path)),tmp_path/'.state',emit=lambda x:None)
    r.model=Model()
    try:
        tid=r.submit('create a simple rag system only!')
        await finish_with_approvals(r,tid)
        assert (tmp_path/'hello.txt').exists()
        assert next(x['state'] for x in r.store.tasks() if x['id']==tid)=='SUCCEEDED'
    finally: await r.close()

async def test_waiting_approvals_do_not_block_new_chat(tmp_path):
    class Chat:
        async def stream(self,contents,route):
            yield types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model',parts=[types.Part(text='Hello')]))])
        async def close(self): pass
    r=Runtime(Settings(root=str(tmp_path)),tmp_path/'.state',emit=lambda x:None)
    async def wait():
        await r.require('test','pending','test approval')
    r.jobs['hold1']=asyncio.create_task(wait())
    r.jobs['hold2']=asyncio.create_task(wait())
    r.model=Chat()
    try:
        tid=r.submit('hello')
        await asyncio.wait_for(r.jobs[tid],2)
        assert next(t['state'] for t in r.store.tasks() if t['id']==tid)=='SUCCEEDED'
    finally: await r.close()

async def test_empty_request_rejected(tmp_path):
    import pytest
    r=Runtime(Settings(root=str(tmp_path)),tmp_path/'.state',emit=lambda x:None)
    try:
        with pytest.raises(ValueError): r.submit(' ')
    finally: await r.close()

def test_bare_flash_is_mode_change_not_empty_task(tmp_path):
    result=subprocess.run([sys.executable,'-m','jason','--state',str(tmp_path/'.state')],
        input='/flash\n/tasks\n/exit\n',capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert 'mode' in result.stdout.lower()
    assert 'No tasks yet.' in result.stdout
    assert 'Task ' not in result.stdout

def test_apps_resolve_known_names_without_shell(tmp_path):
    apps=Apps(tmp_path)
    assert apps.resolve('notepad')
    import pytest
    with pytest.raises(ValueError): apps.resolve('notepad & whoami')

async def test_stop_all_cleans_owned_visible_terminals(tmp_path):
    from types import SimpleNamespace
    r=Runtime(Settings(root=str(tmp_path)),tmp_path/'.state',emit=lambda x:None)
    stopped=[]
    r.apps.terminals[123]=(SimpleNamespace(),SimpleNamespace(close=lambda:stopped.append(123)),'owner')
    try:
        await r.stop('all')
        assert stopped==[123]
        assert not r.apps.terminals
    finally: await r.close()

async def test_revoking_origin_removes_browser_navigation_permission(tmp_path):
    import hashlib
    r=Runtime(Settings(root=str(tmp_path)),tmp_path/'.state',emit=lambda x:None)
    try:
        origin='https://demo.invalid'
        r.store.grant('origin',hashlib.sha256(origin.encode()).hexdigest())
        r.browser.origins.add(origin)
        assert r.browser.allowed(origin)
        r.store.revoke()
        assert not r.browser.allowed(origin)
    finally: await r.close()

async def test_real_visible_terminal_is_owned_and_stops(tmp_path):
    apps=Apps(tmp_path)
    try:
        result=apps.open_terminal('demo-task')
        process=apps.terminals[result['pid']][0]
        assert process.poll() is None
        await apps.stop('demo-task')
        await asyncio.to_thread(process.wait,5)
        assert not apps.terminals
    finally: await apps.close()
