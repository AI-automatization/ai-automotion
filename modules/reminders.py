"""
JARVIS — Eslatmalar (Reminder) moduli

Foydalanish:
  set_reminder(seconds=1800, message="Choy iching", speak_fn=speak)
  list_reminders()   → [(id, vaqt_qoldi, xabar), ...]
  cancel_reminder(id)
"""
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

try:
    from win10toast import ToastNotifier
    _TOAST = ToastNotifier()
    TOAST_OK = True
except ImportError:
    TOAST_OK = False

# Faol eslatmalar: {id: {"timer": Timer, "msg": str, "fire_at": datetime}}
_reminders: dict[int, dict] = {}
_lock = threading.Lock()
_next_id = 1


def _notify(message: str, speak_fn: Optional[Callable] = None):
    """Eslatma vaqti kelganda chaqiriladi"""
    print(f"\n⏰ ESLATMA: {message}\n")

    # Windows toast
    if TOAST_OK:
        try:
            _TOAST.show_toast(
                "JARVIS Eslatma",
                message,
                duration=8,
                threaded=True
            )
        except Exception:
            pass

    # Ovozli bildirishnoma
    if speak_fn:
        try:
            speak_fn(f"Eslatma: {message}")
        except Exception:
            pass


def set_reminder(seconds: int, message: str,
                 speak_fn: Optional[Callable] = None) -> int:
    """
    Eslatma o'rnatish.
    Returns: eslatma ID si
    """
    global _next_id
    rid = _next_id
    _next_id += 1

    fire_at = datetime.now() + timedelta(seconds=seconds)
    timer = threading.Timer(seconds, _notify, args=(message, speak_fn))
    timer.daemon = True

    with _lock:
        _reminders[rid] = {
            "timer": timer,
            "msg": message,
            "fire_at": fire_at
        }

    timer.start()
    return rid


def cancel_reminder(rid: int) -> bool:
    with _lock:
        if rid in _reminders:
            _reminders[rid]["timer"].cancel()
            del _reminders[rid]
            return True
    return False


def list_reminders() -> list[tuple[int, int, str]]:
    """[(id, sekundlar_qoldi, xabar), ...]"""
    now = datetime.now()
    rows: list[tuple[int, int, str]] = []

    with _lock:
        for rid, info in list(_reminders.items()):
            diff = (info["fire_at"] - now).total_seconds()
            if diff > 0:
                rows.append((rid, int(diff), info["msg"]))
            else:
                del _reminders[rid]  # O'tib ketgan

    return sorted(rows, key=lambda x: x[1])


def format_time_left(seconds: int) -> str:
    """Qolgan vaqtni matnga aylantirish"""
    if seconds < 60:
        return f"{seconds} soniya"
    if seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"{m} daqiqa{(' ' + str(s) + ' soniya') if s else ''}"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h} soat{(' ' + str(m) + ' daqiqa') if m else ''}"


# ── Vaqtni buyruqdan ajratib olish ────────────────────────────────────
def parse_duration(cmd: str) -> Optional[int]:
    """
    "30 daqiqadan keyin" → 1800
    "2 soatdan keyin"    → 7200
    "45 sekunddan keyin" → 45
    "ertaga soat 9 da"   → soniyalar soni (bugundan)
    None → topa olmadi
    """
    cmd = cmd.lower()

    # "soat X da" — absolyut vaqt
    m = re.search(r"soat\s+(\d{1,2})(?::(\d{2}))?\s*da", cmd)
    if m:
        target_h = int(m.group(1))
        target_m = int(m.group(2) or 0)
        now = datetime.now()
        target = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)  # Ertaga
        return int((target - now).total_seconds())

    # Nisbiy vaqt
    patterns = [
        (r"(\d+)\s*soat", 3600),
        (r"(\d+)\s*daqiqa", 60),
        (r"(\d+)\s*soniya", 1),
        (r"(\d+)\s*minut", 60),
        (r"(\d+)\s*hour", 3600),
        (r"(\d+)\s*minute", 60),
        (r"(\d+)\s*second", 1),
    ]
    for pattern, multiplier in patterns:
        m = re.search(pattern, cmd)
        if m:
            return int(m.group(1)) * multiplier

    return None


def parse_reminder_message(cmd: str) -> str:
    """
    Buyruqdan eslatma matnini ajratib olish

    Misollar:
    - "30 daqiqadan keyin choy ich" → "choy ich"
    - "soat 15 da yig'ilish bor, eslatib qo'y" → "yig'ilish bor"
    """
    original = cmd.strip()
    low = original.lower()

    # 1) Agar "eslatib qo'y" kabi triggerdan keyin matn bo'lsa, o'shani olish
    triggers = ["eslatib qo'y", "eslatib qoy", "eslatma qo'y", "eslatma qoy", "reminder"]
    for kw in triggers:
        idx = low.find(kw)
        if idx != -1:
            before = original[:idx].strip(" ,.-")
            after = original[idx + len(kw):].strip(" ,.-")

            # Odatda foydali matn triggerdan oldin bo'ladi:
            # "soat 15 da yig'ilish bor, eslatib qo'y"
            if before:
                candidate = before
            else:
                candidate = after

            if candidate:
                # vaqt qismlarini tozalab beramiz
                candidate = re.sub(
                    r"\d+\s*(soat|daqiqa|soniya|minut|hour|minute|second)dan?\s*keyin",
                    "",
                    candidate,
                    flags=re.IGNORECASE
                )
                candidate = re.sub(r"soat\s+\d{1,2}(:\d{2})?\s*da", "", candidate, flags=re.IGNORECASE)
                candidate = re.sub(r"\b(keyin)\b", "", candidate, flags=re.IGNORECASE)
                return candidate.strip(" ,.-") or "Eslatma!"

    # 2) Trigger bo'lmasa: vaqt qismlarini olib tashlash
    cleaned = original
    cleaned = re.sub(
        r"\d+\s*(soat|daqiqa|soniya|minut|hour|minute|second)dan?\s*keyin",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"soat\s+\d{1,2}(:\d{2})?\s*da", "", cleaned, flags=re.IGNORECASE)

    # 3) Keywordlarni olib tashlash (qo'y / qoy / eslatma...)
    cleaned = re.sub(
        r"\b(eslatib|eslatma|reminder|keyin|qo'y|qoy)\b",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    return cleaned.strip(" ,.-") or "Eslatma!"
