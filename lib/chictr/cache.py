"""简易文件缓存：cache/chictr/{key}.json"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "cache" / "chictr"


def _key_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


class FileCache:
    def __init__(self, root: str | Path | None = None, ttl_seconds: int = 3600) -> None:
        self.root = Path(root) if root else _DEFAULT_DIR
        self.ttl = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Any | None:
        path = self.root / f"{_key_hash(key)}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - float(data.get("ts", 0)) > self.ttl:
                return None
            return data.get("value")
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        path = self.root / f"{_key_hash(key)}.json"
        payload = {"ts": time.time(), "key": key, "value": value}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
