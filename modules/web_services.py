"""
JARVIS — Web Xizmatlari

• Valyuta kurslari   — open.er-api.com (bepul, API key shart emas)
• Yangiliklar        — GNews API (bepul tier) yoki RSS
• Tarjima            — deep-translator (Google Translate bepul)
• Trafik             — nominatim.openstreetmap.org (bepul)
"""
import re
try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_OK = True
except ImportError:
    TRANSLATOR_OK = False


# ══════════════════════════════════════════════════════════════════════
#  VALYUTA KURSLARI
# ══════════════════════════════════════════════════════════════════════
# Til → valyuta kodi xaritasi
CURRENCY_NAMES = {
    "dollar": "USD", "usd": "USD", "amerikan": "USD",
    "euro": "EUR", "evro": "EUR", "yevro": "EUR",
    "rub": "RUB", "rubl": "RUB", "rossiya": "RUB",
    "som": "UZS", "so'm": "UZS", "uzs": "UZS",
    "tenge": "KZT", "kazak": "KZT",
    "lira": "TRY", "turk": "TRY",
    "yuan": "CNY", "xitoy": "CNY",
    "pound": "GBP", "funt": "GBP", "britaniya": "GBP",
    "yen": "JPY", "yapon": "JPY",
    "dirham": "AED", "arab": "AED",
}


def get_currency_rate(from_cur: str = "USD", to_cur: str = "UZS",
                      amount: float = 1.0) -> str:
    """Valyuta kursini olish"""
    if not REQUESTS_OK:
        return "requests kutubxonasi o'rnatilmagan"
    try:
        url  = f"https://open.er-api.com/v6/latest/{from_cur.upper()}"
        resp = requests.get(url, timeout=6)
        data = resp.json()
        if data.get("result") != "success":
            return "Valyuta ma'lumotini olib bo'lmadi"
        rates = data.get("rates", {})
        to_upper = to_cur.upper()
        if to_upper not in rates:
            return f"{to_upper} valyutasi topilmadi"
        rate   = rates[to_upper]
        result = rate * amount
        if result > 1000:
            return (f"1 {from_cur.upper()} = "
                    f"{rate:,.0f} {to_upper}. "
                    f"{amount:g} {from_cur.upper()} = "
                    f"{result:,.0f} {to_upper}")
        else:
            return (f"1 {from_cur.upper()} = "
                    f"{rate:.4f} {to_upper}. "
                    f"{amount:g} {from_cur.upper()} = "
                    f"{result:.4f} {to_upper}")
    except requests.Timeout:
        return "Internetga ulanib bo'lmadi"
    except Exception as e:
        return f"Xato: {e}"


def parse_currency_cmd(cmd: str) -> str:
    """
    Buyruqdan valyuta so'rovini tahlil qilish.
    "dollar kursi qancha" → USD → UZS
    "1000 so'm necha dollar" → UZS → USD, 1000
    "evrodan dollarga" → EUR → USD
    """
    # Miqdorni ajratish
    amount = 1.0
    m = re.search(r'(\d[\d\s,.]*)', cmd)
    if m:
        try:
            amount = float(m.group(1).replace(" ", "").replace(",", "."))
        except ValueError:
            pass

    # Valyutalarni topish
    found = []
    for name, code in CURRENCY_NAMES.items():
        if name in cmd:
            if code not in found:
                found.append(code)

    if not found:
        return "Qaysi valyutani ko'rishni xohlaysiz?"

    from_cur = found[0] if len(found) >= 1 else "USD"
    to_cur   = found[1] if len(found) >= 2 else "UZS"

    # "necha dollar" iborasi bo'lsa — yo'nalishni teskari qilish
    if any(w in cmd for w in ["necha dollar", "necha euro", "necha evro"]):
        from_cur, to_cur = to_cur, from_cur

    return get_currency_rate(from_cur, to_cur, amount)


# ══════════════════════════════════════════════════════════════════════
#  YANGILIKLAR
# ══════════════════════════════════════════════════════════════════════
def get_news(topic: str | None = None, count: int = 3) -> str:
    """
    GNews API dan yangiliklar olish.
    API key: https://gnews.io (bepul 100 so'rov/kun)
    """
    if not REQUESTS_OK:
        return "requests kutubxonasi yo'q"
    try:
        # GNews bepul tier
        if topic:
            url = (f"https://gnews.io/api/v4/search"
                   f"?q={topic}&lang=ru&max={count}"
                   f"&token=demo")
        else:
            url = (f"https://gnews.io/api/v4/top-headlines"
                   f"?lang=ru&max={count}&token=demo")

        resp = requests.get(url, timeout=8)
        data = resp.json()
        articles = data.get("articles", [])

        if not articles:
            return "Yangiliklar topilmadi"

        lines = []
        for i, a in enumerate(articles[:count], 1):
            title = a.get("title", "—")[:100]
            lines.append(f"{i}. {title}")
        return "Bugungi yangiliklar:\n" + "\n".join(lines)

    except Exception as e:
        return f"Yangiliklar olib bo'lmadi: {e}"


def get_news_rss(topic: str | None = None, count: int = 3) -> str:
    """RSS orqali yangiliklar (API key shart emas)"""
    if not REQUESTS_OK:
        return "requests kutubxonasi yo'q"
    try:
        import xml.etree.ElementTree as ET

        if topic:
            url = f"https://news.google.com/rss/search?q={topic}&hl=ru&gl=UZ"
        else:
            url = "https://news.google.com/rss?hl=ru&gl=UZ&ceid=UZ:ru"

        resp = requests.get(url, timeout=8,
                            headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:count]

        if not items:
            return "Yangiliklar topilmadi"

        lines = []
        for i, item in enumerate(items, 1):
            title = item.findtext("title", "—")
            # Google RSS da <source> kelib qo'shiladi — tozalaymiz
            title = re.sub(r'\s*-\s*[^-]+$', '', title)[:90]
            lines.append(f"{i}. {title}")

        return "Yangiliklar:\n" + "\n".join(lines)

    except Exception as e:
        return f"Yangiliklar olib bo'lmadi: {e}"


# ══════════════════════════════════════════════════════════════════════
#  TARJIMA
# ══════════════════════════════════════════════════════════════════════
LANG_MAP = {
    "ingliz": "en", "inglizcha": "en", "english": "en", "en": "en",
    "o'zbek": "uz", "o'zbekcha": "uz", "uzbek": "uz", "uz": "uz",
    "rus": "ru", "ruscha": "ru", "russian": "ru", "ru": "ru",
    "nemis": "de", "nemischa": "de", "german": "de",
    "fransuz": "fr", "fransuzcha": "fr", "french": "fr",
    "arab": "ar", "arabcha": "ar", "arabic": "ar",
    "xitoy": "zh-CN", "xitoycha": "zh-CN", "chinese": "zh-CN",
    "yapon": "ja", "yaponcha": "ja", "japanese": "ja",
    "turk": "tr", "turkcha": "tr", "turkish": "tr",
    "koreys": "ko", "koreyscha": "ko", "korean": "ko",
    "ispan": "es", "ispancha": "es", "spanish": "es",
}


def translate_text(text: str, target_lang: str = "en",
                   source_lang: str = "auto") -> str:
    """
    Matnni tarjima qilish.
    target_lang: 'en', 'ru', 'uz', 'de', ...
    """
    if not TRANSLATOR_OK:
        return "deep-translator o'rnatilmagan: pip install deep-translator"
    if not text.strip():
        return "Tarjima qilish uchun matn yo'q"
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result     = translator.translate(text)
        return result or "Tarjima qilib bo'lmadi"
    except Exception as e:
        return f"Tarjima xatosi: {e}"


def parse_translate_cmd(cmd: str) -> str:
    """
    "hello ni o'zbekchaga tarjima qil" → translate("hello", "uz")
    "bu matnni ruscha tarjima qil" → translate(text, "ru")
    "tarjima qil: ..." → translate(...)
    """
    # Maqsad tilni topish
    target = "en"   # Default
    for lang_name, lang_code in LANG_MAP.items():
        if lang_name in cmd:
            target = lang_code
            break

    # Tarjima qilinishi kerak bo'lgan matnni topish
    text = ""

    # "... ni ... tilga tarjima" yoki "tarjima qil: ..."
    patterns = [
        r'"([^"]+)"\s*(?:ni|ni\s+\w+ga|ga)\s+tarjima',
        r"'([^']+)'\s*(?:ni|ni\s+\w+ga|ga)\s+tarjima",
        r'tarjima\s+qil[^\s]*\s*:?\s+(.+)',
        r'(.+?)\s+(?:ni\s+)?(?:\w+cha|inglizcha|ruscha|o\'zbekcha)\s+tarjima',
    ]
    import re as _re
    for pat in patterns:
        m = _re.search(pat, cmd)
        if m:
            text = m.group(1).strip()
            break

    # Agar matn topilmasa — butun buyruqni tozalaymiz
    if not text:
        cleaned = cmd
        for kw in ["tarjima qil", "tarjima", "qil"]:
            cleaned = cleaned.replace(kw, "")
        for lang_name in LANG_MAP:
            cleaned = cleaned.replace(lang_name, "")
        for suf in ["ga", "ni", "da", "cha"]:
            cleaned = _re.sub(r'\b' + suf + r'\b', '', cleaned)
        text = cleaned.strip(" ,.-'\"") or cmd

    if not text or text == cmd:
        return "Tarjima qilish uchun matnni ko'rsating"

    result = translate_text(text, target)
    return f"Tarjima: {result}"


# ══════════════════════════════════════════════════════════════════════
#  INTERNET TEZLIGI  (oddiy ping orqali)
# ══════════════════════════════════════════════════════════════════════
def check_internet_speed() -> str:
    """Ping orqali internet holati"""
    if not REQUESTS_OK:
        return "requests yo'q"
    try:
        import time
        start = time.time()
        requests.get("https://www.google.com", timeout=5)
        ms = round((time.time() - start) * 1000)
        if ms < 100:
            quality = "yaxshi"
        elif ms < 300:
            quality = "o'rtacha"
        else:
            quality = "sekin"
        return f"Internet {quality}, ping {ms} ms"
    except requests.Timeout:
        return "Internet ulanish yo'q"
    except Exception:
        return "Internet holati noma'lum"
