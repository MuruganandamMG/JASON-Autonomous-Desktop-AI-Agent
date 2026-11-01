from dataclasses import dataclass
from datetime import date
from pathlib import Path
import tomllib

@dataclass
class Settings:
    free_project_verified: bool = False
    project_id: str = ""
    verified_on: str = ""
    lite_model: str = "gemini-3.5-flash-lite"
    flash_model: str = "gemini-3.8-flash"
    lite_rpm: int = 0
    lite_tpm: int = 0
    lite_rpd: int = 0
    flash_rpm: int = 0
    flash_tpm: int = 0
    flash_rpd: int = 0
    root: str = "."
    public_demo: bool = False
    origins: tuple = ("https://example.com",)
    @classmethod
    def load(cls, path):
        if not Path(path).exists():
            return cls()
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls(**data.get("ai", {}), **data.get("workspace", {}))
    @property
    def ai_ready(self):
        try:
            age = (date.today() - date.fromisoformat(self.verified_on)).days
            return bool(self.free_project_verified and self.project_id and 0 <= age <= 1 and self.public_demo)
        except ValueError:
            return False
    def limits(self, route):
        return tuple(getattr(self, f"{route}_{k}") for k in ("rpm", "tpm", "rpd"))

