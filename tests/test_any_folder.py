from datetime import date
import pytest
from jason.config import Settings
from jason.policy import Policy, PolicyError
from jason.workspace import Workspace

def test_chat_without_demo_workspace(tmp_path):
    assert Policy(tmp_path,False).public_text('hello')=='hello'
    s=Settings(free_project_verified=True,project_id='demo',verified_on=date.today().isoformat())
    assert s.ai_ready

def test_explicit_any_folder_access_preserves_secret_exclusion(tmp_path):
    outside=tmp_path.parent/(tmp_path.name+'-external')
    outside.mkdir(exist_ok=True)
    (outside/'example.txt').write_text('public example')
    p=Policy(tmp_path,False,any_folder=True)
    w=Workspace(p,tmp_path/'.state')
    assert w.read(str(outside/'example.txt'))['content']=='public example'
    assert str(outside/'example.txt') in w.list(str(outside))
    with pytest.raises(PolicyError): p.path(str(outside/'.env'))
    with pytest.raises(PolicyError): p.public_text('password=real-secret')
