"""
JARVIS — Speech-to-Text
MicGuard + normalize + word count check
"""
import time

try:
    import speech_recognition as sr
    _recognizer = sr.Recognizer()
    _recognizer.pause_threshold          = 0.8
    _recognizer.energy_threshold         = 300
    _recognizer.dynamic_energy_threshold = True
    SR_OK = True
except ImportError:
    sr = None; _recognizer = None; SR_OK = False

from modules.nlu import normalize_text, is_wake_word
from modules.core import State, state_manager, MicGuard


def _get_listen_lang():
    from config import LISTEN_LANG
    return LISTEN_LANG


def listen_command(timeout: int = 7, phrase_limit: int = 10) -> str | None:
    """
    Ovozli buyruq tinglash
    Bug #3: MicGuard — mic resource leak yo'q
    Bug #8: normalize_text — Kiril/Lotin
    Bug #10: word count — ikki kishi gapirsa bloklash
    """
    if not SR_OK:
        return None

    # Bug #1: Jarvis gapirayotsa kutish
    if state_manager.is_speaking.is_set():
        state_manager.is_speaking.wait(timeout=5)
        time.sleep(0.2)

    try:
        with MicGuard(sr) as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.1)
            audio = _recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit
            )

        raw  = _recognizer.recognize_google(audio, language=_get_listen_lang())
        text = normalize_text(raw)

        # Bug #10: juda uzun = ikki kishi gapirgan
        if len(text.split()) > 12:
            from modules.tts import speak
            speak("Bitta buyruq ayting")
            return None

        print(f"👤 Siz: {text}")
        from modules.logger import logger
        logger.info(f"USER: {text}")
        state_manager.set(State.IDLE)
        return text

    except sr.WaitTimeoutError:
        state_manager.set(State.IDLE); return None
    except sr.UnknownValueError:
        state_manager.set(State.IDLE); return None
    except Exception as e:
        from modules.logger import logger
        logger.warning(f"STT xatosi: {e}")
        state_manager.set(State.IDLE); return None


def listen_wake_word() -> bool:
    """
    Bug #1: Jarvis gapirayotsa tinglama
    Bug #3: MicGuard
    """
    if not SR_OK:
        return False
    if state_manager.is_speaking.is_set():
        return False

    try:
        with MicGuard(sr) as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.15)
            audio = _recognizer.listen(source, timeout=2, phrase_time_limit=3)

        raw  = _recognizer.recognize_google(audio, language=_get_listen_lang()).lower()
        text = normalize_text(raw)

        if is_wake_word(text):
            state_manager.set(State.LISTENING)
            return True
        return False

    except Exception:
        return False
