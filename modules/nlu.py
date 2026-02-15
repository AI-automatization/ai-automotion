"""
JARVIS — Natural Language Understanding
normalize, wake word, intent detection, contact match, AI validation
"""
import re, json
from typing import Optional, Tuple

# ── Wake so'zlar ──────────────────────────────────────────
WAKE_WORDS = {"jarvis", "джарвис", "жарвис", "jarwis", "jarvas", "garvis"}

# ── O'zbek morfologiya — suffix pattern ──────────────────
_UZ_SUFFIXES = (
    r"(?:"
    r"ng(?:ga|ni|dan|ning|da)?"   # onang, onangga, onangni
    r"|im(?:ga|ni|dan|ning|da)?"  # onam, otamga
    r"|ing(?:ga|ni|dan)?"
    r"|si(?:ga|ni|dan)?"
    r"|m(?:ga|ni|dan)?"
    r"|lar(?:ni|ga|dan)?"
    r"|ga|ni|dan|ning|da|ka|am|an"
    r")?"
)

# ── Kiril → Lotin ─────────────────────────────────────────
_CYR = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo',
    'ж':'j','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m',
    'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
    'ф':'f','х':'x','ц':'ts','ч':'ch','ш':'sh','щ':'sh',
    'ъ':"'",'ы':'i','ь':"'",'э':'e','ю':'yu','я':'ya',
    'қ':'q','ғ':'g','ҳ':'h','ў':"o'",
}


def normalize_text(text: str) -> str:
    """Kiril → Lotin, kichik harf, tozalash — Bug #8"""
    # Unicode apostroflarni normallashtirish
    text = text.replace('\u2019', "'").replace('\u2018', "'").replace('\u02bc', "'")
    result = []
    for ch in text.lower():
        result.append(_CYR.get(ch, ch))
    text = re.sub(r'\s+', ' ', ''.join(result)).strip()
    # STT xatoliklarini tuzatish
    STT_FIXES = {
        "tayyor qo'y": "taymer qo'y",
        "tayyor qoy":  "taymer qo'y",
        "tayyor koy":  "taymer qo'y",
        "tayyor ko'y": "taymer qo'y",
    }
    for wrong, correct in STT_FIXES.items():
        if wrong in text and any(w in text for w in ["daqiqa","soat","sekund","minut"]):
            text = text.replace(wrong, correct)
    # 'tayyor' yolg'iz holda ham taymer
    if "tayyor" in text and any(w in text for w in ["daqiqa","soat","sekund","minut"]):
        text = text.replace("tayyor", "taymer")
    return text


def is_wake_word(text: str) -> bool:
    return bool(set(text.lower().split()) & WAKE_WORDS)


def is_stop_command(text: str) -> bool:
    """Bug #6: Aniq stop buyruq — "ilovani yop" bilan chalkashmaslik"""
    EXACT = {
        "xayr", "dasturni yop", "jarvis yopil", "yopil",
        "quit", "exit", "stop jarvis", "ketdim", "off",
    }
    low = text.lower().strip()
    if low in EXACT:
        return True
    words = set(low.split())
    PAIRS = [("xayr", "jarvis"), ("jarvis", "yopil"), ("dasturni", "yop")]
    return any(a in words and b in words for a, b in PAIRS)


def contact_match(name: str, cmd: str) -> bool:
    """
    Bug #5 fix: O'zbek suffix bilan to'g'ri moslashtirish
    "ona" → "onaga" ✓, "onang" ✓  |  "abdulazizovka" ✗
    """
    pattern = r"(?<!\w)" + re.escape(name.lower()) + _UZ_SUFFIXES + r"(?!\w)"
    return bool(re.search(pattern, cmd.lower()))


def needs_realtime(cmd: str) -> Optional[str]:
    """Internet kerak bo'lgan so'rovlarni aniqlash"""
    if any(w in cmd for w in ["ob-havo", "havo", "harorat", "yomg'ir", "qor"]):
        return "weather"
    CURRENCY = {"dollar","euro","evro","rubl","so'm","kurs","valyuta","tenge","lira","yuan"}
    if any(w in cmd for w in CURRENCY):
        return "currency"
    if any(w in cmd for w in ["yangilik", "xabar", "news"]):
        return "news"
    if any(w in cmd for w in ["soat", "vaqt", "nechchi"]):
        return "time"
    return None


# ── Intent map — (intent, keywords[]) ─────────────────────
_INTENTS: list[tuple[str, list[str]]] = [
    # Vaqt/sana
    ("date",          ["sana", "kun necha", "bugun necha", "qaysi kun"]),

    # Tizim
    ("screenshot",    ["screenshot", "ekran surat", "skrinshot"]),
    ("stats",         ["cpu", "ram", "batareya", "xotira", "disk", "tizim holati"]),
    ("internet",      ["internet", "ping", "tarmoq tezligi"]),

    # Kompyuter
    ("shutdown",      ["kompyuterni o'chir", "shutdown"]),
    ("restart",       ["qayta yoq", "restart", "reboot"]),
    ("sleep",         ["uxlat", "sleep"]),
    ("lock",          ["ekranni qulf", "qulfla", "lock"]),

    # Ovoz (volume so'zi ham ketadi)
    ("volume",        ["ovoz"]),

    # Media
    ("media_next",    ["keyingi qo'shiq", "keyingisi"]),
    ("media_prev",    ["oldingi qo'shiq", "oldingisi"]),
    ("media_pause",   ["musiqani pauza", "to'xtat musiqa"]),
    ("media_play",    ["musiqani davom", "davom et musiqa"]),

    # Oyna
    ("win_min_all",   ["barcha oynalarni", "hammasini minimal"]),
    ("win_minimize",  ["minimlashtir", "kichrayt"]),
    ("win_maximize",  ["to'liq ekran", "kattalashtir", "maximize"]),
    ("win_close",     ["oynani yop", "oynani o'chir"]),

    # Fayllar
    ("folder_open",   ["papkani och", "papka och", "ochib ko'rsat"]),
    ("file_recent",   ["oxirgi fayl", "so'nggi fayl", "yuklanganlar"]),

    # Eslatmalar
    ("reminder_list", ["eslatmalarni ko'rsat", "eslatmalar ro'yxat"]),
    ("reminder",      ["eslatib qo'y", "eslatma", "reminder", "daqiqadan keyin",
                       "taymer", "taymer qo'y", "daqiqaga", "soatga", "sekundga"]),

    # Vazifalar
    ("task_add",      ["vazifa qo'sh", "todo qo'sh"]),
    ("task_list",     ["vazifalarni ko'rsat", "vazifalar ro'yxat", "todo ro'yxat"]),
    ("task_done",     ["bajarildi", "vazifani tugatdim"]),

    # Kundalik
    ("journal_add",   ["kundalikka yoz", "kundalikka"]),
    ("journal_read",  ["kundalikni ko'rsat", "bugungi kundalik"]),

    # Xotira
    ("memory_save",   ["eslab qol", "xotirla", "yodlab qol"]),
    ("memory_read",   ["nimani eslab qolding", "xotirangni ko'rsat"]),

    # Boshqa
    ("translate",     ["tarjima", "translate"]),
    ("youtube",       ["youtube", "yutub", "utub", "qo'shiq qo'y"]),
    ("clipboard",     ["clipboard", "nusxalangan"]),
    ("processes",     ["jarayonlar", "qaysi dasturlar", "processlar"]),
    ("settings",      ["sozlamalar", "settings", "konfiguratsiya"]),
    ("history",       ["tarixi", "history", "avvalgi buyruqlar"]),
    ("dashboard",     ["dashboard", "panel", "statistika oyna"]),
]


def match_local_intent(cmd: str) -> Optional[str]:
    """Buyruqdan intent topish"""
    low = cmd.lower()
    for intent, keywords in _INTENTS:
        if any(kw in low for kw in keywords):
            return intent
    return None


def parse_ai_json(raw: str) -> dict:
    """AI JSON javobini xavfsiz parse qilish"""
    cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip().strip('`')
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if m:
            try: return json.loads(m.group())
            except Exception: pass
    return {"type": "answer", "speak": raw[:200], "confidence": 0.5}


def validate_ai_response(resp: dict) -> Tuple[bool, str]:
    """Bug #7: AI xavfli buyruq tekshiruvi"""
    if resp.get("type") != "command":
        return True, ""
    action     = resp.get("action", "")
    confidence = float(resp.get("confidence", 1.0))
    DANGEROUS  = {"shutdown", "restart", "delete_file", "kill_process", "format"}
    KNOWN      = {"open_app","volume","shutdown","restart","screenshot",
                  "kill_process","minimize","maximize","lock","sleep","clipboard"}
    if action in DANGEROUS and confidence < 0.90:
        return False, f"Ishonch past ({confidence:.0%})"
    if action and action not in KNOWN:
        return False, f"Noma'lum amal: {action}"
    return True, ""

