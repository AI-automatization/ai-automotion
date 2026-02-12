"""
JARVIS — Media Boshqaruvi

• Spotify  — spotipy orqali (client_id/secret kerak)
• Media tugmalar — pyautogui orqali
• Oyna boshqaruvi — pygetwindow orqali
• Clipboard — pyperclip orqali
"""
import subprocess

# ── Kutubxonalarni tekshirish ──────────────────────────────────────────
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_OK = True
except ImportError:
    SPOTIPY_OK = False

try:
    import pygetwindow as gw
    PYGETWIN_OK = True
except ImportError:
    PYGETWIN_OK = False

try:
    import pyperclip
    PYPERCLIP_OK = True
except ImportError:
    PYPERCLIP_OK = False

try:
    import pyautogui
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


# ══════════════════════════════════════════════════════════════════════
#  SPOTIFY
# ══════════════════════════════════════════════════════════════════════
_sp = None

def init_spotify(client_id: str, client_secret: str,
                 redirect_uri: str = "http://localhost:8888/callback") -> bool:
    global _sp
    if not SPOTIPY_OK or not client_id or client_id.startswith("YOUR"):
        return False
    try:
        scope = ("user-modify-playback-state user-read-playback-state "
                 "user-read-currently-playing")
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            open_browser=True
        ))
        _sp.current_user()   # Test
        return True
    except Exception as e:
        print(f"   [Spotify init xatosi: {e}]")
        _sp = None
        return False


def spotify_search_play(query: str) -> str:
    if not _sp:
        return "Spotify ulangmagan"
    try:
        results = _sp.search(q=query, limit=1, type="track")
        items   = results.get("tracks", {}).get("items", [])
        if not items:
            return "Qo'shiq topilmadi"
        track = items[0]
        _sp.start_playback(uris=[track["uri"]])
        return f"{track['name']} — {track['artists'][0]['name']} qo'yilmoqda"
    except Exception as e:
        return f"Spotify xatosi: {e}"


def spotify_pause() -> str:
    if not _sp: return "Spotify ulangmagan"
    try:
        _sp.pause_playback(); return "Pauza qilindi"
    except Exception: return "Pauza qilib bo'lmadi"


def spotify_resume() -> str:
    if not _sp: return "Spotify ulangmagan"
    try:
        _sp.start_playback(); return "Davom ettirildi"
    except Exception: return "Davom ettirib bo'lmadi"


def spotify_next() -> str:
    if not _sp: return "Spotify ulangmagan"
    try:
        _sp.next_track(); return "Keyingi qo'shiq"
    except Exception: return "Xato"


def spotify_prev() -> str:
    if not _sp: return "Spotify ulangmagan"
    try:
        _sp.previous_track(); return "Oldingi qo'shiq"
    except Exception: return "Xato"


def spotify_current() -> str:
    if not _sp: return "Spotify ulangmagan"
    try:
        cur = _sp.currently_playing()
        if not cur or not cur.get("item"):
            return "Hozir hech narsa ijro etilmayapti"
        item    = cur["item"]
        name    = item["name"]
        artist  = item["artists"][0]["name"]
        is_play = cur["is_playing"]
        status  = "ijro etilmoqda" if is_play else "pauza"
        return f"{name} — {artist}, {status}"
    except Exception:
        return "Ma'lumot olib bo'lmadi"


def spotify_volume(percent: int) -> str:
    if not _sp: return "Spotify ulangmagan"
    try:
        _sp.volume(max(0, min(100, percent)))
        return f"Spotify ovozi {percent}%"
    except Exception:
        return "Ovoz o'zgartirib bo'lmadi"


# ══════════════════════════════════════════════════════════════════════
#  MEDIA TUGMALAR  (klaviatura virtual press)
# ══════════════════════════════════════════════════════════════════════
def media_play_pause():
    if PYAUTOGUI_OK:
        pyautogui.press("playpause")

def media_next():
    if PYAUTOGUI_OK:
        pyautogui.press("nexttrack")

def media_prev():
    if PYAUTOGUI_OK:
        pyautogui.press("prevtrack")

def media_stop():
    if PYAUTOGUI_OK:
        pyautogui.press("stop")


# ══════════════════════════════════════════════════════════════════════
#  OYNA BOSHQARUVI  (pygetwindow)
# ══════════════════════════════════════════════════════════════════════
def find_window(name: str):
    """Oyna nomiga qarab topish (qisman mos)"""
    if not PYGETWIN_OK:
        return None
    wins = gw.getWindowsWithTitle(name)
    return wins[0] if wins else None


def minimize_window(name: str) -> str:
    w = find_window(name)
    if w:
        w.minimize()
        return f"{name} minimallashtirildi"
    return f"{name} topilmadi"


def maximize_window(name: str) -> str:
    w = find_window(name)
    if w:
        w.maximize()
        return f"{name} to'liq ekranga chiqdi"
    return f"{name} topilmadi"


def close_window(name: str) -> str:
    w = find_window(name)
    if w:
        w.close()
        return f"{name} yopildi"
    return f"{name} topilmadi"


def restore_window(name: str) -> str:
    w = find_window(name)
    if w:
        w.restore()
        return f"{name} tiklandi"
    return f"{name} topilmadi"


def list_open_windows() -> list[str]:
    if not PYGETWIN_OK:
        return []
    return [w.title for w in gw.getAllWindows() if w.title.strip()]


def minimize_all_windows() -> str:
    if PYAUTOGUI_OK:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "Barcha oynalar minimallaştirildi"
    return "pyautogui o'rnatilmagan"


# ══════════════════════════════════════════════════════════════════════
#  CLIPBOARD
# ══════════════════════════════════════════════════════════════════════
def get_clipboard() -> str:
    if PYPERCLIP_OK:
        try:
            return pyperclip.paste() or ""
        except Exception:
            return ""
    # Fallback: PowerShell
    try:
        result = subprocess.run(
            ["powershell", "-command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=3
        )
        return result.stdout.strip()
    except Exception:
        return ""


def set_clipboard(text: str) -> bool:
    if PYPERCLIP_OK:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False
    try:
        subprocess.run(
            ["powershell", "-command", f"Set-Clipboard -Value '{text}'"],
            timeout=3
        )
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════
#  JARAYONLAR  (psutil)
# ══════════════════════════════════════════════════════════════════════
def get_top_processes(n: int = 5) -> list[dict]:
    """CPU va RAM bo'yicha eng ko'p ishlatayotgan N ta jarayon"""
    if not PSUTIL_OK:
        return []
    procs = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: x.get("memory_percent", 0),
                  reverse=True)[:n]


def kill_process_by_name(name: str) -> bool:
    """Jarayonni nomi bo'yicha o'ldirish"""
    if not PSUTIL_OK:
        return False
    killed = False
    for p in psutil.process_iter(["name"]):
        try:
            if name.lower() in p.info["name"].lower():
                p.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def get_system_stats() -> dict:
    """CPU, RAM, batareya, disk statistikasi"""
    if not PSUTIL_OK:
        return {}
    stats = {}
    try:
        stats["cpu"]    = round(psutil.cpu_percent(interval=0.1))
        mem             = psutil.virtual_memory()
        stats["ram"]    = round(mem.percent)
        stats["ram_gb"] = round(mem.used / (1024 ** 3), 1)
        stats["ram_total"] = round(mem.total / (1024 ** 3), 1)
        disk            = psutil.disk_usage("C:\\")
        stats["disk"]   = round(disk.percent)
        bat             = psutil.sensors_battery()
        if bat:
            stats["battery"]       = round(bat.percent)
            stats["battery_plug"]  = bat.power_plugged
    except Exception:
        pass
    return stats
