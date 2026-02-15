#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║     JARVIS v4  —  Bug-Safe Arxitektura                              ║
║     Barcha 12 bug oldini olingan                                    ║
╚══════════════════════════════════════════════════════════════════════╝

TUZATILGAN BUGLAR:
  #1  Echo Loop          → is_speaking.Event + pauza
  #2  PROCESSING stuck   → 15s timeout + StateManager
  #3  Mic resource leak  → MicGuard context manager
  #4  Thread-unsafe state → RLock + StateManager
  #5  AI "Jarvis" trigger → wake listener pauza
  #6  Stop so'z context  → is_stop_command() aniq tekshirish
  #7  AI xavfli buyruq   → validate_ai_response()
  #8  STT Kiril/Lotin    → normalize_text()
  #9  Cache eskirgan     → SmartCache TTL
  #10 Ikki kishi gapirsa → phrase_limit + so'z soni chek
  #11 Temp fayl leak     → TempFileManager + atexit
  #12 AI rate limit      → RateLimiter
"""

import os, sys, json, time, asyncio, subprocess, webbrowser
import datetime, re, glob, threading, socket
import math, queue
import tkinter as tk
from tkinter import Canvas, ttk, messagebox

# ── .env yuklash ─────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

# ── Kutubxonalar ─────────────────────────────────────────
try:
    import speech_recognition as sr; SR_OK = True
except ImportError:
    sr = None; SR_OK = False

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    PG_OK = True
except ImportError:
    PG_OK = False

try:
    import edge_tts; ET_OK = True
except ImportError:
    ET_OK = False

try:
    import requests; RQ_OK = True
except ImportError:
    RQ_OK = False

try:
    import anthropic; AN_OK = True
except ImportError:
    AN_OK = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False; PA_OK = True
except ImportError:
    PA_OK = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL; PCW_OK = True
except Exception:
    PCW_OK = False

# ── Modullar ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from modules.core import (
    State, StateManager, MicGuard, with_timeout,
    RateLimiter, SmartCache, TempFileManager,
    state_manager, rate_limiter, smart_cache, temp_manager
)
from modules.nlu import (
    normalize_text, is_stop_command, is_wake_word,
    needs_realtime, match_local_intent,
    parse_ai_json, validate_ai_response,
    WAKE_WORDS
)
from modules.logger        import logger
from modules.memory_manager import (
    save_memory, get_memory, get_all_memory, forget,
    add_journal, get_journal, get_recent_journal,
    add_task, complete_task, get_tasks, delete_task, format_tasks_text
)
from modules.reminders import (
    set_reminder, cancel_reminder, list_reminders,
    parse_duration, parse_reminder_message, format_time_left
)
from modules.media_control import (
    media_play_pause, media_next, media_prev, media_stop,
    minimize_window, maximize_window, close_window,
    list_open_windows, minimize_all_windows,
    get_clipboard, set_clipboard, kill_process_by_name
)
from modules.web_services import (
    get_currency_rate, parse_currency_cmd,
    get_news_rss, parse_translate_cmd, check_internet_speed
)
from modules.file_manager import (
    open_folder, parse_folder_from_cmd,
    get_recent_download, kill_process, format_system_stats,
    get_system_stats as fm_get_stats,
    DOWNLOADS, DESKTOP, DOCUMENTS, FOLDER_MAP
)
from config import (
    CLAUDE_API_KEY, WEATHER_API_KEY, CITY_NAME,
    APPS, WAKE_WORD, LISTEN_LANG, EDGE_VOICE,
    AI_SYSTEM_PROMPT,
)


# ══════════════════════════════════════════════════════════
#  YAGONA NUSXA
# ══════════════════════════════════════════════════════════
_LOCK_SOCKET = None

def ensure_single_instance():
    global _LOCK_SOCKET
    try:
        _LOCK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _LOCK_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        _LOCK_SOCKET.bind(("127.0.0.1", 47843))
        _LOCK_SOCKET.listen(1)
    except OSError:
        print("⚠️  Jarvis allaqachon ishlamoqda!")
        print("   Hal qilish: powershell -Command \"Stop-Process -Name python -Force\"")
        sys.exit(0)


# ══════════════════════════════════════════════════════════
#  GLOBAL HOLAT
# ══════════════════════════════════════════════════════════
command_history   = []
anim_window       = None
_speech_queue     = queue.Queue()
_ai_client        = None   # Bug #performance: singleton


def get_ai_client():
    """Bug #performance yechimi: Claude client bir marta yaratiladi"""
    global _ai_client
    if _ai_client is None and AN_OK and CLAUDE_API_KEY:
        _ai_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    return _ai_client


# ══════════════════════════════════════════════════════════
#  ANIMATSIYA HOLAT SINXRONIZATSIYASI
# ══════════════════════════════════════════════════════════
def _on_state_change(new_state: State):
    """StateManager callback — animatsiyani yangilash"""
    global anim_window
    if anim_window:
        try:
            anim_window.set_state(new_state.value)
        except Exception:
            pass


state_manager.on_change(_on_state_change)


# ══════════════════════════════════════════════════════════
#  TTS — Bug #1, #5, #11 yechimi
# ══════════════════════════════════════════════════════════
async def _tts_async(text: str, voice: str, path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)


def _speak_worker():
    while True:
        text = _speech_queue.get()
        if text is None:
            break
        _do_speak(text)
        _speech_queue.task_done()


def _do_speak(text: str):
    """
    Bug #1 yechimi: is_speaking.set() — wake word listener bloklanadi
    Bug #5 yechimi: gapirish paytida wake listener to'xtatiladi
    Bug #11 yechimi: TempFileManager bilan fayl boshqaruvi
    """
    print(f"\n🤖 Jarvis: {text}\n")
    logger.info(f"SPEAK: {text}")

    state_manager.set(State.SPEAKING)
    # Bug #1: is_speaking allaqachon StateManager ichida set bo'ldi

    if not (ET_OK and PG_OK):
        time.sleep(0.5)
        state_manager.set(State.IDLE)
        return

    tmp = None
    try:
        tmp = temp_manager.create()  # Bug #11: TempFileManager
        asyncio.run(_tts_async(text, EDGE_VOICE, tmp))

        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        pygame.mixer.music.unload()

    except Exception as e:
        logger.error(f"TTS xatosi: {e}")
    finally:
        # Bug #1: Ovoz tugagach + aks-sado uchun pauza
        time.sleep(0.35)
        state_manager.is_speaking.clear()
        state_manager.set(State.IDLE)

        # Bug #11: Temp faylni o'chirish
        if tmp:
            temp_manager.delete(tmp)


def speak(text: str):
    _speech_queue.put(text)


_speak_thread = threading.Thread(target=_speak_worker, daemon=True)
_speak_thread.start()


# ══════════════════════════════════════════════════════════
#  STT — Bug #3, #8, #10 yechimi
# ══════════════════════════════════════════════════════════
if SR_OK:
    recognizer = sr.Recognizer()
    recognizer.pause_threshold          = 0.8
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
else:
    recognizer = None


def listen_command(timeout=7, phrase_limit=10) -> str | None:
    """
    Bug #3 yechimi: MicGuard — mikrofon doim yopiladi
    Bug #8 yechimi: normalize_text — Kiril → Lotin
    Bug #10 yechimi: phrase_limit + so'z soni chek
    """
    if not SR_OK or not recognizer:
        return None

    # Bug #1: Jarvis gapirayotgan bo'lsa kutish
    if state_manager.is_speaking.is_set():
        logger.debug("Gapirish davom etmoqda, tinglash kechiktirildi")
        state_manager.is_speaking.wait(timeout=5)
        time.sleep(0.2)

    try:
        with MicGuard(sr) as source:  # Bug #3: MicGuard
            recognizer.adjust_for_ambient_noise(source, duration=0.1)
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit  # Bug #10: chegaralash
            )

        raw = recognizer.recognize_google(audio, language=LISTEN_LANG)

        # Bug #8: Normalizatsiya
        text = normalize_text(raw)

        # Bug #10: Juda uzun buyruq = ikki kishi gapirgan bo'lishi mumkin
        if len(text.split()) > 12:
            logger.warning(f"Juda uzun buyruq ({len(text.split())} so'z): {text[:50]}")
            speak("Bitta buyruq ayting")
            return None

        print(f"👤 Siz: {text}")
        logger.info(f"USER: {text}")
        state_manager.set(State.IDLE)
        return text

    except sr.WaitTimeoutError:
        state_manager.set(State.IDLE)
        return None
    except sr.UnknownValueError:
        state_manager.set(State.IDLE)
        return None
    except Exception as e:
        logger.warning(f"STT xatosi: {e}")
        state_manager.set(State.IDLE)
        return None


def listen_wake_word() -> bool:
    """
    Bug #1, #3 yechimi: Echo loop va mic leak oldini olish
    Bug #2 yechimi: is_wake_word() aniq tekshirish
    """
    if not SR_OK or not recognizer:
        return False

    # Bug #1: Jarvis gapirsa wake word tinglama
    if state_manager.is_speaking.is_set():
        return False

    try:
        with MicGuard(sr) as source:  # Bug #3
            recognizer.adjust_for_ambient_noise(source, duration=0.15)
            audio = recognizer.listen(source, timeout=2, phrase_time_limit=3)

        raw  = recognizer.recognize_google(audio, language=LISTEN_LANG).lower()
        text = normalize_text(raw)

        if is_wake_word(text):  # Bug #2: aniq tekshirish
            state_manager.set(State.LISTENING)
            return True
        return False

    except Exception:
        return False


# ══════════════════════════════════════════════════════════
#  AI — Bug #2, #7, #12 yechimi
# ══════════════════════════════════════════════════════════
AI_SYSTEM_PROMPT_V4 = """Siz JARVIS — Windows kompyuter yordamchisiz.

MUHIM: Har doim faqat JSON formatida javob bering:

Buyruq uchun:
{
  "type": "command",
  "action": "open_app|volume|shutdown|restart|minimize|maximize|kill_process|screenshot",
  "params": {"app": "chrome", "level": 50},
  "speak": "Bajarildi",
  "confidence": 0.95
}

Savol uchun:
{
  "type": "answer",
  "speak": "Qisqa javob (1-2 jumla, o'zbek tilida)",
  "confidence": 0.9
}

Tushunilmasa:
{
  "type": "unknown",
  "speak": "Tushunmadim, qaytadan ayting",
  "confidence": 0.1
}

QOIDALAR:
- Faqat JSON qaytaring — hech qanday matn emas
- speak: max 2 jumla, faqat o'zbek tilida
- confidence: 0.0-1.0 oralig'ida
- Xavfli buyruqlar uchun confidence 0.95+ bo'lishi kerak"""

ai_history = []


def ask_ai_safe(question: str) -> dict:
    """
    Bug #2 yechimi: timeout bilan AI chaqiruv
    Bug #7 yechimi: validate_ai_response()
    Bug #12 yechimi: RateLimiter
    """
    if not AN_OK:
        return {"type": "answer", "speak": "AI moduli o'rnatilmagan", "confidence": 0}

    if not CLAUDE_API_KEY or CLAUDE_API_KEY in ("", "YOUR_ANTHROPIC_API_KEY"):
        return {"type": "answer", "speak": "Claude API kaliti sozlanmagan", "confidence": 0}

    # Bug #12: Rate limit tekshirish
    if not rate_limiter.wait_if_needed():
        return {"type": "answer", "speak": "Biroz kuting", "confidence": 0}

    state_manager.set(State.PROCESSING)

    def _call_ai():
        client = get_ai_client()  # singleton
        ai_history.append({"role": "user", "content": question})
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=AI_SYSTEM_PROMPT_V4,
            messages=ai_history[-8:]  # oxirgi 8 ta
        )
        return resp.content[0].text

    try:
        # Bug #2: Timeout — 12 sekunddan ortiq kutmaydi
        raw = with_timeout(_call_ai, timeout_sec=12, default=None)

        if raw is None:
            state_manager.set(State.IDLE)
            return {"type": "answer", "speak": "Internet sekin, qayta urining", "confidence": 0}

        resp = parse_ai_json(raw)
        ai_history.append({"role": "assistant", "content": raw})

        # Bug #7: Xavfli buyruqni tekshirish
        if resp.get("type") == "command":
            ok, reason = validate_ai_response(resp)
            if not ok:
                logger.warning(f"AI xavfli buyruq bloklandi: {reason}")
                state_manager.set(State.IDLE)
                return {"type": "answer", "speak": f"Bu buyruqni bajara olmayman: {reason}", "confidence": 0}

        logger.info(f"AI: {question[:40]} → {resp.get('speak','')[:40]}")
        return resp

    except Exception as e:
        logger.error(f"Claude xatosi: {e}")
        state_manager.set(State.IDLE)

        err = str(e)
        if "401" in err:
            return {"type": "answer", "speak": "API kalit noto'g'ri, sozlamalarga kiring", "confidence": 0}
        if "429" in err:
            return {"type": "answer", "speak": "Juda ko'p so'rov, bir daqiqa kuting", "confidence": 0}
        if "timeout" in err.lower():
            return {"type": "answer", "speak": "Internet sekin, qayta urining", "confidence": 0}
        return {"type": "answer", "speak": "Texnik xato, qayta urining", "confidence": 0}
    finally:
        state_manager.set(State.IDLE)


# ══════════════════════════════════════════════════════════
#  OB-HAVO — Bug #9 yechimi (cache)
# ══════════════════════════════════════════════════════════
MONTHS_UZ = ["", "yanvar", "fevral", "mart", "aprel", "may", "iyun",
             "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
DAYS_UZ   = ["dushanba", "seshanba", "chorshanba", "payshanba",
             "juma", "shanba", "yakshanba"]


def get_time_str() -> str:
    n = datetime.datetime.now()
    period = ("tong" if 5 <= n.hour < 12 else
              "kunduz" if n.hour < 17 else
              "kechqurun" if n.hour < 21 else "tun")
    return f"Hozir soat {n.hour}:{n.minute:02d}. {period.capitalize()}."


def get_date_str() -> str:
    n = datetime.datetime.now()
    return (f"Bugun {DAYS_UZ[n.weekday()]}, "
            f"{n.day} {MONTHS_UZ[n.month]}, {n.year} yil.")


def get_weather(city=CITY_NAME) -> str:
    """Bug #9 yechimi: SmartCache — 10 daqiqa kesh"""
    cache_key = f"weather_{city.lower()}"
    cached = smart_cache.get(cache_key, "weather")
    if cached:
        logger.debug(f"Ob-havo keshdan: {city}")
        return cached

    if not RQ_OK or not WEATHER_API_KEY:
        return "Ob-havo API sozlanmagan"
    try:
        url  = (f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=uz")
        data = requests.get(url, timeout=5).json()
        t    = round(data["main"]["temp"])
        desc = data["weather"][0]["description"]
        wind = round(data["wind"]["speed"])
        result = (f"{city}da hozir {t} daraja, {desc}. "
                  f"Shamol {wind} metr per sekund.")
        smart_cache.set(cache_key, result)  # Bug #9: keshga saqlash
        return result
    except Exception:
        return "Ob-havo ma'lumotini olib bo'lmadi"


# ══════════════════════════════════════════════════════════
#  VOLUME
# ══════════════════════════════════════════════════════════
def _vol_interface():
    if not PCW_OK:
        return None
    try:
        devices   = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def control_volume(cmd: str) -> bool:
    """Ovoz boshqaruvi — "ovoz" so'zi majburiy"""
    if "ovoz" not in cmd:
        return False

    vol = _vol_interface()

    if any(w in cmd for w in ["o'chir", "jim", "mute"]):
        if vol:
            vol.SetMute(1, None)
        speak("Ovoz o'chirildi")
        return True

    if any(w in cmd for w in ["yoq", "unmute", "och"]):
        if vol:
            vol.SetMute(0, None)
        speak("Ovoz yoqildi")
        return True

    num = re.search(r'\b(\d{1,3})\b', cmd)
    if num:
        lvl = max(0, min(100, int(num.group(1))))
        if vol:
            vol.SetMasterVolumeLevelScalar(lvl / 100, None)
        speak(f"Ovoz {lvl} foiz")
        return True

    if any(w in cmd for w in ["oshir", "baland", "kattaroq"]):
        if vol:
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(min(1.0, cur + 0.15), None)
        speak("Ovoz oshirildi")
        return True

    if any(w in cmd for w in ["kamayt", "past", "kichikroq"]):
        if vol:
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(max(0.0, cur - 0.15), None)
        speak("Ovoz kamaytirildi")
        return True

    return False


# ══════════════════════════════════════════════════════════
#  KOMPYUTER BOSHQARUVI
# ══════════════════════════════════════════════════════════
def control_computer(cmd: str) -> bool:
    if any(w in cmd for w in ["hozir o'chir", "darhol o'chir"]):
        speak("Kompyuter o'chmoqda")
        subprocess.run("shutdown /s /t 0", shell=True)
        return True

    if any(w in cmd for w in ["kompyuterni o'chir", "shutdown"]):
        speak("Kompyuter 30 soniyada o'chadi")
        subprocess.run("shutdown /s /t 30", shell=True)
        return True

    if any(w in cmd for w in ["o'chirishni bekor", "cancel shutdown"]):
        subprocess.run("shutdown /a", shell=True)
        speak("O'chirish bekor qilindi")
        return True

    if any(w in cmd for w in ["qayta yoq", "restart", "reboot"]):
        speak("Kompyuter qayta yoqilmoqda")
        subprocess.run("shutdown /r /t 5", shell=True)
        return True

    if any(w in cmd for w in ["uxlat", "sleep"]):
        speak("Kompyuter uxlatilmoqda")
        subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return True

    if any(w in cmd for w in ["ekranni qulf", "qulfla", "lock"]):
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        speak("Ekran quflandi")
        return True

    return False


# ══════════════════════════════════════════════════════════
#  ILOVALAR
# ══════════════════════════════════════════════════════════
def open_app(cmd: str) -> bool:
    for key, path in APPS.items():
        if key in cmd:
            try:
                if path.startswith("ms-"):
                    os.startfile(path)
                elif "*" in path:
                    matches = glob.glob(path)
                    if matches:
                        subprocess.Popen(matches[0], shell=True)
                    else:
                        speak(f"{key} topilmadi")
                        return True
                else:
                    subprocess.Popen(path, shell=True)
                speak(f"{key.capitalize()} ochilmoqda")
            except Exception as e:
                logger.error(f"App xatosi {key}: {e}")
                speak(f"{key} ochib bo'lmadi")
            return True
    return False


# ══════════════════════════════════════════════════════════
#  SCREENSHOT
# ══════════════════════════════════════════════════════════
def take_screenshot():
    fname = datetime.datetime.now().strftime("jarvis_%Y-%m-%d_%H-%M-%S.png")
    path  = os.path.join(DESKTOP, fname)
    if PA_OK:
        pyautogui.screenshot().save(path)
        speak("Screenshot Desktop ga saqlandi")
    else:
        subprocess.run("snippingtool /clip", shell=True)
        speak("Screenshot clipboard ga saqlandi")


# ══════════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════════
def load_contacts() -> dict:
    cfile = os.path.join(os.path.dirname(__file__), "contacts.json")
    try:
        with open(cfile, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}


def open_telegram_contact(cmd: str) -> bool:
    contacts = load_contacts()
    for name, info in contacts.items():
        if name.lower() in cmd:
            display = info.get("display", name)
            try:
                if info.get("type") == "username":
                    os.startfile(f"tg://resolve?domain={info['username']}")
                else:
                    phone = info.get("phone", "").replace("+", "")
                    os.startfile(f"https://t.me/{phone}")
                speak(f"Telegramda {display} chati ochilmoqda")
            except Exception:
                webbrowser.open("https://web.telegram.org/")
                speak("Telegram ochilmoqda")
            return True
    speak("Bu kontakt topilmadi")
    return True


# ══════════════════════════════════════════════════════════
#  BUYRUQ QAYTA ISHLASH
# ══════════════════════════════════════════════════════════
def _record(cmd: str, resp: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    command_history.append((ts, cmd, resp))
    if len(command_history) > 200:
        command_history.pop(0)
    logger.info(f"CMD: {cmd} | RESP: {resp[:60]}")


def execute_local_intent(intent: str, cmd: str) -> bool:
    """Mahalliy buyruqni bajarish"""

    if intent == "time":
        resp = get_time_str(); speak(resp); _record(cmd, resp); return True

    if intent == "date":
        resp = get_date_str(); speak(resp); _record(cmd, resp); return True

    if intent == "screenshot":
        take_screenshot(); _record(cmd, "screenshot"); return True

    if intent == "stats":
        stats = fm_get_stats()
        resp  = format_system_stats(stats)
        speak(resp); _record(cmd, resp); return True

    if intent == "internet":
        resp = check_internet_speed(); speak(resp); _record(cmd, resp); return True

    # Ovoz — "ovoz" so'zi konteksti bilan
    if intent in ("volume_up", "volume_down", "volume_mute", "volume_set"):
        return control_volume(cmd)

    if intent == "shutdown":
        return control_computer(cmd)

    if intent == "restart":
        return control_computer(cmd)

    if intent == "sleep":
        return control_computer(cmd)

    if intent == "lock":
        return control_computer(cmd)

    if intent == "media_next":
        media_next(); speak("Keyingi qo'shiq"); _record(cmd, "media_next"); return True

    if intent == "media_prev":
        media_prev(); speak("Oldingi qo'shiq"); _record(cmd, "media_prev"); return True

    if intent in ("media_pause", "media_play"):
        media_play_pause(); speak("Bajarildi"); _record(cmd, intent); return True

    if intent == "folder_open":
        folder = parse_folder_from_cmd(cmd)
        resp   = open_folder(folder or DESKTOP)
        speak(resp); _record(cmd, resp); return True

    if intent == "file_recent":
        resp = get_recent_download(); speak(resp); _record(cmd, resp); return True

    if intent == "win_minimize":
        win_name = re.sub(r'\b(minimlashtir|kichrayt)\b', '', cmd).strip() or "Chrome"
        resp = minimize_window(win_name)
        speak(resp); _record(cmd, resp); return True

    if intent == "win_maximize":
        win_name = re.sub(r'\b(toliq ekran|kattalashtir)\b', '', cmd).strip() or "Chrome"
        resp = maximize_window(win_name)
        speak(resp); _record(cmd, resp); return True

    if intent == "win_close":
        win_name = re.sub(r'\b(oynani yop)\b', '', cmd).strip() or "Chrome"
        resp = close_window(win_name)
        speak(resp); _record(cmd, resp); return True

    if intent == "win_min_all":
        resp = minimize_all_windows(); speak(resp); _record(cmd, resp); return True

    if intent == "youtube":
        q = cmd
        for yw in ["youtube", "yutub", "utub"]:
            q = q.replace(yw, "")
        q = re.sub(r'\b(ga|da|kir|och|ni)\b', '', q).strip()
        if q:
            webbrowser.open(f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}")
            speak(f"YouTube da {q} ochilmoqda")
        else:
            webbrowser.open("https://www.youtube.com")
            speak("YouTube ochilmoqda")
        _record(cmd, "youtube"); return True

    if intent == "reminder":
        duration = parse_duration(cmd)
        if duration:
            msg = parse_reminder_message(cmd)
            set_reminder(duration, msg, speak)
            resp = f"Eslatma o'rnatildi: {format_time_left(duration)} dan keyin «{msg}»"
            speak(resp); _record(cmd, resp)
        else:
            speak("Qancha vaqtdan keyin eslatish kerak?")
        return True

    if intent == "reminder_list":
        reminders = list_reminders()
        if not reminders:
            resp = "Hech qanday eslatma yo'q"
        else:
            lines = [f"{i}. {format_time_left(s)}: {m}"
                     for i, (rid, s, m) in enumerate(reminders, 1)]
            resp = "Eslatmalar: " + ", ".join(lines)
        speak(resp); _record(cmd, resp); return True

    if intent == "task_add":
        text = re.sub(r'\b(vazifa|todo|qosh|qo\'sh|task)\b', '', cmd).strip(" ,.-")
        if text:
            add_task(text)
            resp = f"Vazifa qo'shildi: {text[:50]}"
        else:
            resp = "Qanday vazifa?"
        speak(resp); _record(cmd, resp); return True

    if intent == "task_list":
        tasks = get_tasks()
        resp  = format_tasks_text(tasks)
        speak(resp[:200]); _record(cmd, resp); return True

    if intent == "task_done":
        num = re.search(r'\b(\d+)\b', cmd)
        if num:
            tid = int(num.group(1))
            resp = (f"{tid}-vazifa bajarildi" if complete_task(tid)
                    else "Bunday vazifa topilmadi")
        else:
            resp = "Qaysi vazifa raqamini ayting"
        speak(resp); _record(cmd, resp); return True

    if intent == "journal_add":
        text = re.sub(r'\b(kundalikka|yoz|qoy|journal)\b', '', cmd).strip(" ,.-")
        if text:
            add_journal(text)
            resp = f"Kundalikka yozildi"
        else:
            resp = "Nima yozishni aytmadingiz"
        speak(resp); _record(cmd, resp); return True

    if intent == "journal_read":
        entries = get_journal()
        if not entries:
            resp = "Bugun kundalikda hech narsa yo'q"
        else:
            resp = "Bugungi kundalik: " + ". ".join(e["text"] for e in entries[:3])
        speak(resp); _record(cmd, resp); return True

    if intent == "memory_save":
        m = re.search(r'(mening\s+)?(.+?)\s+(eslab|yodlab|xotirla)', cmd)
        if m:
            raw   = m.group(2).strip().split()
            key   = raw[0] if raw else "nota"
            val   = " ".join(raw[1:]) if len(raw) > 1 else m.group(2)
            save_memory(key, val)
            resp  = f"Eslab qolindi: {key} = {val}"
        else:
            resp = "Nima eslab qolishimni aytmadingiz"
        speak(resp); _record(cmd, resp); return True

    if intent == "memory_read":
        data = get_all_memory()
        if data:
            resp = "Xotiramda: " + ", ".join(f"{k}: {v}"
                                              for k, v in list(data.items())[:5])
        else:
            resp = "Xotiramda hech narsa yo'q"
        speak(resp); _record(cmd, resp); return True

    if intent == "translate":
        resp = parse_translate_cmd(cmd); speak(resp); _record(cmd, resp); return True

    if intent == "telegram":
        return open_telegram_contact(cmd)

    if intent == "settings":
        speak("Sozlamalar oynasi ochildi"); _record(cmd, "settings"); return True

    if intent == "processes":
        from modules.file_manager import get_top_processes
        resp = get_top_processes()
        speak(resp[:200]); _record(cmd, resp); return True

    return False


def execute_ai_response(resp_dict: dict, original_cmd: str):
    """
    Bug #7 yechimi: AI buyruqini xavfsiz bajarish
    Bug #8 yechimi: confidence tekshirish
    """
    speak_text = resp_dict.get("speak", "Bajarildi")
    resp_type  = resp_dict.get("type", "answer")
    action     = resp_dict.get("action", "")
    params     = resp_dict.get("params", {})
    confidence = resp_dict.get("confidence", 1.0)

    if resp_type == "command":
        # Bug #7: Xavfli buyruq — yuqori ishonch kerak
        ok, reason = validate_ai_response(resp_dict)
        if not ok:
            speak(f"Bu buyruqni bajara olmayman")
            _record(original_cmd, f"BLOCKED: {reason}")
            return

        # Ishonch past bo'lsa tasdiqlash
        if confidence < 0.75:
            speak(f"{speak_text} qilayinmi?")
            confirm = listen_command(timeout=5)
            if not confirm or "ha" not in confirm:
                speak("Bekor qilindi")
                return

        # Buyruqni bajarish
        if action == "open_app":
            open_app(params.get("app", ""))
        elif action == "volume":
            lvl = params.get("level", 50)
            vol = _vol_interface()
            if vol:
                vol.SetMasterVolumeLevelScalar(lvl / 100, None)
        elif action == "shutdown":
            control_computer("kompyuterni o'chir")
        elif action == "restart":
            control_computer("qayta yoq")
        elif action == "screenshot":
            take_screenshot()
            return
        elif action == "kill_process":
            name = params.get("name", "")
            if name:
                kill_process(name)

    speak(speak_text)
    _record(original_cmd, speak_text)


# ══════════════════════════════════════════════════════════
#  ASOSIY PIPELINE
# ══════════════════════════════════════════════════════════
def process_command(cmd: str) -> bool:
    """
    True → davom et
    False → BACKGROUND ga o't
    """
    if not cmd:
        return True

    cmd = cmd.strip()

    # ── Bug #6: Stop so'z aniq tekshirish ────────────────
    if is_stop_command(cmd):
        speak("Xop, fonga o'tdim. Kerak bo'lsa chaqiring.")
        _record(cmd, "STOP → BACKGROUND")
        return False  # BACKGROUND ga o'tish

    # ── Ovoz — BIRINCHI (shutdown bilan konflikt oldini olish) ──
    if "ovoz" in cmd and control_volume(cmd):
        _record(cmd, "volume"); return True

    # ── Kompyuter boshqaruvi ─────────────────────────────
    if any(w in cmd for w in ["kompyuterni o'chir", "restart", "qayta yoq",
                               "uxlat", "qulfla", "hozir o'chir"]):
        if control_computer(cmd):
            _record(cmd, "system"); return True

    # ── Ob-havo (Realtime) ───────────────────────────────
    realtime = needs_realtime(cmd)
    if realtime == "weather":
        city_m = re.search(r'(\w+)da\s+(?:ob-havo|havo)', cmd)
        city   = city_m.group(1).capitalize() if city_m else CITY_NAME
        resp   = get_weather(city); speak(resp); _record(cmd, resp); return True

    if realtime == "currency":
        resp = parse_currency_cmd(cmd); speak(resp); _record(cmd, resp); return True

    if realtime == "news":
        topic = re.sub(r'\b(yangilik|xabar|news|haqida)\b', '', cmd).strip()
        resp  = get_news_rss(topic if len(topic) > 3 else None)
        speak(resp); _record(cmd, resp); return True

    if realtime == "time":
        resp = get_time_str(); speak(resp); _record(cmd, resp); return True

    # ── Mahalliy intent ──────────────────────────────────
    intent = match_local_intent(cmd)
    if intent:
        if execute_local_intent(intent, cmd):
            return True

    # ── Ilova ochish ─────────────────────────────────────
    open_words = ["och", "ochib", "ishga tushir", "yoq", "start"]
    if any(w in cmd for w in open_words):
        if open_app(cmd):
            _record(cmd, "app open"); return True

    if open_app(cmd):
        _record(cmd, "app open"); return True

    # ── Telegram kontaktlar ──────────────────────────────
    contacts = load_contacts()
    if any(name.lower() in cmd for name in contacts):
        return open_telegram_contact(cmd)

    # ── AI Fallback ──────────────────────────────────────
    speak("Bir daqiqa...")
    ai_resp = ask_ai_safe(cmd)
    execute_ai_response(ai_resp, cmd)
    return True


# ══════════════════════════════════════════════════════════
#  ASOSIY TSIKL — BACKGROUND / ACTIVE
# ══════════════════════════════════════════════════════════
def main_loop():
    speak("Salom! Jarvis tayyor. Meni chaqiring.")
    state_manager.set(State.BACKGROUND)

    _last_wake  = 0
    _COOLDOWN   = 2.5   # Bug #1: echo loop uchun cooldown

    while True:
        current = state_manager.get()

        # ── BACKGROUND: faqat wake word kutish ───────────
        if current == State.BACKGROUND:
            print("👂 'Jarvis' deng...")

            if listen_wake_word():
                now = time.time()

                # Bug #1: Cooldown — echo loop oldini olish
                if now - _last_wake < _COOLDOWN:
                    time.sleep(0.3)
                    state_manager.set(State.BACKGROUND)
                    continue

                _last_wake = now

                try:
                    import winsound
                    winsound.Beep(880, 120)
                    time.sleep(0.04)
                    winsound.Beep(1100, 80)
                except Exception:
                    pass

                state_manager.set(State.LISTENING)

                # ── ACTIVE: buyruq tinglash ───────────────
                print("🎤 Gapiring...")
                cmd = listen_command(timeout=8, phrase_limit=10)

                if cmd:
                    # False qaytsa → BACKGROUND ga qayt
                    if not process_command(cmd):
                        state_manager.set(State.BACKGROUND)
                    else:
                        # Buyruqdan keyin ham ACTIVE qoladi
                        # 3 daqiqa jim bo'lsa avtomatik BACKGROUND
                        pass
                else:
                    try:
                        import winsound
                        winsound.Beep(400, 150)
                    except Exception:
                        pass
                    state_manager.set(State.BACKGROUND)

        # ── ACTIVE: buyruq kutish (BACKGROUND ga o'tgach emas) ──
        elif current == State.LISTENING:
            # Bug #2: LISTENING da qolib ketgan bo'lsa
            state_manager.check_auto_background()

        time.sleep(0.05)


def main_keyboard():
    """Test rejimi"""
    print("\n🤖 JARVIS v4 — Klaviatura Test Rejimi")
    print("   'xayr' yoki 'yopil' → chiqish\n")
    speak("Jarvis v4 test rejimida tayyor")

    while True:
        try:
            cmd = input("👤 Buyruq: ").lower().strip()
            if not cmd:
                continue
            if is_stop_command(cmd):
                speak("Xayr! Ko'rishguncha.")
                break
            process_command(cmd)
        except KeyboardInterrupt:
            speak("Xayr!")
            break


# ══════════════════════════════════════════════════════════
#  ISHGA TUSHIRISH
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    ensure_single_instance()
    keyboard_mode = "--keyboard" in sys.argv

    if keyboard_mode:
        main_keyboard()
    else:
        try:
            main_loop()
        except KeyboardInterrupt:
            speak("Xayr!")
        finally:
            temp_manager.cleanup_all()  # Bug #11
            _speech_queue.put(None)
