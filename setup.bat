@echo off
chcp 65001 >nul 2>&1
title JARVIS v3 Setup

echo.
echo =====================================================
echo   JARVIS v3 - To'liq O'rnatish
echo =====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATO] Python topilmadi!
    echo python.org dan yuklab oring, "Add to PATH" ni belgilang
    pause & exit /b 1
)
python --version
echo [OK] Python topildi
echo.

echo [1/4] pip yangilanmoqda...
python -m pip install --upgrade pip --quiet

echo [2/4] Asosiy kutubxonalar o'rnatilmoqda...
pip install edge-tts pygame SpeechRecognition requests anthropic --quiet
pip install pyautogui pycaw comtypes Pillow --quiet
pip install psutil pygetwindow pyperclip --quiet
pip install deep-translator spotipy win10toast python-dotenv --quiet
echo [OK] Asosiy kutubxonalar tayyor

echo [3/4] PyAudio o'rnatilmoqda...
pip install pyaudio --quiet
if %errorlevel% neq 0 (
    echo PyAudio standart usulda o'rnatilmadi, pipwin urinilmoqda...
    pip install pipwin --quiet
    pipwin install pyaudio --quiet
    if %errorlevel% neq 0 (
        echo [OGOHLANTIRISH] PyAudio o'rnatilmadi - mikrofon ishlamasligi mumkin
    ) else (
        echo [OK] PyAudio tayyor (pipwin orqali)
    )
) else (
    echo [OK] PyAudio tayyor
)

echo [4/4] .env fayli tayyorlanmoqda...
if not exist ".env" (
    copy ".env.example" ".env" >nul 2>&1
    echo [OK] .env fayli yaratildi - API kalitlarni to'ldiring!
) else (
    echo [OK] .env fayli mavjud
)

echo.
echo --- Modullar tekshirilmoqda ---
python -c "import speech_recognition;  print('[OK] SpeechRecognition')" 2>nul || echo [XATO] SpeechRecognition
python -c "import edge_tts;            print('[OK] edge-tts')"          2>nul || echo [XATO] edge-tts
python -c "import pygame;              print('[OK] pygame')"            2>nul || echo [XATO] pygame
python -c "import anthropic;           print('[OK] anthropic')"         2>nul || echo [XATO] anthropic
python -c "import requests;            print('[OK] requests')"          2>nul || echo [XATO] requests
python -c "import psutil;              print('[OK] psutil')"            2>nul || echo [XATO] psutil
python -c "import pygetwindow;         print('[OK] pygetwindow')"       2>nul || echo [OGOHLANTIRISH] pygetwindow
python -c "import pyperclip;           print('[OK] pyperclip')"         2>nul || echo [OGOHLANTIRISH] pyperclip
python -c "import deep_translator;     print('[OK] deep-translator')"   2>nul || echo [OGOHLANTIRISH] deep-translator
python -c "import spotipy;             print('[OK] spotipy')"           2>nul || echo [OGOHLANTIRISH] spotipy
python -c "import win10toast;          print('[OK] win10toast')"        2>nul || echo [OGOHLANTIRISH] win10toast
python -c "import dotenv;              print('[OK] python-dotenv')"     2>nul || echo [OGOHLANTIRISH] python-dotenv
python -c "import pyaudio;             print('[OK] PyAudio')"           2>nul || echo [OGOHLANTIRISH] PyAudio
python -c "import pycaw;               print('[OK] pycaw')"             2>nul || echo [OGOHLANTIRISH] pycaw

echo.
echo --- Windows Autostart ---
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
(
echo @echo off
echo cd /d "%~dp0"
echo start /min pythonw.exe jarvis.py
) > "%STARTUP%\Jarvis.bat"
if exist "%STARTUP%\Jarvis.bat" (
    echo [OK] Autostart qo'shildi
) else (
    echo [XATO] Autostart qo'shib bo'lmadi
)

echo.
echo =====================================================
echo   O'rnatish yakunlandi!
echo =====================================================
echo.
echo MUHIM QADAMLAR:
echo   1. .env faylni oching
echo   2. CLAUDE_API_KEY ni yozing  (https://console.anthropic.com)
echo   3. WEATHER_API_KEY ni yozing (https://openweathermap.org)
echo   4. Spotify uchun: https://developer.spotify.com/dashboard
echo.
echo ISHGA TUSHIRISH:
echo   python jarvis.py             (ovozli + animatsiya)
echo   python jarvis.py --keyboard  (klaviatura test)
echo.
pause
