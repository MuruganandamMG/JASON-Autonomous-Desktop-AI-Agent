import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from .policy import PolicyError

class Workspace:
    def __init__(self, policy, state):
        self.policy, self.state = policy, Path(state)
    def read(self, path):
        p = self.policy.path(path)
        if p.stat().st_size > 128_000:
            raise PolicyError("File too large; request a smaller excerpt.")
        content = self.policy.public_text(p.read_text(encoding="utf-8"))
        return {"path":path, "content":content, "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    def list(self):
        return [str(p.relative_to(self.policy.root)) for p in self.policy.root.iterdir()
                if not p.name.startswith(".")][:200]
    def write(self, path, content, expected_hash):
        p = self.policy.path(path)
        self.policy.public_text(content)
        actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
        if actual != expected_hash:
            raise PolicyError("File changed or already exists; read it again before editing.")
        self.state.mkdir(parents=True, exist_ok=True)
        if p.exists():
            (self.state / (actual + ".bak")).write_bytes(p.read_bytes())
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=p.parent)
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(content.encode("utf-8"))
            if (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "") != expected_hash:
                raise PolicyError("Concurrent edit detected.")
            os.replace(name,p)
        finally:
            Path(name).unlink(missing_ok=True)
        return {"status":"verified", "path":path, "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    def open_vscode(self):
        import shutil
        code = shutil.which("code")
        if not code: raise PolicyError("VS Code command is not installed.")
        from .shells import child_env
        subprocess.Popen([code, str(self.policy.root)], shell=False,env=child_env())
        return {"status":"launched"}

