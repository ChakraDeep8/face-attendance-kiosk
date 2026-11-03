from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os, sys

@dataclass(frozen=True)
class Settings:
    data_root: Path
    token: str
    model_name: str = "buffalo_s"
    model_root: Path = Path("models")

    @classmethod
    def load(cls) -> "Settings":
        root = Path(os.getenv("VERITY_DATA_ROOT", Path.home() / "AppData/Local/Verity"))
        root.mkdir(parents=True, exist_ok=True)
        (root / "faces").mkdir(exist_ok=True)
        (root / "alerts").mkdir(exist_ok=True)
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        model_root = Path(os.getenv("VERITY_MODEL_ROOT", bundle_root / "models"))
        model_root.mkdir(parents=True, exist_ok=True)
        return cls(root, os.getenv("VERITY_TOKEN", "development-token"), os.getenv("VERITY_MODEL", "buffalo_s"), model_root)

settings = Settings.load()
