"""
JARVIS — Fayl va Jarayon Boshqaruvi

• Fayl operatsiyalari (ochish, ko'chirish, ro'yxat)
• Papkalarni ochish
• Jarayonlarni boshqarish (psutil)
"""
import os
import re
import glob
import shutil
import subprocess
from datetime import datetime

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


# ── Uy papkasi va umumiy yo'llar ───────────────────────────────────────
HOME     = os.path.expanduser("~")
DESKTOP  = os.path.join(HOME, "Desktop")
DOWNLOADS= os.path.join(HOME, "Downloads")
DOCUMENTS= os.path.join(HOME, "Documents")
PICTURES = os.path.join(HOME, "Pictures")
MUSIC    = os.path.join(HOME, "Music")
VIDEOS   = os.path.join(HOME, "Videos")

FOLDER_MAP = {
    "desktop": DESKTOP,      "ish stoli": DESKTOP,
    "downloads": DOWNLOADS,  "yuklamalar": DOWNLOADS,
    "documents": DOCUMENTS,  "hujjatlar": DOCUMENTS,
    "pictures": PICTURES,    "rasmlar": PICTURES,
    "music": MUSIC,          "musiqa": MUSIC,
    "videos": VIDEOS,        "videolar": VIDEOS,
    "c": "C:\\",             "d": "D:\\",
    "e": "E:\\",
}

EXT_MAP = {
    "rasm": ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"),
    "video": ("*.mp4", "*.avi", "*.mkv", "*.mov", "*.wmv"),
    "musiqa": ("*.mp3", "*.wav", "*.flac", "*.aac", "*.ogg"),
    "hujjat": ("*.docx", "*.doc", "*.pdf", "*.txt", "*.xlsx"),
    "kod": ("*.py", "*.js", "*.ts", "*.html", "*.css", "*.java"),
    "arxiv": ("*.zip", "*.rar", "*.7z", "*.tar", "*.gz"),
}


# ══════════════════════════════════════════════════════════════════════
#  PAPKALAR
# ══════════════════════════════════════════════════════════════════════
def open_folder(path: str) -> str:
    """Windows Explorer da papkani ochish"""
    try:
        if os.path.exists(path):
            subprocess.Popen(f'explorer "{path}"')
            return f"Papka ochildi: {os.path.basename(path)}"
        else:
            return f"Papka topilmadi: {path}"
    except Exception as e:
        return f"Ochib bo'lmadi: {e}"


def parse_folder_from_cmd(cmd: str) -> str | None:
    """Buyruqdan papka nomini topish"""
    for name, path in FOLDER_MAP.items():
        if name in cmd:
            return path
    return None


# ══════════════════════════════════════════════════════════════════════
#  FAYLLAR
# ══════════════════════════════════════════════════════════════════════
def list_files(folder: str, pattern: str | None = None,
               n: int = 10) -> list[dict]:
    """
    Papkadagi fayllar ro'yxati.
    pattern: '*.mp3', '*.pdf', ...
    Returns: [{"name": ..., "size_kb": ..., "modified": ...}, ...]
    """
    if not os.path.exists(folder):
        return []
    patterns = ([pattern] if pattern else ["*"])
    files    = []
    for pat in patterns:
        for fp in glob.glob(os.path.join(folder, pat)):
            if os.path.isfile(fp):
                stat = os.stat(fp)
                files.append({
                    "name":      os.path.basename(fp),
                    "path":      fp,
                    "size_kb":   round(stat.st_size / 1024, 1),
                    "modified":  datetime.fromtimestamp(
                                     stat.st_mtime
                                 ).strftime("%Y-%m-%d %H:%M")
                })
    # Oxirgisi birinchi
    files.sort(key=lambda x: x["modified"], reverse=True)
    return files[:n]


def get_recent_download() -> str:
    """Oxirgi yuklab olingan fayl"""
    files = list_files(DOWNLOADS)
    if not files:
        return "Yuklamalar papkasi bo'sh"
    f = files[0]
    return f"Oxirgi fayl: {f['name']} ({f['size_kb']} KB)"


def open_file(path: str) -> str:
    """Faylni standart dasturda ochish"""
    try:
        os.startfile(path)
        return f"{os.path.basename(path)} ochildi"
    except Exception as e:
        return f"Ochib bo'lmadi: {e}"


def copy_file(src: str, dst_folder: str) -> str:
    """Faylni ko'chirish"""
    try:
        if not os.path.exists(src):
            return "Manba fayl topilmadi"
        dst = os.path.join(dst_folder, os.path.basename(src))
        shutil.copy2(src, dst)
        return f"{os.path.basename(src)} ko'chirildi"
    except Exception as e:
        return f"Ko'chirib bo'lmadi: {e}"


def delete_file(path: str) -> str:
    """Faylni o'chirish (recycle bin ga yubormasdan)"""
    try:
        if os.path.exists(path):
            os.remove(path)
            return f"{os.path.basename(path)} o'chirildi"
        return "Fayl topilmadi"
    except Exception as e:
        return f"O'chirib bo'lmadi: {e}"


def create_folder(parent: str, name: str) -> str:
    """Yangi papka yaratish"""
    try:
        path = os.path.join(parent, name)
        os.makedirs(path, exist_ok=True)
        return f"'{name}' papkasi yaratildi"
    except Exception as e:
        return f"Yaratib bo'lmadi: {e}"


# ══════════════════════════════════════════════════════════════════════
#  JARAYONLAR
# ══════════════════════════════════════════════════════════════════════
def get_top_processes(n: int = 5) -> str:
    """Eng ko'p xotira ishlatayotgan N ta jarayon"""
    if not PSUTIL_OK:
        return "psutil o'rnatilmagan"
    procs = []
    for p in psutil.process_iter(["name", "memory_percent", "cpu_percent"]):
        try:
            info = p.info
            if info["memory_percent"] and info["memory_percent"] > 0.1:
                procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
    lines = []
    for i, p in enumerate(procs[:n], 1):
        name = (p["name"] or "?")[:25]
        mem  = round(p.get("memory_percent", 0), 1)
        cpu  = round(p.get("cpu_percent", 0), 1)
        lines.append(f"{i}. {name} — RAM: {mem}%, CPU: {cpu}%")
    return "Eng ko'p ishlatayotgan jarayonlar:\n" + "\n".join(lines)


def kill_process(name: str) -> str:
    """Jarayonni to'xtatish"""
    if not PSUTIL_OK:
        return "psutil o'rnatilmagan"
    killed = []
    for p in psutil.process_iter(["name"]):
        try:
            if name.lower() in (p.info.get("name") or "").lower():
                pname = p.info["name"]
                p.kill()
                killed.append(pname)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if killed:
        return f"{', '.join(set(killed))} to'xtatildi"
    return f"'{name}' nomli jarayon topilmadi"


# ══════════════════════════════════════════════════════════════════════
#  TIZIM STATISTIKASI
# ══════════════════════════════════════════════════════════════════════
def get_system_stats() -> dict:
    """CPU, RAM, disk, batareya"""
    stats = {}
    if not PSUTIL_OK:
        return stats
    try:
        stats["cpu"]        = round(psutil.cpu_percent(interval=0.2))
        mem                 = psutil.virtual_memory()
        stats["ram"]        = round(mem.percent)
        stats["ram_used"]   = round(mem.used  / (1024**3), 1)
        stats["ram_total"]  = round(mem.total / (1024**3), 1)
        try:
            disk             = psutil.disk_usage("C:\\")
            stats["disk"]    = round(disk.percent)
            stats["disk_free"]= round(disk.free  / (1024**3), 1)
        except Exception:
            pass
        bat = psutil.sensors_battery()
        if bat:
            stats["battery"]      = round(bat.percent)
            stats["plugged"]      = bat.power_plugged
    except Exception:
        pass
    return stats


def format_system_stats(stats: dict) -> str:
    """Statistikani matnга aylantirish"""
    if not stats:
        return "Tizim ma'lumotlari olib bo'lmadi"
    parts = []
    if "cpu" in stats:
        parts.append(f"CPU: {stats['cpu']}%")
    if "ram" in stats:
        parts.append(f"RAM: {stats['ram']}% ({stats.get('ram_used',0)}/{stats.get('ram_total',0)} GB)")
    if "disk" in stats:
        parts.append(f"Disk C: {stats['disk']}% (bo'sh {stats.get('disk_free',0)} GB)")
    if "battery" in stats:
        plug = "⚡" if stats.get("plugged") else "🔋"
        parts.append(f"Batareya: {plug} {stats['battery']}%")
    return " | ".join(parts)
