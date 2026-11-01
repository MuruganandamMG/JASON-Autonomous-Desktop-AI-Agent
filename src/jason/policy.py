import hashlib
import re
from pathlib import Path

class PolicyError(Exception): pass

class Policy:
    def __init__(self, root, public_demo):
        self.root = Path(root).resolve()
        self.public_demo = public_demo
    def public_text(self, text):
        if not self.public_demo:
            raise PolicyError("Opt into a non-sensitive public/demo workspace first.")
        patterns = [
            r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+",
            r"AIza[\w-]{20,}", r"-----BEGIN .*PRIVATE KEY",
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
            r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+|/home/)\S+",
            r"(?:AKIA|ASIA)[A-Z0-9]{16}", r"gh[pousr]_[A-Za-z0-9]{20,}",
            r"(?i)(confidential|personally identifiable|private customer|social security)",
        ]
        if any(re.search(p, text) for p in patterns):
            raise PolicyError("Potential private data withheld locally. Rephrase using demo content.")
        return text
    def path(self, relative):
        p = (self.root / relative).resolve()
        if not p.is_relative_to(self.root):
            raise PolicyError("Path is outside the approved root.")
        forbidden = {".git", ".jason", ".venv", "node_modules", "id_rsa", "id_ed25519", "credentials.json"}
        if any(part.lower() in forbidden or part.lower().startswith(".env") or
               part.lower().endswith((".pem", ".key", ".pfx")) for part in p.relative_to(self.root).parts):
            raise PolicyError("Sensitive or internal path is excluded.")
        return p
    def command_identity(self, command):
        # Exact command AND project execution manifests are bound to the grant.
        h = hashlib.sha256((str(self.root) + "\0" + command).encode())
        for pattern in ("package*.json", "*lock*", "pyproject.toml", "*.ps1"):
            for p in sorted(self.root.glob(pattern)):
                if p.is_file():
                    h.update(str(p.relative_to(self.root)).encode())
                    h.update(p.read_bytes())
        return h.hexdigest()

