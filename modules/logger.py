"""
JARVIS — Loglash moduli
Barcha buyruqlar, xatolar va hodisalar logs/ papkaga yoziladi
"""
import logging
import os
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setup_logger() -> logging.Logger:
    log_dir = os.path.join(_BASE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"jarvis_{datetime.now().strftime('%Y-%m-%d')}.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.WARNING)   # Konsolga faqat ogohlantirish+

    log = logging.getLogger("jarvis")
    if not log.handlers:           # Ikki marta qo'shilmasin
        log.setLevel(logging.DEBUG)
        log.addHandler(fh)
        log.addHandler(ch)
    return log


logger = setup_logger()
