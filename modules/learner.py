import re
"""
JARVIS — O'z-o'zini o'rgatish moduli
- Foydalanuvchi buyruqlarini eslab qoladi
- STT xatolarini o'rganadi
- Offline cache
"""
import json, os
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
os.makedirs(_DATA, exist_ok=True)

LEARNED_FILE  = os.path.join(_DATA, "learned_commands.json")
STT_FIX_FILE  = os.path.join(_DATA, "stt_patterns.json")
OFFLINE_FILE  = os.path.join(_DATA, "offline_cache.json")


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Buyruqni o'rganish ────────────────────────────────────
def learn_command(raw_cmd: str, intent: str, success: bool):
    """Har bir buyruqni saqlaydi"""
    data = _load(LEARNED_FILE, {})
    key  = raw_cmd.strip().lower()
    if key not in data:
        data[key] = {"intent": intent, "count": 0, "success": 0}
    data[key]["count"]   += 1
    data[key]["success"] += 1 if success else 0
    data[key]["last"]     = datetime.now().isoformat()
    _save(LEARNED_FILE, data)


# ── STT xatosini o'rganish ────────────────────────────────
def learn_stt_fix(wrong: str, correct: str):
    """
    Agar foydalanuvchi bir xil noto'g'ri so'zni qayta-qayta aytsa,
    avtomatik tuzatish sifatida saqlaydi
    """
    data = _load(STT_FIX_FILE, {})
    if wrong not in data:
        data[wrong] = {"correct": correct, "count": 0}
    data[wrong]["count"] += 1
    _save(STT_FIX_FILE, data)


def get_stt_fixes() -> dict:
    """O'rganilgan STT tuzatishlarini qaytaradi"""
    return {k: v["correct"] for k, v in _load(STT_FIX_FILE, {}).items()}


# ── Offline cache ─────────────────────────────────────────
# Dinamik ma'lumotlar — cache saqlanmaydi
DYNAMIC_ACTIONS = {"get_sysinfo", "processes", "screenshot", "internet"}
DYNAMIC_QUERIES = {"processes", "cpu", "ram", "battery", "ip"}

def cache_ai_response(cmd: str, response: str, action: str = "", params: dict = None):
    """
    Faqat statik javoblarni cache ga saqlaydi.
    Dinamik: cpu, ram, processes, battery — saqlanmaydi
    """
    if params is None:
        params = {}

    # Dinamik actionlarni o'tkazib yuborish
    if action in DYNAMIC_ACTIONS:
        return
    if params.get("query") in DYNAMIC_QUERIES:
        return
    # Vaqt/sana ham dinamik
    if any(w in cmd for w in ["vaqt", "soat", "sana", "bugun", "hozir"]):
        return

    data = _load(OFFLINE_FILE, {})
    key = re.sub(r'[?!.,]', '', cmd.lower().strip())
    data[key] = {
        "response": response,
        "saved":    datetime.now().isoformat()
    }
    if len(data) > 500:
        oldest = sorted(data.items(), key=lambda x: x[1]["saved"])
        for k, _ in oldest[:50]:
            del data[k]
    _save(OFFLINE_FILE, data)


def get_cached_response(cmd: str) -> str | None:
    """Offline cache dan javob qidiradi"""
    # Dinamik so'rovlarni cache dan o'tkazmaymiz
    if any(w in cmd for w in ["orqa fonda", "jarayon", "process", "cpu", "ram",
                               "batareya", "vaqt", "soat", "sana", "hozir", "ip"]):
        return None

    data  = _load(OFFLINE_FILE, {})
    key   = re.sub(r'[?!.,]', '', cmd.lower().strip())
    if key in data:
        return data[key]["response"]
    for saved_cmd, val in data.items():
        words       = set(key.split())
        saved_words = set(saved_cmd.split())
        overlap     = len(words & saved_words)
        if overlap >= 3 and overlap / max(len(words), 1) > 0.7:
            return val["response"]
    return None


def get_stats() -> str:
    """O'rganish statistikasi"""
    learned = _load(LEARNED_FILE, {})
    cached  = _load(OFFLINE_FILE, {})
    fixes   = _load(STT_FIX_FILE, {})
    return (f"O'rganilgan buyruqlar: {len(learned)}, "
            f"Offline cache: {len(cached)}, "
            f"STT tuzatishlar: {len(fixes)}")
