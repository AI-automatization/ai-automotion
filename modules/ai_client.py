"""
JARVIS — AI Client
Claude singleton, rate limiting, timeout, xavfsiz bajarish
"""
import threading
from modules.core import State, state_manager, rate_limiter, with_timeout
from modules.nlu import parse_ai_json, validate_ai_response

try:
    import anthropic; AN_OK = True
except ImportError:
    AN_OK = False

_client      = None
_client_lock = threading.Lock()
_history     : list[dict] = []

AI_SYSTEM_PROMPT = """Siz JARVIS — Windows kompyuter yordamchisiz.
Har doim FAQAT JSON formatida javob bering.

Buyruq uchun:
{"type":"command","action":"ACTION","params":{},"speak":"Bajarildi","confidence":0.95}

Mavjud actionlar:
- open_app    : {"app": "chrome"}
- volume      : {"level": 50}
- shutdown/restart/sleep/lock/screenshot : {}
- kill_process: {"name": "chrome.exe"}
- get_sysinfo : {"query": "os|cpu|ram|disk|battery|ip|hostname"}

Savol/suhbat uchun:
{"type":"answer","speak":"Qisqa javob o'zbek tilida (max 2 jumla)","confidence":0.9}

Tushunilmasa:
{"type":"unknown","speak":"Tushunmadim, qaytadan ayting","confidence":0.1}

QOIDALAR:
- FAQAT JSON — hech qanday boshqa matn, markdown emas
- speak: max 2 jumla, faqat o'zbek tilida
- Tizim ma'lumoti so'ralganda get_sysinfo ishlat
- confidence: 0.0-1.0"""


def _get_client():
    global _client
    from config import CLAUDE_API_KEY
    with _client_lock:
        if _client is None and AN_OK and CLAUDE_API_KEY:
            try:
                _client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            except Exception:
                pass
    return _client


def ask_ai(question: str) -> dict:
    """
    Xavfsiz AI chaqiruv
    Bug #2: 12s timeout
    Bug #12: rate limiting
    """
    from config import CLAUDE_API_KEY
    from modules.logger import logger

    if not AN_OK:
        return {"type": "answer", "speak": "AI moduli o'rnatilmagan", "confidence": 0}
    if not CLAUDE_API_KEY or CLAUDE_API_KEY in ("", "YOUR_ANTHROPIC_API_KEY"):
        return {"type": "answer", "speak": "Claude API kaliti sozlanmagan", "confidence": 0}

    # Bug #12: Rate limit
    if not rate_limiter.wait_if_needed(block=False):
        return {"type": "answer", "speak": "Biroz kuting", "confidence": 0}

    state_manager.set(State.PROCESSING)

    def _call():
        client = _get_client()
        if not client:
            raise RuntimeError("Client yo'q")
        _history.append({"role": "user", "content": question})
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=AI_SYSTEM_PROMPT,
            messages=_history[-8:]
        )
        return resp.content[0].text

    try:
        # Bug #2: 12s timeout
        raw = with_timeout(_call, timeout_sec=12, default=None)

        if raw is None:
            return {"type": "answer", "speak": "Internet sekin, qayta urining", "confidence": 0}

        result = parse_ai_json(raw)
        _history.append({"role": "assistant", "content": raw})
        logger.info(f"AI: {question[:40]} → {result.get('speak','')[:40]}")
        return result

    except Exception as e:
        logger.error(f"Claude xatosi: {e}")
        err = str(e)
        if "401" in err: return {"type": "answer", "speak": "API kalit noto'g'ri", "confidence": 0}
        if "429" in err: return {"type": "answer", "speak": "Juda ko'p so'rov, kuting", "confidence": 0}
        return {"type": "answer", "speak": "Texnik xato yuz berdi", "confidence": 0}
    finally:
        state_manager.set(State.IDLE)


def clear_history():
    global _history
    _history = []
