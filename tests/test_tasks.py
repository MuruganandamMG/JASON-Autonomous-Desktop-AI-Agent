import asyncio
import pytest
from jason.tasks import Runtime
from jason.config import Settings
from jason.policy import PolicyError

async def test_denied_write_waits_for_local_approval(tmp_path):
    r = Runtime(Settings(root=str(tmp_path), public_demo=True), tmp_path / ".state", emit=lambda x:None)
    try:
        job=asyncio.create_task(r.dispatch("t", "write_file", {"path":"demo.txt","content":"ok","expected_hash":""}, "op"))
        await asyncio.sleep(.01)
        assert not (tmp_path / "demo.txt").exists()
        aid=next(iter(r.approvals))
        r.approve(aid)
        assert (await job)["status"]=="verified"
        assert (tmp_path / "demo.txt").read_text()=="ok"
        assert (await r.dispatch("t","write_file",{"path":"demo.txt","content":"ok","expected_hash":""},"op"))["status"]=="verified"
    finally:
        await r.close()

async def test_file_text_requires_exact_public_classification(tmp_path):
    (tmp_path/'demo.txt').write_text('public example')
    r=Runtime(Settings(root=str(tmp_path),public_demo=True),tmp_path/'.state',emit=lambda x:None)
    try:
        task=asyncio.create_task(r.dispatch('t','read_file',{'path':'demo.txt'},'read'))
        await asyncio.sleep(.01)
        assert r.approvals
        r.approve(next(iter(r.approvals)))
        assert (await task)['content']=='public example'
    finally:
        await r.close()


async def test_stop_cancels_pending_approval(tmp_path):
    r=Runtime(Settings(root=str(tmp_path),public_demo=True),tmp_path/".state",emit=lambda x:None)
    task=r.submit("Create a demo file")
    await asyncio.sleep(.01)
    await r.stop("all")
    assert not r.jobs or all(t.done() for t in r.jobs.values())
    await r.close()

async def test_secret_cannot_become_a_task(tmp_path):
    r=Runtime(Settings(root=str(tmp_path),public_demo=True),tmp_path/".state",emit=lambda x:None)
    try:
        with pytest.raises(PolicyError):
            r.submit("password: real-secret")
    finally:
        await r.close()

async def test_revoked_grant_blocks_paused_write(tmp_path):
    r=Runtime(Settings(root=str(tmp_path),public_demo=True),tmp_path/'.state',emit=lambda x:None)
    r.paused.clear()
    try:
        pending=asyncio.create_task(r.dispatch('t','write_file',{'path':'denied.txt','content':'ok','expected_hash':''},'revoked'))
        await asyncio.sleep(.01)
        r.approve(next(iter(r.approvals)))
        await asyncio.sleep(.01)
        r.store.revoke()
        r.paused.set()
        with pytest.raises(PolicyError):
            await pending
        assert not (tmp_path/'denied.txt').exists()
    finally:
        await r.close()

