"""
JARVIS — Buyruqlar tarixi
"""
import datetime, threading

_history : list[tuple[str, str, str]] = []
_lock    = threading.Lock()
MAX_SIZE = 200


def record(cmd: str, resp: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    with _lock:
        _history.append((ts, cmd, resp))
        if len(_history) > MAX_SIZE:
            _history.pop(0)
    from modules.logger import logger
    logger.info(f"CMD: {cmd} | RESP: {resp[:60]}")


def get_recent(n: int = 50) -> list[tuple[str, str, str]]:
    with _lock:
        return list(_history[-n:])


def get_last() -> tuple | None:
    with _lock:
        return _history[-1] if _history else None


def clear():
    with _lock:
        _history.clear()
