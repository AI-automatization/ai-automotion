"""
JARVIS — Core: State, MicGuard, Cache, RateLimiter, TempManager
"""
import os, time, threading, tempfile, atexit
from enum import Enum
from typing import Any, Callable, Optional


# ══════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════
class State(Enum):
    IDLE       = "idle"
    LISTENING  = "listening"
    SPEAKING   = "speaking"
    PROCESSING = "processing"
    BACKGROUND = "background"


class StateManager:
    def __init__(self):
        self._lock       = threading.RLock()
        self._state      = State.BACKGROUND
        self._changed_at = time.time()
        self._callbacks  : list[Callable] = []
        # Bug #1 fix: gapirish davomida wake word bloki
        self.is_speaking = threading.Event()

    def set(self, new: State):
        with self._lock:
            if self._state == new:
                return
            self._state      = new
            self._changed_at = time.time()
            if new == State.SPEAKING:
                self.is_speaking.set()
        for cb in self._callbacks:
            try: cb(new)
            except Exception: pass

    def get(self) -> State:
        with self._lock:
            return self._state

    def on_change(self, cb: Callable):
        self._callbacks.append(cb)

    def elapsed(self) -> float:
        """Joriy holatda qancha vaqt o'tdi (soniya)"""
        with self._lock:
            return time.time() - self._changed_at


# ══════════════════════════════════════════════════════════
#  MIC GUARD  — Bug #3 fix
# ══════════════════════════════════════════════════════════
class MicGuard:
    """Mikrofon resource leak oldini olish"""
    def __init__(self, sr_module):
        self._sr  = sr_module
        self._src = None

    def __enter__(self):
        self._src = self._sr.Microphone()
        return self._src.__enter__()

    def __exit__(self, *args):
        if self._src:
            try: self._src.__exit__(*args)
            except Exception: pass
            self._src = None


# ══════════════════════════════════════════════════════════
#  TIMEOUT — Bug #2 fix
# ══════════════════════════════════════════════════════════
def with_timeout(func: Callable, timeout_sec: float, default: Any = None) -> Any:
    """Thread orqali timeout bilan chaqirish"""
    result = [default]
    exc    = [None]

    def _run():
        try:    result[0] = func()
        except Exception as e: exc[0] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout_sec)

    if t.is_alive():
        return default
    if exc[0]:
        raise exc[0]
    return result[0]


# ══════════════════════════════════════════════════════════
#  RATE LIMITER — Bug #12 fix
# ══════════════════════════════════════════════════════════
class RateLimiter:
    def __init__(self, max_calls: int = 15, window_sec: float = 60.0):
        self._max    = max_calls
        self._window = window_sec
        self._calls  : list[float] = []
        self._lock   = threading.Lock()

    def wait_if_needed(self, block: bool = True) -> bool:
        with self._lock:
            now = time.time()
            self._calls = [c for c in self._calls if now - c < self._window]

            if len(self._calls) < self._max:
                self._calls.append(now)
                return True

            if not block:
                return False

            wait = self._window - (now - self._calls[0])
            if wait > 0:
                time.sleep(min(wait, 5.0))
            self._calls = [c for c in self._calls
                           if time.time() - c < self._window]
            self._calls.append(time.time())
            return True


# ══════════════════════════════════════════════════════════
#  SMART CACHE — Bug #9 fix
# ══════════════════════════════════════════════════════════
class SmartCache:
    _TTL = {"weather": 600, "currency": 300, "news": 120, "default": 60}

    def __init__(self):
        self._data : dict[str, tuple] = {}
        self._lock = threading.Lock()

    def get(self, key: str, category: str = "default") -> Optional[Any]:
        with self._lock:
            if key in self._data:
                value, ts, cat = self._data[key]
                ttl = self._TTL.get(cat, 60)
                if time.time() - ts < ttl:
                    return value
                del self._data[key]
        return None

    def set(self, key: str, value: Any, category: str = "default"):
        with self._lock:
            self._data[key] = (value, time.time(), category)

    def clear(self, category: Optional[str] = None):
        with self._lock:
            if category:
                self._data = {k: v for k, v in self._data.items()
                              if v[2] != category}
            else:
                self._data.clear()


# ══════════════════════════════════════════════════════════
#  TEMP FILE MANAGER — Bug #11 fix
# ══════════════════════════════════════════════════════════
class TempFileManager:
    def __init__(self):
        self._files: set[str] = set()
        self._lock  = threading.Lock()
        atexit.register(self.cleanup_all)

    def create(self, suffix: str = ".mp3") -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
            path = fp.name
        with self._lock:
            self._files.add(path)
        return path

    def delete(self, path: str):
        try: os.unlink(path)
        except Exception: pass
        with self._lock:
            self._files.discard(path)

    def cleanup_all(self):
        with self._lock:
            for p in list(self._files):
                try: os.unlink(p)
                except Exception: pass
            self._files.clear()


# ── Singletonlar ──────────────────────────────────────────
state_manager = StateManager()
rate_limiter  = RateLimiter(max_calls=15, window_sec=60)
smart_cache   = SmartCache()
temp_manager  = TempFileManager()
