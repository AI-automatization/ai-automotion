"""
jarvis.py dan Spotify kodlarini o'chiradi.
Ishlatish: python remove_spotify.py
"""
import re, shutil, os

TARGET = "jarvis.py"
BACKUP = "jarvis.py.bak"

# Avval zaxira nusxa
shutil.copy2(TARGET, BACKUP)
print(f"✅ Zaxira saqlandi: {BACKUP}")

with open(TARGET, "r", encoding="utf-8") as f:
    lines = f.readlines()

cleaned = []
skip_block = False

for i, line in enumerate(lines):
    # 1) Import qatorlari (117-118)
    if re.search(r'(init_spotify|spotify_search_play|spotify_pause|spotify_resume'
                 r'|spotify_next|spotify_prev|spotify_current|spotify_volume)', line):
        print(f"  🗑  Import o'chirildi [{i+1}]: {line.rstrip()}")
        continue

    # 2) SPOTIFY_WORDS bloki boshlanishi
    if 'SPOTIFY_WORDS' in line:
        skip_block = True
        print(f"  🗑  Spotify bloki boshlanishi [{i+1}]")

    # 3) Blok tugashi — keyingi if/elif/else/return/break qatori
    if skip_block:
        # Blok: SPOTIFY_WORDS dan boshlanib, keyingi asosiy buyruq blokigacha
        # Blok ichidagi barcha qatorlarni o'tkazib yuboramiz
        # Blok "return True" bilan tugaydi
        if 'return True' in line and skip_block:
            print(f"  🗑  Spotify bloki tugadi [{i+1}]")
            skip_block = False
            continue
        else:
            continue

    # 4) init_spotify chaqiruvi
    if 'init_spotify' in line:
        print(f"  🗑  init_spotify o'chirildi [{i+1}]: {line.rstrip()}")
        continue

    # 5) SPOTIFY config import (config.py dan)
    if re.search(r'SPOTIFY_CLIENT_ID|SPOTIFY_CLIENT_SECRET|SPOTIFY_REDIRECT', line):
        print(f"  🗑  Spotify config o'chirildi [{i+1}]: {line.rstrip()}")
        continue

    cleaned.append(line)

with open(TARGET, "w", encoding="utf-8") as f:
    f.writelines(cleaned)

print(f"\n✅ Tayyor! {len(lines) - len(cleaned)} qator o'chirildi.")
print(f"   Asl fayl: {BACKUP}")
print(f"   Yangi fayl: {TARGET}")

# Tekshirish
remaining = [l for l in cleaned if 'spotify' in l.lower()]
if remaining:
    print(f"\n⚠️  Hali qolgan spotify qatorlar:")
    for l in remaining:
        print(f"   {l.rstrip()}")
else:
    print("\n✅ Spotify to'liq o'chirildi!")