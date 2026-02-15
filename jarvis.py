#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   JARVIS v4  —  O'zbek Ovozli Yordamchi                             ║
║   Modulli arxitektura  |  12 bug tuzatilgan                         ║
╚══════════════════════════════════════════════════════════════════════╝
Fayllar:
  modules/core.py            — State, Cache, RateLimiter, TempManager
  modules/nlu.py             — NLU, intent, contact matching
  modules/tts.py             — TTS (asyncio bug fix)
  modules/stt.py             — STT (MicGuard)
  modules/ai_client.py       — Claude singleton
  modules/computer_control.py— Volume, shutdown, apps, Telegram
  modules/animation.py       — HUD, sozlamalar, tarixi
  modules/history.py         — Buyruqlar tarixi
  modules/logger.py          — Loglash
  modules/memory_manager.py  — Xotira, kundalik, vazifalar
  modules/reminders.py       — Eslatmalar
  modules/media_control.py   — Media, oyna, clipboard
  modules/web_services.py    — Valyuta, tarjima, yangiliklar
  modules/file_manager.py    — Fayl, jarayonlar, statistika
  config.py                  — Sozlamalar
"""
import os, sys, re, time, threading, socket, webbrowser

# ── Yagona nusxa ─────────────────────────────────────────
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


# ── Modullar ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.core             import State, state_manager, temp_manager
from modules.nlu              import (is_stop_command, needs_realtime,
                                      match_local_intent, contact_match)
from modules.tts              import speak, stop_speaking, play_beep, shutdown_tts
from modules.stt              import listen_command, listen_wake_word
from modules.ai_client        import ask_ai
from modules.computer_control import (control_volume, control_computer,
                                      take_screenshot, open_app,
                                      load_contacts, open_telegram_contact)
from modules.animation        import (start_animation, open_settings_window,
                                      open_history_window, open_dashboard_window)
from modules import history
from modules.logger           import logger
from modules.memory_manager   import (save_memory, get_memory, get_all_memory,
                                      add_journal, get_journal,
                                      add_task, complete_task,
                                      get_tasks, format_tasks_text)
from modules.reminders        import (set_reminder, list_reminders,
                                      parse_duration, parse_reminder_message,
                                      format_time_left)
from modules.media_control    import (media_play_pause, media_next, media_prev,
                                      media_stop, minimize_window,
                                      maximize_window, close_window,
                                      minimize_all_windows, get_clipboard)
from modules.web_services     import (parse_currency_cmd, get_news_rss,
                                      parse_translate_cmd, check_internet_speed)
from modules.file_manager     import (open_folder, parse_folder_from_cmd,
                                      get_recent_download, kill_process,
                                      get_top_processes, format_system_stats,
                                      get_system_stats as fm_get_stats,
                                      DESKTOP, FOLDER_MAP)
from config                   import CITY_NAME, WAKE_WORD

import datetime

# ── Vaqt/sana ────────────────────────────────────────────
_MONTHS = ["","yanvar","fevral","mart","aprel","may","iyun",
           "iyul","avgust","sentabr","oktabr","noyabr","dekabr"]
_DAYS   = ["dushanba","seshanba","chorshanba","payshanba",
           "juma","shanba","yakshanba"]

def _time_str() -> str:
    n = datetime.datetime.now()
    p = ("tong" if 5<=n.hour<12 else "kunduz" if n.hour<17
         else "kechqurun" if n.hour<21 else "tun")
    return f"Hozir soat {n.hour}:{n.minute:02d}. {p.capitalize()}."

def _date_str() -> str:
    n = datetime.datetime.now()
    return f"Bugun {_DAYS[n.weekday()]}, {n.day} {_MONTHS[n.month]}, {n.year} yil."

# ── Ob-havo (cache) ───────────────────────────────────────
def _weather(city: str = CITY_NAME) -> str:
    from modules.core import smart_cache
    import requests
    from config import WEATHER_API_KEY

    key    = f"weather_{city.lower()}"
    cached = smart_cache.get(key, "weather")
    if cached: return cached

    if not WEATHER_API_KEY:
        return "Ob-havo API sozlanmagan"
    try:
        url  = (f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=uz")
        data = requests.get(url, timeout=5).json()
        t    = round(data["main"]["temp"])
        desc = data["weather"][0]["description"]
        wind = round(data["wind"]["speed"])
        result = f"{city}da hozir {t} daraja, {desc}. Shamol {wind} m/s."
        smart_cache.set(key, result, "weather")
        return result
    except Exception:
        return "Ob-havo ma'lumotini olib bo'lmadi"


# ══════════════════════════════════════════════════════════
#  MAHALLIY INTENT BAJARISH
# ══════════════════════════════════════════════════════════
def _exec(intent: str, cmd: str) -> bool:
    """Mahalliy intent → amal"""

    if intent == "date":
        resp = _date_str(); speak(resp); history.record(cmd, resp); return True

    if intent == "screenshot":
        take_screenshot(); history.record(cmd, "screenshot"); return True

    if intent == "stats":
        resp = format_system_stats(fm_get_stats())
        speak(resp); history.record(cmd, resp); return True

    if intent == "internet":
        resp = check_internet_speed(); speak(resp); history.record(cmd, resp); return True

    if intent == "volume":
        return control_volume(cmd)

    if intent in ("shutdown","restart","sleep","lock"):
        return control_computer(cmd)

    if intent == "media_next":
        media_next(); speak("Keyingi qo'shiq"); history.record(cmd, "next"); return True

    if intent == "media_prev":
        media_prev(); speak("Oldingi qo'shiq"); history.record(cmd, "prev"); return True

    if intent in ("media_pause","media_play"):
        media_play_pause(); speak("Bajarildi"); history.record(cmd, intent); return True

    if intent == "win_min_all":
        resp = minimize_all_windows(); speak(resp); history.record(cmd, resp); return True

    if intent == "win_minimize":
        name = re.sub(r'\b(minimlashtir|kichrayt)\b','',cmd).strip() or "Chrome"
        resp = minimize_window(name); speak(resp); history.record(cmd,resp); return True

    if intent == "win_maximize":
        name = re.sub(r"\b(to'liq ekran|kattalashtir|maximize)\b",'',cmd).strip() or "Chrome"
        resp = maximize_window(name); speak(resp); history.record(cmd,resp); return True

    if intent == "win_close":
        name = re.sub(r"\b(oynani yop|oynani o'chir)\b",'',cmd).strip() or "Chrome"
        resp = close_window(name); speak(resp); history.record(cmd,resp); return True

    if intent == "folder_open":
        folder = parse_folder_from_cmd(cmd)
        resp   = open_folder(folder or DESKTOP)
        speak(resp); history.record(cmd,resp); return True

    if intent == "file_recent":
        resp = get_recent_download(); speak(resp); history.record(cmd,resp); return True

    if intent == "reminder_list":
        rows = list_reminders()
        resp = ("Hech qanday eslatma yo'q" if not rows
                else "Eslatmalar: " + ", ".join(f"{i}. {format_time_left(s)}: {m}"
                                                 for i,(rid,s,m) in enumerate(rows,1)))
        speak(resp); history.record(cmd,resp); return True

    if intent == "reminder":
        dur = parse_duration(cmd)
        if dur:
            msg  = parse_reminder_message(cmd)
            set_reminder(dur, msg, speak)
            resp = f"Eslatma o'rnatildi: {format_time_left(dur)} dan keyin «{msg}»"
            speak(resp); history.record(cmd, resp)
        else:
            speak("Qancha vaqtdan keyin eslatish kerak?")
        return True

    if intent == "task_add":
        text = re.sub(r"\b(vazifa|todo|qo'sh|qosh|task)\b",'',cmd).strip(" ,.-")
        if text:
            add_task(text); resp = f"Vazifa qo'shildi: {text[:50]}"
        else:
            resp = "Qanday vazifa?"
        speak(resp); history.record(cmd,resp); return True

    if intent == "task_list":
        resp = format_tasks_text(get_tasks())
        speak(resp[:200]); history.record(cmd,resp); return True

    if intent == "task_done":
        num = re.search(r'\b(\d+)\b', cmd)
        if num:
            tid = int(num.group(1))
            resp = (f"{tid}-vazifa bajarildi" if complete_task(tid)
                    else "Bunday vazifa topilmadi")
        else:
            resp = "Qaysi vazifa raqamini ayting"
        speak(resp); history.record(cmd,resp); return True

    if intent == "journal_add":
        text = re.sub(r"\b(kundalikka|yoz|qo'y|journal)\b",'',cmd).strip(" ,.-")
        if text: add_journal(text); resp = "Kundalikka yozildi"
        else:    resp = "Nima yozishni aytmadingiz"
        speak(resp); history.record(cmd,resp); return True

    if intent == "journal_read":
        entries = get_journal()
        resp    = ("Bugun kundalikda hech narsa yo'q" if not entries
                   else "Bugungi kundalik: " + ". ".join(e["text"] for e in entries[:3]))
        speak(resp); history.record(cmd,resp); return True

    if intent == "memory_save":
        m = re.search(r'(mening\s+)?(.+?)\s+(eslab|yodlab|xotirla)', cmd)
        if m:
            raw = m.group(2).strip().split()
            key = raw[0]; val = " ".join(raw[1:]) if len(raw)>1 else m.group(2)
            save_memory(key, val); resp = f"Eslab qolindi: {key} = {val}"
        else:
            resp = "Nima eslab qolishimni aytmadingiz"
        speak(resp); history.record(cmd,resp); return True

    if intent == "memory_read":
        data = get_all_memory()
        resp = ("Xotiramda: " + ", ".join(f"{k}: {v}" for k,v in list(data.items())[:5])
                if data else "Xotiramda hech narsa yo'q")
        speak(resp); history.record(cmd,resp); return True

    if intent == "translate":
        resp = parse_translate_cmd(cmd); speak(resp); history.record(cmd,resp); return True

    if intent == "youtube":
        q = cmd
        for w in ["youtube","yutub","utub"]: q = q.replace(w,"")
        q = re.sub(r"\b(ga|da|kir|och|ni)\b",'',q).strip()
        if q:
            webbrowser.open(f"https://www.youtube.com/results?search_query={q.replace(' ','+')}")
            speak(f"YouTube da {q} ochilmoqda")
        else:
            webbrowser.open("https://www.youtube.com"); speak("YouTube ochilmoqda")
        history.record(cmd,"youtube"); return True

    if intent == "clipboard":
        text = get_clipboard()
        resp = f"Clipboardda: {text[:80]}" if text else "Clipboard bo'sh"
        speak(resp); history.record(cmd,resp); return True

    if intent == "processes":
        resp = get_top_processes(); speak(resp[:200]); history.record(cmd,resp); return True

    if intent == "settings":
        threading.Thread(target=open_settings_window, daemon=True).start()
        speak("Sozlamalar ochildi"); history.record(cmd,"settings"); return True

    if intent == "history":
        threading.Thread(target=open_history_window, daemon=True).start()
        speak("Buyruqlar tarixi ochildi"); history.record(cmd,"history"); return True

    if intent == "dashboard":
        threading.Thread(target=open_dashboard_window, daemon=True).start()
        speak("Dashboard ochildi"); history.record(cmd,"dashboard"); return True

    return False


# ══════════════════════════════════════════════════════════
#  AI JAVOBINI BAJARISH  — Bug #7 fix
# ══════════════════════════════════════════════════════════
def _exec_ai(resp_dict: dict, original: str):
    from modules.nlu import validate_ai_response
    speak_text = resp_dict.get("speak", "Bajarildi")
    rtype      = resp_dict.get("type", "answer")
    action     = resp_dict.get("action", "")
    params     = resp_dict.get("params", {})
    confidence = float(resp_dict.get("confidence", 1.0))

    if rtype == "command":
        ok, reason = validate_ai_response(resp_dict)
        if not ok:
            speak(f"Bu buyruqni bajara olmayman")
            history.record(original, f"BLOCKED: {reason}"); return

        # Ishonch past → tasdiqlash
        if confidence < 0.75:
            speak(f"{speak_text} qilayinmi?")
            confirm = listen_command(timeout=5)
            if not confirm or "ha" not in confirm:
                speak("Bekor qilindi"); return

        if   action == "open_app":     open_app(params.get("app",""))
        elif action == "screenshot":   take_screenshot(); return
        elif action == "shutdown":     control_computer("kompyuterni o'chir"); return
        elif action == "restart":      control_computer("qayta yoq"); return
        elif action == "kill_process":
            name = params.get("name","")
            if name: kill_process(name)
        elif action == "volume":
            from modules.computer_control import set_volume_level
            set_volume_level(params.get("level", 50))

    speak(speak_text)
    history.record(original, speak_text)


# ══════════════════════════════════════════════════════════
#  ASOSIY BUYRUQ QAYTA ISHLASH
# ══════════════════════════════════════════════════════════
def process_command(cmd: str) -> bool:
    """
    True  → davom et (ACTIVE yoki BACKGROUND)
    False → BACKGROUND ga o't (stop buyruq)
    """
    if not cmd: return True
    cmd = cmd.strip()

    # ── Stop ──────────────────────────────────────────────
    if is_stop_command(cmd):
        speak("Xop, fonga o'tdim. Kerak bo'lsa chaqiring.")
        history.record(cmd, "BACKGROUND"); return False

    # ── To'xtat (nutq) ────────────────────────────────────
    if any(w in cmd for w in ["toxta","to'xta","jim bo'l","bas","yetarli"]):
        stop_speaking(); history.record(cmd,"STOP"); return True

    # ── Ovoz — BIRINCHI (shutdown bilan konflikt yo'q) ────
    if "ovoz" in cmd and control_volume(cmd):
        return True

    # ── Kompyuter ─────────────────────────────────────────
    SYSTEM_WORDS = ["kompyuterni o'chir","hozir o'chir","restart",
                    "qayta yoq","uxlat","qulfla","o'chirishni bekor"]
    if any(w in cmd for w in SYSTEM_WORDS):
        if control_computer(cmd): return True

    # ── Real-time (internet kerak) ────────────────────────
    rt = needs_realtime(cmd)
    if rt == "weather":
        city_m = re.search(r'(\w+)da\s+(?:ob-havo|havo)', cmd)
        resp   = _weather(city_m.group(1).capitalize() if city_m else CITY_NAME)
        speak(resp); history.record(cmd, resp); return True

    if rt == "time":
        resp = _time_str(); speak(resp); history.record(cmd, resp); return True

    if rt == "currency":
        resp = parse_currency_cmd(cmd); speak(resp); history.record(cmd, resp); return True

    if rt == "news":
        topic = re.sub(r'\b(yangilik|xabar|news|haqida)\b','',cmd).strip()
        resp  = get_news_rss(topic if len(topic)>3 else None)
        speak(resp); history.record(cmd, resp); return True

    # ── Mahalliy intent ───────────────────────────────────
    intent = match_local_intent(cmd)
    if intent and _exec(intent, cmd):
        return True

    # ── Saytlar ───────────────────────────────────────────
    SITES = {
        "google":    "https://www.google.com",
        "gmail":     "https://mail.google.com",
        "instagram": "https://www.instagram.com",
        "github":    "https://www.github.com",
        "chatgpt":   "https://chat.openai.com",
        "tiktok":    "https://www.tiktok.com",
    }
    for site, url in SITES.items():
        if site in cmd:
            # Google qidiruv
            if site == "google":
                m = re.search(r'google(?:\s+da)?\s+(.+?)\s*(?:qidir|search)?$', cmd)
                if m:
                    webbrowser.open(f"https://www.google.com/search?q={m.group(1).replace(' ','+')}")
                    speak(f"{m.group(1)} qidirilmoqda"); history.record(cmd,"google"); return True
            webbrowser.open(url)
            speak(f"{site.capitalize()} ochilmoqda")
            history.record(cmd, site); return True

    # ── Ilova ochish ──────────────────────────────────────
    if open_app(cmd):
        history.record(cmd, "app open"); return True

    # ── Telegram kontakt ─────────────────────────────────
    contacts = load_contacts()
    if "telegram" in cmd or any(contact_match(n, cmd) for n in contacts):
        if any(contact_match(n, cmd) for n in contacts):
            return open_telegram_contact(cmd)
        open_app("telegram"); return True

    # ── AI fallback ───────────────────────────────────────
    speak("Bir daqiqa...")
    state_manager.set(State.PROCESSING)
    ai_resp = ask_ai(cmd)
    _exec_ai(ai_resp, cmd)
    return True


# ══════════════════════════════════════════════════════════
#  ASOSIY TSIKL
# ══════════════════════════════════════════════════════════
def main_loop():
    speak("Salom! Jarvis tayyor. Meni chaqiring.")
    state_manager.set(State.BACKGROUND)

    _last_wake  = 0.0
    _COOLDOWN   = 2.5      # Bug #1: echo loop uchun

    while True:
        current = state_manager.get()

        # ── BACKGROUND: faqat wake word ───────────────────
        if current == State.BACKGROUND:
            print("👂 'Jarvis' deng...")

            if not listen_wake_word():
                time.sleep(0.05); continue

            now = time.time()
            if now - _last_wake < _COOLDOWN:
                time.sleep(0.3)
                state_manager.set(State.BACKGROUND); continue
            _last_wake = now

            play_beep(880, 120); time.sleep(0.04); play_beep(1100, 80)
            state_manager.set(State.LISTENING)

        # ── LISTENING / ACTIVE: buyruq tinglash ──────────
        # Har ikki holat ham tinglaydi — bitta buyruqdan keyin
        # avtomatik qayta tinglashga kiradi (conversational mode)
        if state_manager.get() in (State.LISTENING, State.IDLE):
            print("🎤 Gapiring...")
            cmd = listen_command(timeout=6, phrase_limit=10)

            if cmd:
                if not process_command(cmd):
                    # is_stop_command → BACKGROUND
                    state_manager.set(State.BACKGROUND)
                else:
                    # Buyruqdan keyin 3s kutib yangi buyruq tinglash
                    # Javob tugashini kutish
                    _speech_wait_start = time.time()
                    while state_manager.is_speaking.is_set():
                        if time.time() - _speech_wait_start > 15:
                            break
                        time.sleep(0.1)
                    state_manager.set(State.LISTENING)
            else:
                # Buyruq kelinmadi → BACKGROUND
                play_beep(400, 150)
                state_manager.set(State.BACKGROUND)

        time.sleep(0.05)


def main_keyboard():
    """Test rejimi — mikrofonsiz"""
    print("\n🤖 JARVIS v4 — Klaviatura Test Rejimi")
    print("   'xayr' yoki 'yopil' → chiqish\n")
    speak("Jarvis v4 test rejimida tayyor")

    while True:
        try:
            cmd = input("👤 Buyruq: ").lower().strip()
            if not cmd: continue
            if is_stop_command(cmd):
                speak("Xayr! Ko'rishguncha."); break
            process_command(cmd)
        except KeyboardInterrupt:
            speak("Xayr!"); break


# ══════════════════════════════════════════════════════════
#  ISHGA TUSHIRISH
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    ensure_single_instance()
    keyboard_mode = "--keyboard" in sys.argv

    if keyboard_mode:
        main_keyboard()
    else:
        # Animatsiyani alohida threadda ishga tushirish
        anim_thread = threading.Thread(target=start_animation, daemon=True)
        anim_thread.start()
        time.sleep(0.8)  # Animatsiya tayyor bo'lguncha kutish

        try:
            main_loop()
        except KeyboardInterrupt:
            speak("Xayr!")
        finally:
            temp_manager.cleanup_all()
            shutdown_tts()