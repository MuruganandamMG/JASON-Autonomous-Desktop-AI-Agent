import asyncio
import hashlib
import tempfile
from pathlib import Path
import pytest
from jason.config import Settings
from jason.policy import Policy, PolicyError
from jason.store import Store
from jason.quota import Quota, QuotaWait, pacific_reset
from jason.workspace import Workspace

def test_default_blocks_cloud(tmp_path):
    s = Settings.load(tmp_path / "absent.toml")
    assert not s.ai_ready
    assert s.limits("lite") == (0, 0, 0)

def test_free_gate_requires_recent_verification():
    s = Settings(free_project_verified=True, project_id="demo", verified_on="2000-01-01")
    assert not s.ai_ready

def test_secret_in_chat_and_history_is_blocked(tmp_path):
    p = Policy(tmp_path, True)
    for text in ["GEMINI_API_KEY=abc123", "token: supersecretvalue", "my email is me@example.com"]:
        with pytest.raises(PolicyError):
            p.public_text(text)
    assert p.public_text("Explain the demo frontend") == "Explain the demo frontend"

def test_root_escape_and_secret_files(tmp_path):
    p = Policy(tmp_path, True)
    for name in ["../escape.txt", ".env", ".env.local", "id_rsa", ".git/config"]:
        with pytest.raises(PolicyError):
            p.path(name)

def test_junction_escape(tmp_path):
    target = tmp_path.parent / (tmp_path.name + "-outside")
    target.mkdir(exist_ok=True)
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink privilege unavailable")
    with pytest.raises(PolicyError):
        Policy(tmp_path, True).path("link/file")

def test_store_reopen_and_revocation(tmp_path):
    db = tmp_path / "state.db"
    with Store(db) as s:
        s.grant("cmd", "abc")
        assert s.allowed("cmd", "abc")
        s.task("t1", "WAITING_FOR_QUOTA", "demo")
    with Store(db) as s:
        assert s.tasks()[0]["state"] == "WAITING_FOR_QUOTA"
        s.revoke()
        assert not s.allowed("cmd", "abc")

def test_checked_edits_preserve_external_work(tmp_path):
    w = Workspace(Policy(tmp_path, True), tmp_path / ".state")
    f = tmp_path / "demo.txt"
    f.write_text("original")
    old = hashlib.sha256(f.read_bytes()).hexdigest()
    f.write_text("external")
    with pytest.raises(PolicyError):
        w.write("demo.txt", "new", old)
    assert f.read_text() == "external"

def test_edit_new_file_requires_nonexistence(tmp_path):
    w = Workspace(Policy(tmp_path, True), tmp_path / ".state")
    assert w.write("demo.txt", "hello", "")["status"] == "verified"
    with pytest.raises(PolicyError):
        w.write("demo.txt", "overwrite", "")

def test_quota_project_persistence_and_reset(tmp_path):
    with Store(tmp_path / "state.db") as s:
        q = Quota(s, {"m": (2, 100, 2)}, now=lambda: 1000)
        q.reserve("m", 40)
        q.reserve("m", 40)
        with pytest.raises(QuotaWait):
            q.reserve("m", 1)
        assert len(s.usage()) == 2
    with Store(tmp_path / "state.db") as s:
        q = Quota(s, {"m": (2, 100, 2)}, now=lambda: 1120)
        with pytest.raises(QuotaWait):
            q.reserve("m", 1)

def test_unknown_quota_never_unlimited(tmp_path):
    with Store(tmp_path / "state.db") as s:
        with pytest.raises(QuotaWait):
            Quota(s, {"m": (0, 0, 0)}).reserve("m", 1)

def test_pacific_reset_dst():
    from datetime import datetime, timezone
    for date, hour in [("2026-07-01", 7), ("2026-12-01", 8)]:
        stamp = datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp()
        assert datetime.fromtimestamp(pacific_reset(stamp), timezone.utc).hour == hour

