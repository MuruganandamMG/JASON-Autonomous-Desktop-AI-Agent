import asyncio
import os
import shutil
import pytest
from jason.shells import Shells
from jason.models import declarations
from jason.browser import Browser

async def test_three_real_shells_and_state(tmp_path):
    s = Shells(tmp_path)
    try:
        for i in range(1,4):
            await s.run(i, f"$demo = {i}; Write-Output $demo", "task"+str(i))
        for i in range(1,4):
            assert await asyncio.to_thread(s.sessions[i].done.wait, 15)
        assert "1" in s.output(1)
        await s.run(1, "Write-Output ($demo+10)", "task1")
        assert await asyncio.to_thread(s.sessions[1].done.wait, 15)
        assert "11" in s.output(1)
        with pytest.raises(ValueError):
            await s.run(4, "echo no", "task4")
        await s.stop(3)
        assert s.sessions[1].process.isalive()
        assert s.sessions[2].process.isalive()
    finally:
        await s.close()

async def test_child_environment_has_no_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-test-value")
    s = Shells(tmp_path)
    try:
        await s.run(1, "if ($env:GEMINI_API_KEY) { Write-Output 'LEAK' } else { Write-Output 'CLEAN' }", "t")
        assert await asyncio.to_thread(s.sessions[1].done.wait, 15)
        assert "CLEAN" in s.output(1)
        assert "LEAK\r\n" not in s.output(1)
    finally:
        await s.close()

def test_tools_are_manual_schemas():
    names = {d["name"] for d in declarations()}
    assert {"read_file","write_file","shell_run","shell_output","browser_navigate"} <= names

async def test_browser_blocks_unapproved_origin():
    b = Browser(["https://example.com"])
    with pytest.raises(ValueError):
        await b.navigate("https://private.invalid")
    assert b.page is None

async def test_cancel_during_shell_start_cleans_up(tmp_path,monkeypatch):
    import threading
    from types import SimpleNamespace
    entered=threading.Event()
    release=threading.Event()
    cleaned=[]
    s=Shells(tmp_path)
    def spawn(owner):
        entered.set()
        release.wait(5)
        return SimpleNamespace(job=SimpleNamespace(close=lambda:cleaned.append(True)),process=SimpleNamespace(write=lambda x:None,terminate=lambda x:None),done=threading.Event())
    monkeypatch.setattr(s,'_spawn',spawn)
    task=asyncio.create_task(s.run(1,'echo safe','t'))
    await asyncio.to_thread(entered.wait,2)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError): await task
    assert cleaned
    assert not s.sessions


