#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║     JARVIS v3  —  O'zbek Ovozli Yordamchi                           ║
║     Windows Voice Assistant  —  Full Edition                         ║
╚══════════════════════════════════════════════════════════════════════╝
Yangiliklar v3:
  ✅ Xotira tizimi (memory.json)
  ✅ Kundalik va Vazifalar (To-Do)
  ✅ Eslatmalar (threading.Timer + Toast)
  ✅ Spotify integratsiya
  ✅ Media tugmalar (play/pause/next/prev)
  ✅ Oyna boshqaruvi (minimize/maximize/close)
  ✅ Clipboard boshqaruvi
  ✅ Fayl boshqaruvi
  ✅ Jarayonlar (psutil)
  ✅ Valyuta kurslari
  ✅ Yangiliklar (RSS)
  ✅ Tarjima (deep-translator)
  ✅ Dashboard: CPU/RAM/Batareya (HUD da)
  ✅ Loglash (logs/ papkasiga)
  ✅ Buyruqlar tarixi
  ✅ Sozlamalar oynasi (tkinter)
  ✅ .env xavfsizlik
"""

import os, sys, json, time, asyncio, subprocess, webbrowser
import datetime, tempfile, re, glob, threading, socket
import math
import queue
import tkinter as tk
from tkinter import Canvas, ttk, messagebox, simpledialog

# ── .env fayldan API kalitlarni yuklash ───────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    DOTENV_OK = True
except ImportError:
    DOTENV_OK = False


# ══════════════════════════════════════════════════════════════════════
#  YAGONA NUSXA
# ══════════════════════════════════════════════════════════════════════
_LOCK_SOCKET = None

def ensure_single_instance():
    global _LOCK_SOCKET
    try:
        _LOCK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _LOCK_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        _LOCK_SOCKET.bind(("127.0.0.1", 47843))
        _LOCK_SOCKET.listen(1)
        return True
    except OSError:
        print("⚠️  Jarvis allaqachon ishlamoqda!")
        sys.exit(0)


# ══════════════════════════════════════════════════════════════════════
#  KUTUBXONALAR
# ══════════════════════════════════════════════════════════════════════
def check_import(module, pip_name=None):
    try:
        return __import__(module), True
    except ImportError:
        n = pip_name or module
        print(f"⚠️  {n} topilmadi → pip install {n}")
        return None, False

_, SR_OK  = check_import("speech_recognition", "SpeechRecognition")
_, PG_OK  = check_import("pygame")
_, ET_OK  = check_import("edge_tts", "edge-tts")
_, RQ_OK  = check_import("requests")
_, AN_OK  = check_import("anthropic")
_, PA_OK  = check_import("pyautogui")

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    PCW_OK = True
except Exception:
    PCW_OK = False

if SR_OK: import speech_recognition as sr
else:     sr = None

if PG_OK:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

if ET_OK:  import edge_tts
if RQ_OK:  import requests
if AN_OK:  import anthropic
if PA_OK:
    import pyautogui
    pyautogui.FAILSAFE = False

# ── Yangi modullar ────────────────────────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(__file__))

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
    init_spotify, spotify_search_play, spotify_pause, spotify_resume,
    spotify_next, spotify_prev, spotify_current, spotify_volume,
    media_play_pause, media_next, media_prev, media_stop,
    minimize_window, maximize_window, close_window, restore_window,
    list_open_windows, minimize_all_windows,
    get_clipboard, set_clipboard,
    kill_process_by_name, get_top_processes, get_system_stats
)
from modules.web_services import (
    get_currency_rate, parse_currency_cmd,
    get_news_rss,
    translate_text, parse_translate_cmd,
    check_internet_speed
)
from modules.file_manager import (
    open_folder, parse_folder_from_cmd,
    list_files, get_recent_download, open_file,
    kill_process, format_system_stats,
    get_system_stats as fm_get_stats,
    DOWNLOADS, DESKTOP, DOCUMENTS, PICTURES, FOLDER_MAP
)

from config import (
    CLAUDE_API_KEY, WEATHER_API_KEY, CITY_NAME,
    APPS, WAKE_WORD, LISTEN_LANG, EDGE_VOICE,
    AI_SYSTEM_PROMPT,
    SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
)


# ══════════════════════════════════════════════════════════════════════
#  GLOBAL HOLAT
# ══════════════════════════════════════════════════════════════════════
jarvis_state     = "idle"
anim_window      = None
command_history  = []          # [(vaqt, buyruq, javob), ...]
_speech_queue    = queue.Queue()   # Thread-safe ovoz navbati


# ══════════════════════════════════════════════════════════════════════
#  YORDAMCHILAR
# ══════════════════════════════════════════════════════════════════════
def play_beep(freq=880, duration_ms=200):
    try:
        import winsound
        winsound.Beep(freq, duration_ms)
    except Exception:
        pass


def set_state(state: str):
    global jarvis_state, anim_window
    jarvis_state = state
    if anim_window:
        try:
            anim_window.set_state(state)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  TTS  —  Thread-xavfsiz speak
# ══════════════════════════════════════════════════════════════════════
async def _tts_async(text: str, voice: str, tmp_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(tmp_path)


def _speak_worker():
    """Alohida threadda ovozli javoblarni navbat bilan chiqaradi"""
    while True:
        text = _speech_queue.get()
        if text is None:
            break
        _do_speak(text)
        _speech_queue.task_done()


def _do_speak(text: str):
    print(f"\n🤖 Jarvis: {text}\n")
    logger.info(f"SPEAK: {text}")
    set_state("speaking")
    if not (ET_OK and PG_OK):
        set_state("idle")
        return
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tmp = fp.name
        asyncio.run(_tts_async(text, EDGE_VOICE, tmp))
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        try:
            os.unlink(tmp)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"TTS xatosi: {e}")
    finally:
        set_state("idle")


def speak(text: str):
    """Asosiy speak funksiyasi — navbatga qo'shadi"""
    _speech_queue.put(text)


# Speak worker ni threadda ishga tushirish
_speak_thread = threading.Thread(target=_speak_worker, daemon=True)
_speak_thread.start()


# ══════════════════════════════════════════════════════════════════════
#  STT  —  Ovozni matnga
# ══════════════════════════════════════════════════════════════════════
if SR_OK and sr:
    recognizer = sr.Recognizer()
    recognizer.pause_threshold           = 0.8
    recognizer.energy_threshold          = 300
    recognizer.dynamic_energy_threshold  = True
else:
    recognizer = None


def listen(timeout=7, phrase_limit=12):
    if not SR_OK or not recognizer:
        return None
    try:
        with sr.Microphone() as src:
            recognizer.adjust_for_ambient_noise(src, duration=0.1)
            audio = recognizer.listen(src, timeout=timeout,
                                       phrase_time_limit=phrase_limit)
        text = recognizer.recognize_google(audio, language=LISTEN_LANG)
        print(f"👤 Siz: {text}")
        logger.info(f"USER: {text}")
        set_state("idle")
        return text.lower().strip()
    except sr.WaitTimeoutError:
        set_state("idle"); return None
    except sr.UnknownValueError:
        set_state("idle"); return None
    except Exception as e:
        logger.warning(f"STT xatosi: {e}")
        set_state("idle"); return None


def listen_wake_word():
    if not SR_OK or not recognizer:
        return False
    try:
        with sr.Microphone() as src:
            recognizer.adjust_for_ambient_noise(src, duration=0.2)
            audio = recognizer.listen(src, timeout=3, phrase_time_limit=3)
        text = recognizer.recognize_google(audio, language=LISTEN_LANG).lower()
        if WAKE_WORD in text:
            set_state("listening")
            return True
        return False
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════
#  ANIMATSIYA  —  Cyberpunk HUD (CPU/RAM ko'rsatgich bilan)
# ══════════════════════════════════════════════════════════════════════
class JarvisAnimation:
    W, H   = 240, 310
    BG     = "#050810"
    PANEL  = "#0a1628"
    BORDER = "#0d2444"

    STATE_CFG = {
        "idle":      {"color": "#00aaff", "label": "STANDBY",      "dim": 0.35},
        "listening": {"color": "#00ffee", "label": "TINGLAYAPMAN", "dim": 1.0},
        "thinking":  {"color": "#ffaa00", "label": "O'YLAMOQDA",   "dim": 1.0},
        "speaking":  {"color": "#00ff88", "label": "GAPIRMOQDA",   "dim": 1.0},
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JARVIS")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.96)
        self.root.configure(bg=self.BG)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{sw-self.W-18}+{sh-self.H-55}")

        self.cv = Canvas(self.root, width=self.W, height=self.H,
                         bg=self.BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self._drag_x = self._drag_y = 0
        self.cv.bind("<ButtonPress-1>", self._drag_start)
        self.cv.bind("<B1-Motion>",     self._drag_move)
        # Sağ klik — kontekst menyu
        self.cv.bind("<Button-3>",      self._show_menu)

        self._cur_color  = self.STATE_CFG["idle"]["color"]
        self._particles  = []
        self._frame      = 0
        self._running    = True
        self._stats      = {}          # CPU/RAM ma'lumotlari
        self._stats_tick = 0           # Har 30 frame yangilash

        self._menu = tk.Menu(self.root, tearoff=0,
                             bg="#0a1628", fg="#00aaff",
                             activebackground="#00aaff",
                             activeforeground="#000")
        self._menu.add_command(label="⚙️  Sozlamalar",
                               command=lambda: open_settings_window(self.root))
        self._menu.add_command(label="📋 Buyruqlar tarixi",
                               command=lambda: open_history_window(self.root))
        self._menu.add_separator()
        self._menu.add_command(label="❌ Jarvis ni yopish",
                               command=self._quit)

        self._spawn_particles()
        self._animate()

    def _quit(self):
        self._running = False
        self.root.destroy()
        os._exit(0)

    def _drag_start(self, e):
        self._drag_x = e.x; self._drag_y = e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _show_menu(self, e):
        try: self._menu.tk_popup(e.x_root, e.y_root)
        finally: self._menu.grab_release()

    def _spawn_particles(self):
        import random
        cx, cy = self.W//2, 110
        self._particles = [{
            "angle": random.uniform(0, 2*math.pi),
            "speed": random.uniform(0.3, 1.1),
            "dist":  random.uniform(28, 72),
            "size":  random.uniform(1.5, 3.5),
            "phase": random.uniform(0, 2*math.pi),
            "cx": cx, "cy": cy,
        } for _ in range(18)]

    def _lerp_color(self, c1, c2, t):
        t = max(0.0, min(1.0, t))
        def ch(c): return int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)
        r1,g1,b1 = ch(c1); r2,g2,b2 = ch(c2)
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

    def _dim(self, color, factor):
        r = min(255, int(int(color[1:3],16)*factor))
        g = min(255, int(int(color[3:5],16)*factor))
        b = min(255, int(int(color[5:7],16)*factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _animate(self):
        if not self._running:
            return
        cv  = self.cv
        W, H = self.W, self.H
        cv.delete("all")

        state = jarvis_state
        cfg   = self.STATE_CFG.get(state, self.STATE_CFG["idle"])
        color, dim_f, label = cfg["color"], cfg["dim"], cfg["label"]
        t = self._frame / 30.0

        self._cur_color = self._lerp_color(self._cur_color, color, 0.08)
        c = self._cur_color
        pad = 8

        # Fon
        cv.create_rectangle(pad, pad, W-pad, H-pad,
                             fill=self.PANEL, outline=self.BORDER, width=1)

        # Sarlavha
        cv.create_rectangle(pad, pad, W-pad, pad+28,
                             fill="#07111f", outline="", width=0)
        cv.create_text(W//2, pad+14, text="J · A · R · V · I · S",
                       font=("Courier", 9, "bold"), fill=self._dim(c, 0.7))
        cv.create_rectangle(pad+6, pad+8, pad+12, pad+20,
                             fill=self._dim(c, 0.4), outline="")
        cv.create_rectangle(W-pad-12, pad+8, W-pad-6, pad+20,
                             fill=self._dim(c, 0.4), outline="")
        cv.create_line(pad+4, pad+29, W-pad-4, pad+29,
                       fill=self._dim(c, 0.25), width=1)

        # Orb markazi
        cx, cy_orb = W//2, 110

        # Glow
        for gs, ga in zip([52, 42, 34], [0.06, 0.10, 0.16]):
            gc = self._dim(c, ga * (1.5 if state != "idle" else 0.5))
            cv.create_oval(cx-gs, cy_orb-gs, cx+gs, cy_orb+gs,
                           fill=gc, outline="")

        if state == "idle":
            breath = 0.5 + 0.5*math.sin(t*1.2)
            r_b = 22 + 4*breath
            cv.create_oval(cx-r_b, cy_orb-r_b, cx+r_b, cy_orb+r_b,
                           fill=self._dim(c, 0.15),
                           outline=self._dim(c, 0.4), width=1)
            rd = 7 + 2*breath
            cv.create_oval(cx-rd, cy_orb-rd, cx+rd, cy_orb+rd,
                           fill=self._dim(c, 0.5), outline="")
            lc = self._dim(c, 0.35)
            cv.create_line(cx-14, cy_orb, cx+14, cy_orb, fill=lc, width=1)
            cv.create_line(cx, cy_orb-14, cx, cy_orb+14, fill=lc, width=1)

        elif state == "listening":
            for i in range(4):
                phase = (t*1.6 - i*0.45) % 1.0
                r_s = 16 + phase*46
                cv.create_oval(cx-r_s, cy_orb-r_s, cx+r_s, cy_orb+r_s,
                               fill="",
                               outline=self._dim(c, (1.0-phase)*0.8),
                               width=max(1, int(2*(1-phase))))
            mw, mh = 10, 15
            cv.create_rectangle(cx-mw//2, cy_orb-mh//2,
                                 cx+mw//2, cy_orb+mh//2,
                                 fill=c, outline=self._dim(c,0.5), width=1)
            cv.create_arc(cx-mw//2-3, cy_orb-mh//2,
                          cx+mw//2+3, cy_orb+mh//2+6,
                          start=0, extent=-180,
                          outline=c, fill="", style="arc", width=2)
            cv.create_line(cx, cy_orb+mh//2+5, cx, cy_orb+mh//2+10,
                           fill=c, width=2)
            cv.create_line(cx-6, cy_orb+mh//2+10, cx+6, cy_orb+mh//2+10,
                           fill=c, width=2)

        elif state == "thinking":
            for ring_i, (orb_r, spd, ph) in enumerate(
                    [(36, 2.0, 0), (26, -3.2, 0.5)]):
                ang = t*spd + ph
                rx, ry = orb_r, orb_r*0.38
                cv.create_oval(cx-rx, cy_orb-ry, cx+rx, cy_orb+ry,
                               outline=self._dim(c, 0.18), fill="", width=1)
                dx = cx + rx*math.cos(ang)
                dy = cy_orb + ry*math.sin(ang)
                dr = 5 if ring_i==0 else 4
                cv.create_oval(dx-dr, dy-dr, dx+dr, dy+dr,
                               fill=c, outline="")
                for tr in range(6):
                    ta  = ang - tr*0.18
                    tdx = cx + rx*math.cos(ta)
                    tdy = cy_orb + ry*math.sin(ta)
                    tdr = dr*(1-tr/7)
                    cv.create_oval(tdx-tdr, tdy-tdr, tdx+tdr, tdy+tdr,
                                   fill=self._dim(c, 0.5*(1-tr/6)), outline="")
            r_star = 10 + 2*math.sin(t*5)
            cv.create_oval(cx-r_star, cy_orb-r_star, cx+r_star, cy_orb+r_star,
                           fill=self._dim(c, 0.9), outline="")

        elif state == "speaking":
            n_bars = 11; bar_w = 8; gap = 4
            total_w = n_bars*(bar_w+gap) - gap
            sx = cx - total_w//2
            max_h = 44; min_h = 5
            for i in range(n_bars):
                ph_i = t*4.5 + i*0.55
                h = min_h + (max_h-min_h)*abs(math.sin(ph_i))
                bx = sx + i*(bar_w+gap)
                cv.create_rectangle(bx-2, cy_orb+int(h+4)//2,
                                     bx+bar_w+2, cy_orb-int(h+4)//2,
                                     fill=self._dim(c, 0.2), outline="")
                cv.create_rectangle(bx, cy_orb+h//2,
                                     bx+bar_w, cy_orb-h//2,
                                     fill=c, outline="")
                cv.create_rectangle(bx, cy_orb-int(h)//2,
                                     bx+bar_w, cy_orb-int(h)//2+2,
                                     fill="white", outline="")

        # Particlelar
        if state != "idle":
            for p in self._particles:
                p["angle"] += p["speed"]*0.02
                pulse = 0.7 + 0.3*math.sin(t*2 + p["phase"])
                px = p["cx"] + p["dist"]*math.cos(p["angle"])*pulse
                py = p["cy"] + p["dist"]*math.sin(p["angle"])*pulse*0.6
                ps = p["size"]*pulse*dim_f
                cv.create_oval(px-ps, py-ps, px+ps, py+ps,
                               fill=self._dim(c, 0.55*dim_f), outline="")

        # ── CPU / RAM / Batareya paneli ──────────────────────────────
        self._stats_tick += 1
        if self._stats_tick >= 60:   # Har 2 soniyada yangilash
            self._stats_tick = 0
            try:
                self._stats = fm_get_stats()
            except Exception:
                pass

        stats_y = cy_orb + 70
        cv.create_line(pad+4, stats_y-4, W-pad-4, stats_y-4,
                       fill=self._dim(c, 0.20), width=1)

        if self._stats:
            bar_h = 5
            bar_bg = "#0d2444"

            def draw_bar(label_txt, value, y_pos, bar_color):
                cv.create_text(pad+12, y_pos, text=label_txt,
                               font=("Courier", 7), fill=self._dim(c, 0.6),
                               anchor="w")
                bx1, bx2 = pad+42, W-pad-12
                bw = bx2 - bx1
                cv.create_rectangle(bx1, y_pos-3, bx2, y_pos+3,
                                     fill=bar_bg, outline="")
                filled = int(bw * min(100, value) / 100)
                if filled > 0:
                    cv.create_rectangle(bx1, y_pos-3, bx1+filled, y_pos+3,
                                         fill=bar_color, outline="")
                cv.create_text(bx2+4, y_pos, text=f"{value}%",
                               font=("Courier", 6), fill=self._dim(c, 0.55),
                               anchor="w")

            cpu_color = "#ff4444" if self._stats.get("cpu",0)>80 else c
            draw_bar("CPU", self._stats.get("cpu", 0),   stats_y+8,  cpu_color)
            ram_color = "#ff8800" if self._stats.get("ram",0)>85 else c
            draw_bar("RAM", self._stats.get("ram", 0),   stats_y+20, ram_color)

            bat = self._stats.get("battery")
            if bat is not None:
                plug = self._stats.get("plugged", False)
                bat_color = (c if plug or bat > 20 else "#ff2222")
                bat_icon  = "⚡" if plug else "🔋"
                cv.create_text(pad+12, stats_y+32,
                               text=f"{bat_icon} BAT  {bat}%",
                               font=("Courier", 7),
                               fill=bat_color, anchor="w")
            stats_y += 44

        # Quyi holat satri
        y_bottom = H - pad - 28
        cv.create_line(pad+4, y_bottom, W-pad-4, y_bottom,
                       fill=self._dim(c, 0.20), width=1)
        blink = abs(math.sin(t*3.0))
        cv.create_oval(pad+10, y_bottom+7, pad+16, y_bottom+13,
                       fill=self._dim(c, blink*dim_f), outline="")
        cv.create_text(W//2+4, y_bottom+10, text=label,
                       font=("Courier", 8, "bold"),
                       fill=self._dim(c, 0.85*dim_f))

        # Chegara glow
        glow_a = 0.18 + 0.08*math.sin(t*2)
        cv.create_rectangle(pad, pad, W-pad, H-pad,
                             fill="", outline=self._dim(c, glow_a), width=2)
        cv.create_rectangle(pad+1, pad+1, W-pad-1, H-pad-1,
                             fill="", outline=self._dim(c, glow_a*0.5), width=1)

        self._frame += 1
        self.root.after(33, self._animate)

    def set_state(self, state):
        global jarvis_state
        jarvis_state = state

    def stop(self):
        self._running = False
        try: self.root.destroy()
        except Exception: pass

    def run(self):
        self.root.mainloop()


def start_animation():
    global anim_window
    anim_window = JarvisAnimation()
    anim_window.run()


# ══════════════════════════════════════════════════════════════════════
#  SOZLAMALAR OYNASI
# ══════════════════════════════════════════════════════════════════════
def open_settings_window(parent=None):
    win = tk.Toplevel(parent) if parent else tk.Tk()
    win.title("JARVIS — Sozlamalar")
    win.geometry("500x520")
    win.configure(bg="#0a1628")
    win.resizable(False, False)

    style = ttk.Style(win)
    style.theme_use("clam")
    style.configure("TNotebook",       background="#0a1628", borderwidth=0)
    style.configure("TNotebook.Tab",   background="#0d2444", foreground="#00aaff",
                                       padding=[10, 4])
    style.configure("TFrame",          background="#0a1628")
    style.configure("TLabel",          background="#0a1628", foreground="#aabbcc",
                                       font=("Courier", 9))
    style.configure("TEntry",          fieldbackground="#07111f", foreground="#ffffff",
                                       insertcolor="#00aaff")
    style.configure("TButton",         background="#0d2444", foreground="#00aaff",
                                       font=("Courier", 9))

    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    # ── API Kalitlar tab ──────────────────────────────────────────────
    tab_api = ttk.Frame(nb)
    nb.add(tab_api, text="🔑 API Kalitlar")

    fields_api = [
        ("Claude API Key:",      "CLAUDE_API_KEY"),
        ("Weather API Key:",     "WEATHER_API_KEY"),
        ("Spotify Client ID:",   "SPOTIFY_CLIENT_ID"),
        ("Spotify Client Sec:",  "SPOTIFY_CLIENT_SECRET"),
    ]
    entries_api = {}
    for i, (label, key) in enumerate(fields_api):
        ttk.Label(tab_api, text=label).grid(row=i, column=0, sticky="w",
                                             padx=12, pady=8)
        e = ttk.Entry(tab_api, width=35, show="*")
        e.grid(row=i, column=1, padx=8, pady=8)
        cur_val = os.environ.get(key, "")
        e.insert(0, cur_val)
        entries_api[key] = e

    def save_api():
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        lines = []
        for key, entry in entries_api.items():
            val = entry.get().strip()
            if val:
                lines.append(f"{key}={val}")
        with open(env_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        messagebox.showinfo("Saqlandi",
                            ".env faylga saqlandi.\nJarvisni qayta ishga tushiring.",
                            parent=win)

    ttk.Button(tab_api, text="💾 Saqlash", command=save_api).grid(
        row=len(fields_api), column=1, sticky="e", padx=8, pady=12)

    # ── Xotira tab ───────────────────────────────────────────────────
    tab_mem = ttk.Frame(nb)
    nb.add(tab_mem, text="🧠 Xotira")

    mem_frame = tk.Frame(tab_mem, bg="#0a1628")
    mem_frame.pack(fill="both", expand=True, padx=12, pady=8)

    mem_text = tk.Text(mem_frame, bg="#07111f", fg="#aabbcc",
                       font=("Courier", 9), width=55, height=12)
    mem_text.pack(fill="both", expand=True)

    def load_memory_view():
        mem_text.config(state="normal")
        mem_text.delete("1.0", "end")
        data = get_all_memory()
        if data:
            for k, v in data.items():
                mem_text.insert("end", f"{k}: {v}\n")
        else:
            mem_text.insert("end", "Xotira bo'sh\n")
        mem_text.config(state="disabled")

    load_memory_view()
    ttk.Button(tab_mem, text="🔄 Yangilash",
               command=load_memory_view).pack(pady=4)

    # ── Vazifalar tab ────────────────────────────────────────────────
    tab_tasks = ttk.Frame(nb)
    nb.add(tab_tasks, text="📌 Vazifalar")

    task_text = tk.Text(tab_tasks, bg="#07111f", fg="#aabbcc",
                        font=("Courier", 9), width=55, height=10)
    task_text.pack(fill="both", expand=True, padx=12, pady=8)

    def load_tasks_view():
        task_text.config(state="normal")
        task_text.delete("1.0", "end")
        tasks = get_tasks(only_pending=False)
        task_text.insert("end", format_tasks_text(tasks))
        task_text.config(state="disabled")

    load_tasks_view()

    task_entry_frame = tk.Frame(tab_tasks, bg="#0a1628")
    task_entry_frame.pack(fill="x", padx=12, pady=4)
    task_input = ttk.Entry(task_entry_frame, width=40)
    task_input.pack(side="left", padx=4)

    def add_task_gui():
        txt = task_input.get().strip()
        if txt:
            add_task(txt)
            task_input.delete(0, "end")
            load_tasks_view()
    ttk.Button(task_entry_frame, text="➕ Qo'sh",
               command=add_task_gui).pack(side="left", padx=4)

    win.mainloop() if not parent else None


# ══════════════════════════════════════════════════════════════════════
#  BUYRUQLAR TARIXI OYNASI
# ══════════════════════════════════════════════════════════════════════
def open_history_window(parent=None):
    win = tk.Toplevel(parent) if parent else tk.Tk()
    win.title("JARVIS — Buyruqlar tarixi")
    win.geometry("600x400")
    win.configure(bg="#0a1628")

    text = tk.Text(win, bg="#07111f", fg="#aabbcc",
                   font=("Courier", 9), wrap="word")
    text.pack(fill="both", expand=True, padx=10, pady=10)

    scroll = tk.Scrollbar(win, command=text.yview)
    scroll.pack(side="right", fill="y")
    text.config(yscrollcommand=scroll.set)

    if command_history:
        for ts, cmd, resp in command_history[-50:]:
            text.insert("end", f"[{ts}] 👤 {cmd}\n")
            text.insert("end", f"       🤖 {resp[:80]}\n\n")
    else:
        text.insert("end", "Hali buyruqlar tarixi yo'q\n")
    text.config(state="disabled")

    if not parent:
        win.mainloop()


# ══════════════════════════════════════════════════════════════════════
#  KOMPYUTER BOSHQARUVI
# ══════════════════════════════════════════════════════════════════════
def control_computer(cmd: str) -> bool:
    if any(w in cmd for w in ["hozir o'chir", "darhol o'chir", "tez o'chir"]):
        speak("Kompyuter o'chmoqda")
        subprocess.run("shutdown /s /t 0", shell=True); return True

    if any(w in cmd for w in [
        "kompyuterni o'chir", "o'chir", "shutdown",
        "kompyuter o'chir", "yopib qo'y kompyuterni"
    ]):
        speak("Kompyuter 30 soniyada o'chadi")
        subprocess.run("shutdown /s /t 30", shell=True); return True

    if any(w in cmd for w in ["o'chirishni bekor", "cancel shutdown"]):
        subprocess.run("shutdown /a", shell=True)
        speak("O'chirish bekor qilindi"); return True

    if any(w in cmd for w in [
        "qayta yoq", "restart", "qayta ishga tushir", "reboot"
    ]):
        speak("Kompyuter qayta yoqilmoqda")
        subprocess.run("shutdown /r /t 5", shell=True); return True

    if any(w in cmd for w in ["uxlat", "sleep", "uxlatib qo'y", "hibernat"]):
        speak("Kompyuter uxlatilmoqda")
        subprocess.run(
            "rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return True

    if any(w in cmd for w in ["ekranni qulf", "qulfla", "lock", "blokirovka"]):
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        speak("Ekran quflandi"); return True

    return False


# ══════════════════════════════════════════════════════════════════════
#  ILOVALAR
# ══════════════════════════════════════════════════════════════════════
def open_app(cmd: str) -> bool:
    for key, path in APPS.items():
        if key in cmd:
            try:
                if path.startswith("ms-"):
                    os.startfile(path)
                else:
                    # Glob bilan wildcard hal qilish
                    if "*" in path:
                        matches = glob.glob(path)
                        if matches:
                            subprocess.Popen(matches[0], shell=True)
                        else:
                            speak(f"{key} topilmadi"); return True
                    else:
                        subprocess.Popen(path, shell=True)
                speak(f"{key.capitalize()} ochilmoqda")
            except Exception as e:
                logger.error(f"App ochib bo'lmadi {key}: {e}")
                speak(f"{key} ochib bo'lmadi")
            return True
    return False


# ══════════════════════════════════════════════════════════════════════
#  VOLUME  (pycaw)
# ══════════════════════════════════════════════════════════════════════
def _vol_interface():
    if not PCW_OK: return None
    try:
        devices   = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception: return None

def control_volume(cmd: str) -> bool:
    vol = _vol_interface()

    if any(w in cmd for w in ["o'chir", "jim", "mute"]) and "ovoz" in cmd:
        if vol: vol.SetMute(1, None)
        speak("Ovoz o'chirildi"); return True

    if any(w in cmd for w in ["yoq", "unmute"]) and "ovoz" in cmd:
        if vol: vol.SetMute(0, None)
        speak("Ovoz yoqildi"); return True

    num = re.search(r'\b(\d{1,3})\b', cmd)
    if num and "ovoz" in cmd:
        lvl = max(0, min(100, int(num.group(1))))
        if vol: vol.SetMasterVolumeLevelScalar(lvl/100, None)
        speak(f"Ovoz {lvl} foiz"); return True

    if any(w in cmd for w in ["oshir", "baland", "kattaroq"]) and "ovoz" in cmd:
        if vol:
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(min(1.0, cur+0.15), None)
        speak("Ovoz oshirildi"); return True

    if any(w in cmd for w in ["kamayt", "past", "kichikroq"]) and "ovoz" in cmd:
        if vol:
            cur = vol.GetMasterVolumeLevelScalar()
            vol.SetMasterVolumeLevelScalar(max(0.0, cur-0.15), None)
        speak("Ovoz kamaytirildi"); return True

    return False


# ══════════════════════════════════════════════════════════════════════
#  SCREENSHOT
# ══════════════════════════════════════════════════════════════════════
def take_screenshot():
    fname = datetime.datetime.now().strftime("jarvis_%Y-%m-%d_%H-%M-%S.png")
    path  = os.path.join(DESKTOP, fname)
    if PA_OK:
        pyautogui.screenshot().save(path)
        speak("Screenshot Desktop ga saqlandi")
    else:
        subprocess.run("snippingtool /clip", shell=True)
        speak("Screenshot clipboard ga saqlandi")


# ══════════════════════════════════════════════════════════════════════
#  VAQT / SANA
# ══════════════════════════════════════════════════════════════════════
MONTHS_UZ = ["", "yanvar", "fevral", "mart", "aprel", "may", "iyun",
             "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
DAYS_UZ   = ["dushanba", "seshanba", "chorshanba", "payshanba",
             "juma", "shanba", "yakshanba"]

def get_time():
    n = datetime.datetime.now()
    period = ("tong" if 5 <= n.hour < 12 else
              "kunduz" if n.hour < 17 else
              "kechqurun" if n.hour < 21 else "tun")
    return f"Hozir soat {n.hour}:{n.minute:02d}. {period.capitalize()}."

def get_date():
    n = datetime.datetime.now()
    return (f"Bugun {DAYS_UZ[n.weekday()]}, "
            f"{n.day} {MONTHS_UZ[n.month]}, {n.year} yil.")


# ══════════════════════════════════════════════════════════════════════
#  OB-HAVO
# ══════════════════════════════════════════════════════════════════════
def get_weather(city=CITY_NAME):
    if not RQ_OK or WEATHER_API_KEY in ("", "YOUR_OPENWEATHER_API_KEY"):
        return "Ob-havo API sozlanmagan"
    try:
        url  = (f"https://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=uz")
        data = requests.get(url, timeout=5).json()
        t    = round(data["main"]["temp"])
        desc = data["weather"][0]["description"]
        wind = round(data["wind"]["speed"])
        return (f"{city}da hozir {t} daraja, {desc}. "
                f"Shamol {wind} metr per sekund.")
    except Exception:
        return "Ob-havo ma'lumotini olib bo'lmadi"


# ══════════════════════════════════════════════════════════════════════
#  YOUTUBE / WEB
# ══════════════════════════════════════════════════════════════════════
def play_youtube(query: str):
    webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ','+')}")
    speak(f"YouTube da {query} ochilmoqda")

def web_search(query: str):
    webbrowser.open(f"https://www.google.com/search?q={query.replace(' ','+')}")
    speak(f"{query} qidirilmoqda")


# ══════════════════════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════════════════════
def load_contacts():
    cfile = os.path.join(os.path.dirname(__file__), "contacts.json")
    try:
        with open(cfile, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception: return {}


def open_telegram_contact(cmd: str) -> bool:
    contacts = load_contacts()
    matched  = None; info = None
    for name, cinfo in contacts.items():
        if name.lower() in cmd:
            matched = name; info = cinfo; break
    if not info:
        speak("Bu kontakt topilmadi"); return True
    display = info.get("display", matched.capitalize())
    try:
        if info.get("type") == "username":
            os.startfile(f"tg://resolve?domain={info['username']}")
        else:
            os.startfile(f"https://t.me/{info.get('phone','').replace('+','')}")
        speak(f"Telegramda {display} chati ochilmoqda")
    except Exception:
        webbrowser.open("https://web.telegram.org/")
        speak("Telegram ochilmoqda")
    return True


# ══════════════════════════════════════════════════════════════════════
#  AI  —  Claude
# ══════════════════════════════════════════════════════════════════════
ai_history = []

def ask_ai(question: str) -> str:
    if not AN_OK:
        return "Anthropic kutubxonasi o'rnatilmagan"
    if not CLAUDE_API_KEY or CLAUDE_API_KEY in ("", "YOUR_ANTHROPIC_API_KEY"):
        return "Claude API kaliti sozlanmagan"
    set_state("thinking")
    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        ai_history.append({"role": "user", "content": question})
        resp   = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=AI_SYSTEM_PROMPT,
            messages=ai_history[-10:]
        )
        answer = resp.content[0].text
        ai_history.append({"role": "assistant", "content": answer})
        logger.info(f"AI Q: {question[:50]} | A: {answer[:50]}")
        return answer
    except Exception as e:
        logger.error(f"Claude xatosi: {e}")
        return f"AI xatosi: {e}"
    finally:
        set_state("idle")


# ══════════════════════════════════════════════════════════════════════
#  BUYRUQLARNI QAYTA ISHLASH  —  asosiy router
# ══════════════════════════════════════════════════════════════════════
def _record(cmd: str, resp: str):
    """Tarixi va logga yozish"""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    command_history.append((ts, cmd, resp))
    if len(command_history) > 200:
        command_history.pop(0)
    logger.info(f"CMD: {cmd} | RESP: {resp[:60]}")


def process_command(cmd: str) -> bool:
    """True → davom et | False → dasturni yop"""
    if not cmd: return True
    cmd = cmd.strip()

    # ── Chiqish ──────────────────────────────────────────────────────
    EXIT_WORDS = ["xayr", "yopil", "yop", "chiq", "ketdim", "off",
                  "stop jarvis", "jarvis yopil", "dasturni yop", "quit"]
    if any(w in cmd for w in EXIT_WORDS):
        speak("Xayr! Ko'rishguncha.")
        return False

    # ── Toxta ────────────────────────────────────────────────────────
    PAUSE_WORDS = ["toxta", "to'xta", "jim bo'l", "yetarli", "bas"]
    if any(w in cmd for w in PAUSE_WORDS):
        if PG_OK:
            try: pygame.mixer.music.stop()
            except Exception: pass
        # Navbatni tozalash
        while not _speech_queue.empty():
            try: _speech_queue.get_nowait()
            except Exception: pass
        set_state("idle")
        play_beep(660, 100)
        _record(cmd, "[to'xtatildi]")
        return True

    # ── Kompyuter boshqaruvi ─────────────────────────────────────────
    if control_computer(cmd):
        _record(cmd, "kompyuter buyruqi")
        return True

    # ── Screenshot ───────────────────────────────────────────────────
    if any(w in cmd for w in ["screenshot", "ekran surat", "skrinshot"]):
        take_screenshot()
        _record(cmd, "screenshot"); return True

    # ── Vaqt ─────────────────────────────────────────────────────────
    if any(w in cmd for w in ["soat", "vaqt", "nechchi"]):
        resp = get_time(); speak(resp)
        _record(cmd, resp); return True

    # ── Sana ─────────────────────────────────────────────────────────
    if (any(w in cmd for w in ["sana", "kun necha", "bugun"])
            and "ob-havo" not in cmd):
        resp = get_date(); speak(resp)
        _record(cmd, resp); return True

    # ── Ob-havo ──────────────────────────────────────────────────────
    if any(w in cmd for w in ["ob-havo", "havo", "harorat"]):
        city_m = re.search(r'(\w+)da\s+(?:ob-havo|havo)', cmd)
        city   = city_m.group(1).capitalize() if city_m else CITY_NAME
        resp   = get_weather(city); speak(resp)
        _record(cmd, resp); return True

    # ── Ovoz ─────────────────────────────────────────────────────────
    if "ovoz" in cmd and control_volume(cmd):
        _record(cmd, "ovoz"); return True

    # ── Tizim statistikasi ───────────────────────────────────────────
    STATS_WORDS = ["cpu", "ram", "batareya", "xotira", "disk",
                   "tizim holati", "kompyuter holati"]
    if any(w in cmd for w in STATS_WORDS):
        stats = fm_get_stats()
        resp  = format_system_stats(stats)
        speak(resp); _record(cmd, resp); return True

    # ── Internet tezligi ─────────────────────────────────────────────
    if any(w in cmd for w in ["internet", "ping", "tarmoq"]):
        resp = check_internet_speed(); speak(resp)
        _record(cmd, resp); return True

    # ── Valyuta ──────────────────────────────────────────────────────
    CURRENCY_WORDS = ["dollar", "euro", "evro", "rubl", "so'm", "kurs",
                      "valyuta", "tenge", "lira", "yuan"]
    if any(w in cmd for w in CURRENCY_WORDS):
        resp = parse_currency_cmd(cmd); speak(resp)
        _record(cmd, resp); return True

    # ── Tarjima ──────────────────────────────────────────────────────
    if any(w in cmd for w in ["tarjima", "translate"]):
        resp = parse_translate_cmd(cmd); speak(resp)
        _record(cmd, resp); return True

    # ── Yangiliklar ──────────────────────────────────────────────────
    if any(w in cmd for w in ["yangilik", "xabar", "news"]):
        topic = None
        for kw in ["yangilik", "xabar", "news", "haqida", "bo'yicha"]:
            cmd_c = cmd.replace(kw, "").strip()
        topic = cmd_c if len(cmd_c) > 3 else None
        resp  = get_news_rss(topic); speak(resp)
        _record(cmd, resp); return True

    # ── Eslatmalar ───────────────────────────────────────────────────
    REMIND_WORDS = ["eslatib qo'y", "eslatib qoy", "eslatma",
                    "reminder", "soatga", "daqiqadan keyin"]
    if any(w in cmd for w in REMIND_WORDS):
        duration = parse_duration(cmd)
        if duration:
            msg = parse_reminder_message(cmd)
            rid = set_reminder(duration, msg, speak)
            human_time = format_time_left(duration)
            resp = f"Eslatma o'rnatildi: {human_time} dan keyin «{msg}»"
            speak(resp); _record(cmd, resp)
        else:
            speak("Qancha vaqtdan keyin eslatish kerak?")
        return True

    if any(w in cmd for w in ["eslatmalarni ko'rsat", "eslatmalar ro'yxat",
                               "qanday eslatmalar"]):
        reminders = list_reminders()
        if not reminders:
            resp = "Hech qanday eslatma yo'q"
        else:
            lines = [f"{i}. {format_time_left(s)}: {m}"
                     for i, (rid, s, m) in enumerate(reminders, 1)]
            resp = "Eslatmalar:\n" + "\n".join(lines)
        speak(resp); _record(cmd, resp); return True

    # ── Kundalik ─────────────────────────────────────────────────────
    JOURNAL_WORDS = ["kundalikka", "kundalik yoz", "journal",
                     "bugun nima qild", "yozib qo'y"]
    if any(w in cmd for w in JOURNAL_WORDS):
        # Matnni ajratish
        text = cmd
        for kw in ["kundalikka", "kundalik", "yoz", "qo'y", "journal"]:
            text = text.replace(kw, "")
        text = text.strip(" ,.-")
        if text:
            add_journal(text)
            resp = f"Kundalikka yozildi: {text[:50]}"
        else:
            resp = "Nima yozishni aytmadingiz"
        speak(resp); _record(cmd, resp); return True

    if any(w in cmd for w in ["kundalikni ko'rsat", "bugungi kundalik",
                               "kundalikni o'qi"]):
        entries = get_journal()
        if not entries:
            resp = "Bugun kundalikda hech narsa yo'q"
        else:
            resp = "Bugungi kundalik: " + ". ".join(e["text"] for e in entries)
        speak(resp); _record(cmd, resp); return True

    # ── Vazifalar ────────────────────────────────────────────────────
    TASK_WORDS = ["vazifa qo'sh", "vazifa qo", "todo qo'sh",
                  "vazifani qo'sh", "task"]
    if any(w in cmd for w in TASK_WORDS):
        text = cmd
        for kw in ["vazifa qo'sh", "vazifa", "qo'sh", "todo", "task"]:
            text = text.replace(kw, "")
        text = text.strip(" ,.-")
        if text:
            t    = add_task(text)
            resp = f"Vazifa qo'shildi: {text[:50]}"
        else:
            resp = "Qanday vazifa qo'shishni aytmadingiz"
        speak(resp); _record(cmd, resp); return True

    if any(w in cmd for w in ["vazifalarni ko'rsat", "vazifalar ro'yxat",
                               "qanday vazifalar", "todo ro'yxat"]):
        tasks = get_tasks()
        resp  = format_tasks_text(tasks)
        speak(resp[:200]); _record(cmd, resp); return True

    DONE_WORDS = ["bajarildi", "bajarilgan", "vazifani yopib qo'y",
                  "vazifani tugatdim"]
    if any(w in cmd for w in DONE_WORDS):
        num = re.search(r'\b(\d+)\b', cmd)
        if num:
            task_id = int(num.group(1))
            if complete_task(task_id):
                resp = f"{task_id}-vazifa bajarilgan deb belgilandi"
            else:
                resp = "Bunday vazifa topilmadi"
        else:
            resp = "Qaysi vazifa? Raqamini ayting"
        speak(resp); _record(cmd, resp); return True

    # ── Xotira ───────────────────────────────────────────────────────
    if any(w in cmd for w in ["eslab qol", "xotirla", "yodlab qol"]):
        # "mening ismim Ali, eslab qol" → save_memory("ism", "Ali")
        kv_m = re.search(r'(mening\s+)?(.+?)\s+(?:eslab|yodlab|xotirla)', cmd)
        if kv_m:
            raw   = kv_m.group(2).strip()
            parts = raw.split()
            key   = parts[0] if parts else "nota"
            val   = " ".join(parts[1:]) if len(parts) > 1 else raw
            save_memory(key, val)
            resp = f"Eslab qolindi: {key} = {val}"
        else:
            resp = "Nima eslab qolishimni aytmadingiz"
        speak(resp); _record(cmd, resp); return True

    if any(w in cmd for w in ["nimani eslab qolding", "xotirangni ko'rsat",
                               "mening ma'lumotlarim"]):
        data = get_all_memory()
        if data:
            resp = "Xotiramda: " + ", ".join(f"{k}: {v}" for k, v in
                                              list(data.items())[:5])
        else:
            resp = "Xotiramda hech narsa yo'q"
        speak(resp); _record(cmd, resp); return True

    # ── Spotify ──────────────────────────────────────────────────────
    SPOTIFY_WORDS = ["spotify", "spotifiy"]
    if any(w in cmd for w in SPOTIFY_WORDS):
        if any(w in cmd for w in ["qo'y", "qoy", "ijro", "play"]):
            q = cmd
            for kw in SPOTIFY_WORDS + ["qo'y", "qoy", "da", "ni"]:
                q = q.replace(kw, "")
            q = q.strip()
            if q:
                resp = spotify_search_play(q)
            else:
                resp = spotify_resume()
        elif any(w in cmd for w in ["toxta", "pauza", "pause"]):
            resp = spotify_pause()
        elif any(w in cmd for w in ["keyingi", "next"]):
            resp = spotify_next()
        elif any(w in cmd for w in ["oldingi", "prev"]):
            resp = spotify_prev()
        elif any(w in cmd for w in ["nima ijro", "qaysi qo'shiq", "hozir nima"]):
            resp = spotify_current()
        else:
            resp = spotify_current()
        speak(resp); _record(cmd, resp); return True

    # ── Media tugmalar ───────────────────────────────────────────────
    MEDIA_WORDS = {
        "keyingi qo'shiq": media_next,
        "oldingi qo'shiq": media_prev,
        "musiqani pauza": media_play_pause,
        "musiqani davom": media_play_pause,
        "musiqani to'xtat": media_stop,
    }
    for phrase, fn in MEDIA_WORDS.items():
        if phrase in cmd:
            fn(); speak("Bajarildi")
            _record(cmd, phrase); return True

    # ── Oyna boshqaruvi ──────────────────────────────────────────────
    WIN_OPS = [
        (["minimlashtir", "minimal"], "minimize"),
        (["to'liq ekran", "maksimum", "maximizat"], "maximize"),
        (["oynani yop", "oynani o'chir"], "close"),
        (["barcha oynalarni", "hammasini minimal"], "minimize_all"),
    ]
    for keywords, op in WIN_OPS:
        if any(w in cmd for w in keywords):
            if op == "minimize_all":
                resp = minimize_all_windows()
            else:
                # Oyna nomini topish
                win_name = re.sub(
                    r'\b(minimlashtir|to\'liq ekran|maksimum|oynani yop|barcha)\b',
                    '', cmd).strip()
                if not win_name:
                    win_name = "Chrome"
                fn_map = {"minimize": minimize_window,
                          "maximize": maximize_window,
                          "close":    close_window}
                resp = fn_map[op](win_name)
            speak(resp); _record(cmd, resp); return True

    # ── Clipboard ────────────────────────────────────────────────────
    if any(w in cmd for w in ["clipboard", "nusxalangan", "nusxa olindi"]):
        text = get_clipboard()
        if text:
            resp = f"Clipboardda: {text[:80]}"
        else:
            resp = "Clipboard bo'sh"
        speak(resp); _record(cmd, resp); return True

    # ── Fayl boshqaruvi ──────────────────────────────────────────────
    FILE_OPEN_WORDS = ["papkani och", "papka och", "ochib ko'rsat"]
    if any(w in cmd for w in FILE_OPEN_WORDS):
        folder = parse_folder_from_cmd(cmd)
        if folder:
            resp = open_folder(folder)
        else:
            resp = open_folder(DESKTOP)
        speak(resp); _record(cmd, resp); return True

    if any(w in cmd for w in ["oxirgi fayl", "so'nggi fayl", "yuklanganlar"]):
        resp = get_recent_download()
        speak(resp); _record(cmd, resp); return True

    # ── Jarayonlar ───────────────────────────────────────────────────
    if any(w in cmd for w in ["jarayonlar", "qaysi dasturlar", "processlar"]):
        resp = get_top_processes()
        speak(resp[:200]); _record(cmd, resp); return True

    KILL_WORDS = ["ni to'xtat", "ni o'ldir", "ni yop"]
    if any(w in cmd for w in KILL_WORDS):
        # "chrome ni to'xtat" → "chrome"
        app = cmd
        for kw in KILL_WORDS + ["ni"]:
            app = app.replace(kw, "")
        app = app.strip()
        if app:
            resp = kill_process(app)
        else:
            resp = "Qaysi dasturni to'xtatish kerak?"
        speak(resp); _record(cmd, resp); return True

    # ── Sozlamalar oynasi ────────────────────────────────────────────
    if any(w in cmd for w in ["sozlamalar", "settings", "konfiguratsiya"]):
        threading.Thread(target=open_settings_window, daemon=True).start()
        speak("Sozlamalar oynasi ochildi")
        return True

    # ── Tarixi ───────────────────────────────────────────────────────
    if any(w in cmd for w in ["tarixi", "history", "avvalgi buyruqlar"]):
        threading.Thread(target=open_history_window, daemon=True).start()
        speak("Buyruqlar tarixi ochildi")
        return True

    # ── YouTube ──────────────────────────────────────────────────────
    YT_WORDS = ["youtube", "yutub", "utub"]
    is_yt = any(w in cmd for w in YT_WORDS)
    if is_yt or any(w in cmd for w in ["qo'shiq qo'y", "musiqa qo'y"]):
        q = cmd
        for yw in YT_WORDS:
            q = q.replace(yw, "")
        q = re.sub(r"\b(ga|da|kir|och|ni|qo['']y|musiqa|qo['']shiq)\b", '', q).strip()
        if q:
            play_youtube(q)
        else:
            webbrowser.open("https://www.youtube.com")
            speak("YouTube ochilmoqda")
        _record(cmd, "youtube"); return True

    # ── Saytlar ──────────────────────────────────────────────────────
    SITES = {
        "google":    "https://www.google.com",
        "gmail":     "https://mail.google.com",
        "instagram": "https://www.instagram.com",
        "tiktok":    "https://www.tiktok.com",
        "facebook":  "https://www.facebook.com",
        "github":    "https://www.github.com",
        "chatgpt":   "https://www.chatgpt.com",
    }
    for site, url in SITES.items():
        if site in cmd and any(w in cmd for w in ["kir", "och", "ocha", "ochib"]):
            webbrowser.open(url)
            speak(f"{site.capitalize()} ochilmoqda")
            _record(cmd, site); return True

    # ── Google qidiruv ───────────────────────────────────────────────
    for pattern in [r"google(?:\s+da)?\s+(.+?)\s+qidir",
                    r"qidir\s+(.+)", r"(.+)\s+qidir"]:
        m = re.search(pattern, cmd)
        if m:
            web_search(m.group(1).strip())
            _record(cmd, "google"); return True

    # ── Telegram ─────────────────────────────────────────────────────
    contacts = load_contacts()
    if "telegram" in cmd or any(n.lower() in cmd for n in contacts):
        if any(n.lower() in cmd for n in contacts):
            _record(cmd, "telegram contact")
            return open_telegram_contact(cmd)
        open_app("telegram")
        return True

    # ── Ilovalar ─────────────────────────────────────────────────────
    open_words = ["och", "ochib", "ishga tushir", "yoq", "start"]
    if any(w in cmd for w in open_words):
        if open_app(cmd):
            _record(cmd, "app open"); return True

    if open_app(cmd):
        _record(cmd, "app open"); return True

    # ── AI fallback ──────────────────────────────────────────────────
    speak("Bir daqiqa...")
    answer = ask_ai(cmd)
    speak(answer)
    _record(cmd, answer)
    return True


# ══════════════════════════════════════════════════════════════════════
#  ASOSIY TSIKL
# ══════════════════════════════════════════════════════════════════════
def main_loop():
    # Spotify ni ishga tushirish
    if (SPOTIFY_CLIENT_ID and
            not SPOTIFY_CLIENT_ID.startswith("YOUR")):
        if init_spotify(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET):
            logger.info("Spotify ulandi")
        else:
            logger.warning("Spotify ulanmadi")

    speak("Salom! Jarvis v3 tayyor. Meni chaqiring.")

    _last_wake = 0
    _COOLDOWN  = 2.5

    while True:
        print("👂 'Jarvis' deng...")
        if listen_wake_word():
            now = time.time()
            if now - _last_wake < _COOLDOWN:
                time.sleep(0.3); continue
            _last_wake = now

            play_beep(880, 120); time.sleep(0.04); play_beep(1100, 80)
            set_state("listening")
            print("🎤 Gapiring...")
            cmd = listen(timeout=8, phrase_limit=14)
            if cmd:
                if not process_command(cmd):
                    break
            else:
                play_beep(400, 150)
                set_state("idle")
        time.sleep(0.05)

    print("Jarvis yopildi.")


def main_keyboard():
    print("\n🤖 JARVIS v3 — Klaviatura Test Rejimi\n   'yop' → chiqish\n")
    speak("Jarvis v3 test rejimida tayyor")
    while True:
        try:
            cmd = input("👤 Buyruq: ").lower().strip()
            if not cmd: continue
            if not process_command(cmd): break
        except KeyboardInterrupt:
            speak("Xayr!"); break


# ══════════════════════════════════════════════════════════════════════
#  ISHGA TUSHIRISH
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ensure_single_instance()
    keyboard_mode = "--keyboard" in sys.argv

    if keyboard_mode:
        main_keyboard()
    else:
        anim_thread = threading.Thread(target=start_animation, daemon=True)
        anim_thread.start()
        time.sleep(0.8)

        try:
            main_loop()
        except KeyboardInterrupt:
            speak("Xayr Pashol naxuy!")
        finally:
            if anim_window:
                try: anim_window.stop()
                except Exception: pass

        # Speech navbatini yopish
        _speech_queue.put(None)
