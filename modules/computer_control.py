"""
JARVIS — Kompyuter, Ilova va Telegram boshqaruvi
"""
import os, re, glob, json, subprocess, webbrowser, datetime

from modules.logger import logger
from modules.tts   import speak

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


def _desktop():
    from modules.file_manager import DESKTOP
    return DESKTOP

def _apps():
    from config import APPS
    return APPS


# ══════════════════════════════════════════════════════════
#  VOLUME  — "ovoz" so'zi majburiy
# ══════════════════════════════════════════════════════════
def _vol():
    if not PCW_OK: return None
    try:
        d = AudioUtilities.GetSpeakers()
        i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(i, POINTER(IAudioEndpointVolume))
    except Exception: return None


def set_volume_level(percent: int):
    """AI buyruqidan ovoz darajasini o'rnatish"""
    v = _vol()
    if v:
        v.SetMasterVolumeLevelScalar(max(0,min(100,percent)) / 100, None)


def control_volume(cmd: str) -> bool:
    if "ovoz" not in cmd:
        return False
    v = _vol()

    if any(w in cmd for w in ["o'chir", "jim", "mute"]):
        if v: v.SetMute(1, None)
        speak("Ovoz o'chirildi"); return True

    if any(w in cmd for w in ["yoq", "unmute"]):
        if v: v.SetMute(0, None)
        speak("Ovoz yoqildi"); return True

    num = re.search(r'\b(\d{1,3})\b', cmd)
    if num:
        lvl = max(0, min(100, int(num.group(1))))
        if v: v.SetMasterVolumeLevelScalar(lvl / 100, None)
        speak(f"Ovoz {lvl} foiz"); return True

    if any(w in cmd for w in ["oshir", "baland", "kattaroq"]):
        if v: v.SetMasterVolumeLevelScalar(min(1.0, v.GetMasterVolumeLevelScalar() + 0.15), None)
        speak("Ovoz oshirildi"); return True

    if any(w in cmd for w in ["kamayt", "past", "kichikroq"]):
        if v: v.SetMasterVolumeLevelScalar(max(0.0, v.GetMasterVolumeLevelScalar() - 0.15), None)
        speak("Ovoz kamaytirildi"); return True

    return False


# ══════════════════════════════════════════════════════════
#  KOMPYUTER BOSHQARUVI
# ══════════════════════════════════════════════════════════
def control_computer(cmd: str) -> bool:
    if any(w in cmd for w in ["hozir o'chir", "darhol o'chir"]):
        speak("Kompyuter o'chmoqda")
        subprocess.run("shutdown /s /t 0", shell=True); return True

    if any(w in cmd for w in ["kompyuterni o'chir", "shutdown"]):
        speak("Kompyuter 30 soniyada o'chadi")
        subprocess.run("shutdown /s /t 30", shell=True); return True

    if any(w in cmd for w in ["o'chirishni bekor", "cancel shutdown"]):
        subprocess.run("shutdown /a", shell=True)
        speak("O'chirish bekor qilindi"); return True

    if any(w in cmd for w in ["qayta yoq", "restart", "reboot"]):
        speak("Kompyuter qayta yoqilmoqda")
        subprocess.run("shutdown /r /t 5", shell=True); return True

    if any(w in cmd for w in ["uxlat", "sleep"]):
        speak("Kompyuter uxlatilmoqda")
        subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return True

    if any(w in cmd for w in ["ekranni qulf", "qulfla", "lock"]):
        import ctypes; ctypes.windll.user32.LockWorkStation()
        speak("Ekran quflandi"); return True

    return False


# ══════════════════════════════════════════════════════════
#  SCREENSHOT
# ══════════════════════════════════════════════════════════
def take_screenshot():
    fname = datetime.datetime.now().strftime("jarvis_%Y-%m-%d_%H-%M-%S.png")
    path  = os.path.join(_desktop(), fname)
    if PA_OK:
        pyautogui.screenshot().save(path)
        speak("Screenshot Desktop ga saqlandi")
    else:
        subprocess.run("snippingtool /clip", shell=True)
        speak("Screenshot clipboard ga saqlandi")


# ══════════════════════════════════════════════════════════
#  ILOVALAR
# ══════════════════════════════════════════════════════════
def open_app(cmd: str) -> bool:
    for key, path in _apps().items():
        if key in cmd:
            try:
                if path.startswith("ms-"):
                    os.startfile(path)
                elif "*" in path:
                    matches = glob.glob(path)
                    if matches: subprocess.Popen(matches[0], shell=True)
                    else: speak(f"{key} topilmadi"); return True
                else:
                    subprocess.Popen(path, shell=True)
                speak(f"{key.capitalize()} ochilmoqda")
            except Exception as e:
                logger.error(f"App {key}: {e}")
                speak(f"{key} ochib bo'lmadi")
            return True
    return False


# ══════════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════════
def load_contacts() -> dict:
    base  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfile = os.path.join(base, "contacts.json")
    try:
        with open(cfile, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}


def open_telegram_contact(cmd: str) -> bool:
    from modules.nlu import contact_match
    contacts = load_contacts()

    for name, info in contacts.items():
        if contact_match(name, cmd):
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
