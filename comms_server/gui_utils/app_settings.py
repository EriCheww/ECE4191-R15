from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict
from threading import RLock
from typing import Callable, Dict, Any, List

DEFAULTS: Dict[str, Any] = {
    "ss_save_directory": str(Path.home() / "Screenshots"),
    "ss_user_prefix": "user",
    "console_log_length": "2000",  
}

class Settings:
    def __init__(self, path: str | Path):
        self._path = Path(path).expanduser()
        self._data: Dict[str, Any] = DEFAULTS.copy()
        self._subs: Dict[str, List[Callable[[str, Any, Any], None]]] = defaultdict(list)
        self._subs_all: List[Callable[[str, Any, Any], None]] = []
        self._lock = RLock()
        self.load()  # load if file exists

    # ----- persistence -----
    def load(self):
        if self._path.exists():
            try:
                self._data.update(json.loads(self._path.read_text()))
            except Exception:
                pass  # ignore corrupt file; keep defaults

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    # ----- accessors -----
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any, *, persist: bool = True, notify: bool = True):
        with self._lock:
            old = self._data.get(key)
            if old == value:
                return
            self._data[key] = value
            if persist:
                self.save()
        if notify:
            for cb in list(self._subs.get(key, [])):
                try: cb(key, value, old)
                except Exception: pass
            for cb in list(self._subs_all):
                try: cb(key, value, old)
                except Exception: pass

    # ----- subscriptions -----
    def subscribe(self, key: str, callback: Callable[[str, Any, Any], None]):
        self._subs[key].append(callback)

    def subscribe_all(self, callback: Callable[[str, Any, Any], None]):
        self._subs_all.append(callback)

# Singleton used across the app
CONFIG_PATH = Path(__file__).resolve().parents[1] / ".app_config.json"
settings = Settings(path=str(CONFIG_PATH))
