import asyncio
import time
from google.genai import types
from jason.tasks import Runtime
from jason.config import Settings
from jason.quota import QuotaWait

async def test_temporary_provider_failure_has_bounded_retries(tmp_path):
    from jason.models import ProviderTransient
    class Broken(Model):
        async def stream(self,contents,route):
            self.turns+=1
            raise ProviderTransient(503,delay=0)
            yield
    messages=[]
    r=Runtime(Settings(root=str(tmp_path)),tmp_path/'.state',emit=messages.append)
    r.model=Broken()
    try:
        tid=r.submit('hello','lite')
        await asyncio.wait_for(r.jobs[tid],8)
        assert r.model.turns==5
        assert next(t for t in r.store.tasks() if t['id']==tid)['state']=='FAILED'
        assert any('retry limit' in m.lower() for m in messages)
        assert not any('daily reset' in m for m in messages)
    finally: await r.close()

async def test_provider_wait_can_be_stopped_locally(tmp_path):
    from jason.models import ProviderTransient
    class Waiting(Model):
        async def stream(self,contents,route):
            raise ProviderTransient(503,delay=30)
            yield
    r=Runtime(Settings(root=str(tmp_path)),tmp_path/'.state',emit=lambda x:None)
    r.model=Waiting()
    try:
        tid=r.submit('hello','lite')
        for _ in range(100):
            if next(t['state'] for t in r.store.tasks() if t['id']==tid)=='WAITING_FOR_PROVIDER': break
            await asyncio.sleep(.01)
        await asyncio.wait_for(r.stop('all'),1)
        assert r.jobs[tid].cancelled()
    finally: await r.close()

class Model:
    def __init__(self):
        self.turns=0
        self.requests=[]
    async def stream(self,contents,route):
        self.requests.append([c.model_dump(mode='json') for c in contents])
        self.turns+=1
        if self.turns==1:
            p=types.Part.from_function_call(name='write_file',args={'path':'hello.txt','content':'Hello demo','expected_hash':''})
        else:
            p=types.Part(text='The demo file was written and verified.')
        yield types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model',parts=[p]))])
    async def close(self): pass

async def finish_with_approvals(r,tid):
    for _ in range(300):
        for aid in list(r.approvals): r.approve(aid)
        if r.jobs[tid].done(): return
        await asyncio.sleep(.01)
    raise AssertionError('Task failed to finish')

async def test_model_tool_continuation_and_history(tmp_path):
    r=Runtime(Settings(root=str(tmp_path),public_demo=True),tmp_path/'.state',emit=lambda x:None)
    r.model=Model()
    try:
        tid=r.submit('Write a public demo file','flash')
        await finish_with_approvals(r,tid)
        assert (tmp_path/'hello.txt').read_text()=='Hello demo'
        assert next(t for t in r.store.tasks() if t['id']==tid)['state']=='SUCCEEDED'
        assert r.model.turns==2
        assert any('function_response' in str(c) for c in r.model.requests[1])
        tid=r.submit('What did you just write?','lite')
        await finish_with_approvals(r,tid)
        assert 'Hello demo' in str(r.model.requests[-1])
    finally: await r.close()

async def test_quota_wait_resumes_without_replaying_mutation(tmp_path):
    class Waiting(Model):
        async def stream(self,contents,route):
            if not hasattr(self,'waited'):
                self.waited=True
                raise QuotaWait('Estimated minute quota reached.',time.time()+.01)
            async for c in super().stream(contents,route): yield c
    r=Runtime(Settings(root=str(tmp_path),public_demo=True),tmp_path/'.state',emit=lambda x:None)
    r.model=Waiting()
    try:
        tid=r.submit('Write public demo file','flash')
        await finish_with_approvals(r,tid)
        assert (tmp_path/'hello.txt').read_text()=='Hello demo'
        assert r.model.turns==2
    finally: await r.close()
