#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS — Mikrofon Diagnostika va Test
Ishlatish: python mic_test.py
"""
import sys

# ── Kutubxonalarni tekshirish ──────────────────────────────────────────
try:
    import speech_recognition as sr
    SR_OK = True
except ImportError:
    print("❌ SpeechRecognition topilmadi: pip install SpeechRecognition")
    SR_OK = False

try:
    import pyaudio
    PA_OK = True
except ImportError:
    print("❌ PyAudio topilmadi: pip install pyaudio")
    PA_OK = False


def list_microphones():
    """Barcha mavjud mikrofonlarni ko'rsatish"""
    if not PA_OK:
        return
    print("\n" + "="*55)
    print("  📢 Mavjud mikrofonlar (PyAudio):")
    print("="*55)
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get("maxInputChannels", 0) > 0:
            is_default = "  ← DEFAULT" if i == p.get_default_input_device_info()["index"] else ""
            print(f"  [{i:2d}] {info['name'][:45]}{is_default}")
    p.terminate()

    print("\n  📢 Mavjud mikrofonlar (SpeechRecognition):")
    print("-"*55)
    if SR_OK:
        mics = sr.Microphone.list_microphone_names()
        for i, name in enumerate(mics):
            print(f"  [{i:2d}] {name[:50]}")
    print("="*55)


def test_microphone(device_index=None, lang="uz-UZ"):
    """Mikrofon test — gapiring va tanib olishni ko'ring"""
    if not SR_OK:
        return
    
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.energy_threshold = 200  # Pastroq = sezgirroq
    r.pause_threshold  = 0.5
    
    mic_info = f"device_index={device_index}" if device_index is not None else "default"
    print(f"\n🎤 Mikrofon test [{mic_info}] | Til: {lang}")
    print("   5 soniya gapiring (masalan: 'jarvis' yoki 'salom')...")
    print("   [Ctrl+C] — to'xtatish\n")

    try:
        with sr.Microphone(device_index=device_index) as src:
            print(f"   📊 Ambient noise tekshirilmoqda...")
            r.adjust_for_ambient_noise(src, duration=1)
            print(f"   📊 Energy threshold: {r.energy_threshold:.0f}")
            print(f"   🔴 GAPIRING...\n")
            audio = r.listen(src, timeout=8, phrase_time_limit=5)
        
        print("   ⏳ Tanib olinmoqda...")
        # Bir nechta til bilan sinab ko'rish
        langs = [lang, "ru-RU", "en-US"]
        for l in langs:
            try:
                text = r.recognize_google(audio, language=l)
                print(f"   ✅ [{l}] Natija: '{text}'")
            except sr.UnknownValueError:
                print(f"   ❌ [{l}] Tushunilmadi")
            except sr.RequestError as e:
                print(f"   ❌ [{l}] Internet xatosi: {e}")
                
    except sr.WaitTimeoutError:
        print("   ⏰ Vaqt tugadi — hech narsa eshitilmadi")
        print("   💡 Maslahat: Mikrofon ulanganligi va ovoz ruxsatini tekshiring")
    except OSError as e:
        print(f"   ❌ Mikrofon xatosi: {e}")
    except KeyboardInterrupt:
        print("\n   [To'xtatildi]")


def find_best_microphone():
    """'naushnik', 'headset', 'headphone' ni topish"""
    if not SR_OK:
        return None
    keywords = ["headset", "naushnik", "headphone", "earphone",
                "realtek", "usb audio", "microphone array"]
    mics = sr.Microphone.list_microphone_names()
    for i, name in enumerate(mics):
        name_low = name.lower()
        if any(k in name_low for k in keywords):
            print(f"\n🎧 Topildi: [{i}] {name}")
            return i
    return None


def wake_word_test(device_index=None):
    """Jarvis wake word ni maxsus test"""
    if not SR_OK:
        return
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.energy_threshold = 200
    r.pause_threshold  = 0.6
    
    WAKE_WORD = "jarvis"
    # Ko'p tillarni sinab ko'rish
    LANGS = ["uz-UZ", "ru-RU", "en-US"]

    print(f"\n🤖 Wake Word Test — '{WAKE_WORD}' deng (5 marta sinab ko'ring)")
    print("   [Ctrl+C] — to'xtatish\n")
    
    count = 0
    while count < 10:
        count += 1
        print(f"   [{count}/10] 'Jarvis' deng...", end="", flush=True)
        try:
            with sr.Microphone(device_index=device_index) as src:
                r.adjust_for_ambient_noise(src, duration=0.2)
                audio = r.listen(src, timeout=4, phrase_time_limit=3)
            
            found = False
            for lang in LANGS:
                try:
                    text = r.recognize_google(audio, language=lang).lower()
                    print(f" [{lang}] '{text}'", end="")
                    if WAKE_WORD in text:
                        print(f" ✅ JARVIS ANIQLANDI!")
                        found = True
                        break
                except sr.UnknownValueError:
                    pass
                except sr.RequestError:
                    print(" [Internet xatosi]"); break
            
            if not found:
                print(" ❌")
                
        except sr.WaitTimeoutError:
            print(" [vaqt tugadi]")
        except KeyboardInterrupt:
            print("\n   [To'xtatildi]"); break


def main():
    print("\n" + "🔬"*27)
    print("  JARVIS — Mikrofon Diagnostika Vositasi")
    print("🔬"*27)

    # 1. Barcha mikrofonlarni ko'rsatish
    list_microphones()

    # 2. Eng yaxshi naushnik mikrofoni topish
    best_idx = find_best_microphone()

    print("\n" + "─"*55)
    print("  SINOV MENYUSI:")
    print("  [1] Default mikrofon bilan test")
    print("  [2] Mikrofon ID bo'yicha test")
    print("  [3] Wake word test (jarvis)")
    print("  [4] Barchasi avtomatik")
    print("─"*55)
    
    try:
        choice = input("\n  Tanlov [1-4]: ").strip()
    except KeyboardInterrupt:
        return
    
    if choice == "1":
        test_microphone(device_index=None)
    elif choice == "2":
        try:
            idx = int(input("  Mikrofon ID: ").strip())
            test_microphone(device_index=idx)
        except ValueError:
            print("❌ Noto'g'ri son")
    elif choice == "3":
        idx = best_idx
        if idx is None:
            try:
                idx_str = input(f"  Mikrofon ID (bo'sh = default): ").strip()
                idx = int(idx_str) if idx_str else None
            except ValueError:
                idx = None
        wake_word_test(device_index=idx)
    elif choice == "4":
        test_microphone(device_index=None)
        if best_idx is not None:
            test_microphone(device_index=best_idx)
        wake_word_test(device_index=best_idx)
    
    print("\n" + "="*55)
    print("  💡 NATIJAGA QARAB:")
    print("  • Agar default ishlamasa → MIC_DEVICE_INDEX ni .env ga yozing")
    print("  • Agar [en-US] ishlasa → WAKE_LANG=en-US ni .env ga yozing")
    print("  • Agar hech biri ishlamasa → Internet yoki mikrofon ruxsatini tekshiring")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()