"""
JARVIS — Xotira, Kundalik va Vazifalar (To-Do) moduli

Fayllar:
  data/memory.json  — foydalanuvchi xotiralari (ism, sozlamalar)
  data/journal.json — kundalik yozuvlar
  data/tasks.json   — vazifalar ro'yxati
"""
import json
import os
from datetime import datetime

_BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR   = os.path.join(_BASE, "data")

MEMORY_FILE  = os.path.join(_DATA_DIR, "memory.json")
JOURNAL_FILE = os.path.join(_DATA_DIR, "journal.json")
TASKS_FILE   = os.path.join(_DATA_DIR, "tasks.json")

os.makedirs(_DATA_DIR, exist_ok=True)


# ── Yordamchi ──────────────────────────────────────────────────────────
def _load(path: str, default) -> dict | list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════
#  XOTIRA  — foydalanuvchi ma'lumotlari
# ══════════════════════════════════════════════════════════════════════
def save_memory(key: str, value) -> None:
    """Kalitni xotiraga saqlash"""
    data = _load(MEMORY_FILE, {})
    data[key] = value
    data["_updated"] = datetime.now().isoformat()
    _save(MEMORY_FILE, data)


def get_memory(key: str, default=None):
    """Kalitni xotiradan olish"""
    return _load(MEMORY_FILE, {}).get(key, default)


def get_all_memory() -> dict:
    return {k: v for k, v in _load(MEMORY_FILE, {}).items()
            if not k.startswith("_")}


def forget(key: str) -> bool:
    data = _load(MEMORY_FILE, {})
    if key in data:
        del data[key]
        _save(MEMORY_FILE, data)
        return True
    return False


# ══════════════════════════════════════════════════════════════════════
#  KUNDALIK  — journal
# ══════════════════════════════════════════════════════════════════════
def add_journal(text: str) -> None:
    """Kundalikka yozuv qo'shish"""
    entries = _load(JOURNAL_FILE, [])
    entries.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "text": text.strip()
    })
    _save(JOURNAL_FILE, entries)


def get_journal(date: str | None = None) -> list:
    """
    date = "2025-01-15"  → o'sha kun yozuvlari
    date = None          → bugungi kun
    """
    target = date or datetime.now().strftime("%Y-%m-%d")
    return [e for e in _load(JOURNAL_FILE, []) if e.get("date") == target]


def get_recent_journal(n: int = 5) -> list:
    """Oxirgi N ta yozuv"""
    entries = _load(JOURNAL_FILE, [])
    return entries[-n:]


# ══════════════════════════════════════════════════════════════════════
#  VAZIFALAR  — to-do list
# ══════════════════════════════════════════════════════════════════════
def add_task(text: str, priority: str = "normal") -> dict:
    """Yangi vazifa qo'shish. priority: 'high' | 'normal' | 'low'"""
    tasks = _load(TASKS_FILE, [])
    task = {
        "id":       len(tasks) + 1,
        "text":     text.strip(),
        "priority": priority,
        "done":     False,
        "created":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "finished": None
    }
    tasks.append(task)
    _save(TASKS_FILE, tasks)
    return task


def complete_task(task_id: int) -> bool:
    """Vazifani bajarilgan deb belgilash"""
    tasks = _load(TASKS_FILE, [])
    for t in tasks:
        if t["id"] == task_id:
            t["done"]     = True
            t["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            _save(TASKS_FILE, tasks)
            return True
    return False


def get_tasks(only_pending: bool = True) -> list:
    """Vazifalar ro'yxati. only_pending=True → faqat bajarilmaganlar"""
    tasks = _load(TASKS_FILE, [])
    return [t for t in tasks if not (only_pending and t["done"])]


def delete_task(task_id: int) -> bool:
    tasks = _load(TASKS_FILE, [])
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) < len(tasks):
        _save(TASKS_FILE, new_tasks)
        return True
    return False


def format_tasks_text(tasks: list) -> str:
    """Vazifalarni o'qiladigan matnga aylantirish"""
    if not tasks:
        return "Hech qanday vazifa yo'q"
    lines = []
    for i, t in enumerate(tasks, 1):
        icon = "✅" if t["done"] else ("🔴" if t["priority"] == "high" else "📌")
        lines.append(f"{icon} {i}. {t['text']}")
    return "\n".join(lines)
