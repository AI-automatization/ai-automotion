"""
JARVIS v3 — Konfiguratsiya

API kalitlarni .env faylga yozing (xavfsizroq):
  echo CLAUDE_API_KEY=sk-ant-... >> .env
  echo WEATHER_API_KEY=abc...    >> .env

Yoki shu yerda to'g'ridan to'g'ri to'ldiring (tavsiya etilmaydi).
"""
import os

# .env fayldan yuklash (agar dotenv o'rnatilgan bo'lsa)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

USERNAME = os.environ.get("USERNAME", "User")


# ============================================================
#  API KALITLAR  ← .env faylga ko'chiring!
# ============================================================
CLAUDE_API_KEY        = os.environ.get("CLAUDE_API_KEY", "")
WEATHER_API_KEY       = os.environ.get("WEATHER_API_KEY", "")
SPOTIFY_CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")



# ============================================================
#  SHAHAR
# ============================================================
CITY_NAME    = os.environ.get("CITY_NAME",  "Tashkent")
WEATHER_LANG = "uz"


# ============================================================
#  OVOZ SOZLAMALARI
# ============================================================
WAKE_WORD   = "jarvis"
LISTEN_LANG = "uz-UZ"

# edge-tts ovozlari:
#   uz-UZ-MadinaNeural  → Ayol ovozi (tavsiya)
#   uz-UZ-SardorNeural  → Erkak ovozi
EDGE_VOICE  = os.environ.get("EDGE_VOICE", "uz-UZ-MadinaNeural")


# ============================================================
#  AI TIZIM XABARI
# ============================================================
AI_SYSTEM_PROMPT = """Siz Jarvis — aqlli ovozli yordamchisiz. Windows kompyuter ustida ishlaysiz.
Qoidalar:
1. Faqat O'zbek tilida qisqa (1-2 jumla) javob bering.
2. Siz kompyuter buyruqlarini bajarasiz — "bajarolmayman" demang.
3. Texnik savollarga aniq, foydali javob bering.
4. Salomlashilsa: "Xayrli kun! Qanday yordam bera olaman?" deng.
5. Noto'g'ri so'rov bo'lsa: "Tushunmadim, qaytadan ayting" deng.
6. Hech qachon uzun tushuntirma bermang — ovozda gapiriladi."""


# ============================================================
#  DASTURLAR RO'YXATI
# ============================================================
APPS = {
    # Brauzerlar
    "chrome":          r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome":   r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":         r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",

    # Dasturchilik
    "vs code":         rf"C:\Users\{USERNAME}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode":          rf"C:\Users\{USERNAME}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "webstorm":        rf"C:\Program Files\JetBrains\WebStorm 2024.3\bin\webstorm64.exe",
    "android studio":  rf"C:\Program Files\Android\Android Studio\bin\studio64.exe",
    "terminal":        "wt.exe",
    "cmd":             "cmd.exe",
    "powershell":      "powershell.exe",
    "pycharm":         rf"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe",
    "intellij":        rf"C:\Program Files\JetBrains\IntelliJ*\bin\idea64.exe",
    "postman":         rf"C:\Users\{USERNAME}\AppData\Local\Postman\Postman.exe",

    # Ijtimoiy
    "telegram":        rf"C:\Users\{USERNAME}\AppData\Roaming\Telegram Desktop\Telegram.exe",
    "discord":         rf"C:\Users\{USERNAME}\AppData\Local\Discord\app-*\Discord.exe",
    "zoom":            rf"C:\Users\{USERNAME}\AppData\Roaming\Zoom\bin\Zoom.exe",
    "skype":           rf"C:\Users\{USERNAME}\AppData\Roaming\Microsoft\Teams\current\Teams.exe",
    "slack":           rf"C:\Users\{USERNAME}\AppData\Local\slack\slack.exe",

    # Musiqa / Video
    "spotify":         rf"C:\Users\{USERNAME}\AppData\Roaming\Spotify\Spotify.exe",
    "vlc":             r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "media player":    r"C:\Program Files\Windows Media Player\wmplayer.exe",

    # Ofis
    "word":            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":           r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint":      r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "outlook":         r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
    "onenote":         r"C:\Program Files\Microsoft Office\root\Office16\ONENOTE.EXE",

    # Windows
    "notepad":         "notepad.exe",
    "calculator":      "calc.exe",
    "paint":           "mspaint.exe",
    "explorer":        "explorer.exe",
    "task manager":    "taskmgr.exe",
    "settings":        "ms-settings:",
    "sozlamalar":      "ms-settings:",
    "registry":        "regedit.exe",
    "services":        "services.msc",
}
