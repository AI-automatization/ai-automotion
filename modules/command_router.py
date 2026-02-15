"""
JARVIS — Buyruq Router

Handler'larni kalit so'zlar orqali ro'yxatdan o'tkazadi va buyruqni
moslashtiradi. process_command() ni 50+ if/elif bloklardan xalos qiladi.

Foydalanish:
    from modules.command_router import register, route

    @register("soat", "vaqt", "nechchi")
    def handle_time(cmd: str) -> str | None:
        return get_time()

    matched = route(cmd, speak_fn, record_fn)
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger("jarvis")

# ── Handler turi ─────────────────────────────────────────────────────
# (keywords_tuple, handler_fn, exact_match)
# exact_match=True: faqat bitta kalit so'z bo'lsa emas, birorta bo'lsa
_handlers: list[tuple[tuple[str, ...], Callable[[str], str | None | bool], bool]] = []


def register(*keywords: str, exact: bool = False):
    """
    Decorator: handler funksiyani belgilangan kalit so'zlar bilan bog'laydi.

    Handler qaytarishi mumkin:
      - str       → speak + record qilinadi
      - None      → hech narsa qilmaydi (handler o'zi speak qiladi)
      - False     → dasturni yopish signali (exit buyruqlari uchun)
    """
    def decorator(fn: Callable) -> Callable:
        _handlers.append((keywords, fn, exact))
        return fn
    return decorator


def route(cmd: str, speak_fn: Callable[[str], None],
          record_fn: Callable[[str, str], None]) -> bool | None:
    """
    Buyruqni mos handler'ga yo'naltiradi.

    Qaytaradi:
      True  → buyruq topildi va bajarildi, davom et
      False → chiqish kerak
      None  → hech bir handler mos kelmadi (AI fallback uchun)
    """
    low = cmd.lower()
    for keywords, fn, exact in _handlers:
        if exact:
            matched = any(low == kw for kw in keywords)
        else:
            matched = any(kw in low for kw in keywords)

        if matched:
            try:
                result = fn(cmd)
            except Exception as e:
                logger.error(f"Handler xatosi [{fn.__name__}]: {e}")
                speak_fn("Buyruqni bajarishda xato yuz berdi")
                record_fn(cmd, f"[xato: {e}]")
                return True

            if result is False:
                return False
            if isinstance(result, str):
                speak_fn(result)
                record_fn(cmd, result)
            return True

    return None  # Hech narsa mos kelmadi
