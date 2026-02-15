"""
JARVIS — Text-to-Speech
Dedicated asyncio event loop — shutdown crash yo'q (Bug #asyncio fix)
"""
import asyncio, threading, time, queue

try:
    import edge_tts; ET_OK = True
except ImportError:
    ET_OK = False

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    PG_OK = True
except ImportError:
    PG_OK = False

try:
    import winsound; WS_OK = True
except ImportError:
    WS_OK = False

# ── Lazy import (circular prevent) ───────────────────────
def _get_deps():
    from modules.core import State, state_manager, temp_manager
    from modules.logger import logger
    from config import EDGE_VOICE
    return State, state_manager, temp_manager, logger, EDGE_VOICE


# ── Dedicated event loop — Bug asyncio fix ───────────────
_speech_queue = queue.Queue()
_speech_loop  = asyncio.new_event_loop()


async def _tts_async(text: str, voice: str, path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)


def _do_speak(text: str):
    State, state_manager, temp_manager, logger, EDGE_VOICE = _get_deps()

    print(f"\n🤖 Jarvis: {text}\n")
    logger.info(f"SPEAK: {text}")
    state_manager.set(State.SPEAKING)

    if not (ET_OK and PG_OK):
        time.sleep(len(text) * 0.04)          # Animatsiya uchun fake delay
        state_manager.is_speaking.clear()
        state_manager.set(State.IDLE)
        return

    tmp = None
    try:
        tmp = temp_manager.create(".mp3")
        # Bug fix: dedicated loop, asyncio.run() EMAS
        _speech_loop.run_until_complete(_tts_async(text, EDGE_VOICE, tmp))

        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()

    except Exception as e:
        logger.error(f"TTS xatosi: {e}")
    finally:
        time.sleep(0.35)                       # Aks-sado uchun pauza
        state_manager.is_speaking.clear()
        state_manager.set(State.IDLE)
        if tmp:
            temp_manager.delete(tmp)


def _speak_worker():
    asyncio.set_event_loop(_speech_loop)
    while True:
        text = _speech_queue.get()
        if text is None:
            break
        _do_speak(text)
        _speech_queue.task_done()


# ── Public API ────────────────────────────────────────────
def speak(text: str):
    """Ovozli chiqish — non-blocking"""
    _speech_queue.put(text)


def speak_and_wait(text: str):
    """Sinxron ovozli chiqish — tugaguncha kutadi"""
    speak(text)
    _speech_queue.join()


def stop_speaking():
    """Hozirgi gapni to'xtatish"""
    if PG_OK:
        try: pygame.mixer.music.stop()
        except Exception: pass
    while not _speech_queue.empty():
        try:
            _speech_queue.get_nowait()
            _speech_queue.task_done()
        except Exception:
            pass
    from modules.core import State, state_manager
    state_manager.is_speaking.clear()
    state_manager.set(State.IDLE)


def play_beep(freq: int = 880, duration_ms: int = 200):
    if WS_OK:
        try: winsound.Beep(freq, duration_ms)
        except Exception: pass


def shutdown_tts():
    """Atexit uchun"""
    _speech_queue.put(None)


# ── Worker thread ─────────────────────────────────────────
_t = threading.Thread(target=_speak_worker, daemon=True)
_t.start()
