from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio
from google.genai import types
from jason.models import Gemini
from jason.config import Settings
from jason.policy import Policy
from jason.quota import Quota
from jason.store import Store

async def test_31_flash_lite_passes_model_gate(tmp_path):
    with Store(tmp_path/'state.db') as store:
        model=Gemini.__new__(Gemini)
        model.s=Settings(free_project_verified=True,project_id='demo',verified_on=date.today().isoformat(),lite_model='gemini-3.1-flash-lite')
        model.policy=Policy(tmp_path,False)
        model.quota=Quota(store,{'gemini-3.1-flash-lite':(15,250000,500)})
        model.lock=asyncio.Lock()
        async def chunks():
            yield types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role='model',parts=[types.Part(text='Hello')]))])
        generate=AsyncMock(return_value=chunks())
        model.client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate)))
        result=[c async for c in model.stream([types.Content(role='user',parts=[types.Part(text='Hello')])],'lite')]
        assert result[0].candidates[0].content.parts[0].text=='Hello'
        assert generate.call_args.kwargs['model']=='gemini-3.1-flash-lite'
