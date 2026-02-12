# 🤖 JARVIS v3 — O'zbek Ovozli Yordamchi (Full Edition)

Windows uchun Python da yozilgan AI-powered ovozli yordamchi.

---

## ⚡ Tez Boshlash

### 1. O'rnatish
```batch
setup.bat
```

### 2. API Kalitlar — `.env` faylga yozing
```env
CLAUDE_API_KEY=sk-ant-...
WEATHER_API_KEY=abc123...
CITY_NAME=Tashkent
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
```

### 3. Ishga tushirish
```bash
python jarvis.py            # Ovozli + animatsiya
python jarvis.py --keyboard # Test rejimi
```

---

## 🎙️ Buyruqlar — To'liq Ro'yxat

### 🕐 Vaqt va Ob-havo
| Buyruq | Natija |
|--------|--------|
| `Soat nechchi?` | Vaqtni aytadi |
| `Bugun qanday kun?` | Sanani aytadi |
| `Ob-havo qanday?` | Toshkent ob-havosi |
| `Samarkandda ob-havo` | Berilgan shahar ob-havosi |

### 💻 Tizim
| Buyruq | Natija |
|--------|--------|
| `CPU qancha?` | CPU/RAM/disk/batareya holati |
| `Batareya necha foiz?` | Batareya holati |
| `Internet tezligi?` | Ping tekshirish |
| `Qaysi dasturlar ko'p xotira ishlatayapti?` | Top jarayonlar |
| `Chrome ni to'xtat` | Chrome jarayonini o'ldirish |
| `Screenshot ol` | Ekran suratini saqlash |

### 🔊 Ovoz
| Buyruq | Natija |
|--------|--------|
| `Ovozni oshir` | +15% ovoz |
| `Ovozni 50 ga qo'y` | 50% ovoz |
| `Ovozni o'chir` | Mute |

### 🖥️ Oyna Boshqaruvi
| Buyruq | Natija |
|--------|--------|
| `Chrome ni minimlashtir` | Oynani kichraytirish |
| `VS Code ni to'liq ekran` | Maksimallashtiirish |
| `Barcha oynalarni minimlashtir` | Win+D |

### 📁 Fayllar
| Buyruq | Natija |
|--------|--------|
| `Yuklamalar papkasini och` | Downloads ochiladi |
| `Rasmlar papkasini och` | Pictures ochiladi |
| `Oxirgi yuklab olingan fayl` | Oxirgi fayl nomi |

### 📌 Vazifalar (To-Do)
| Buyruq | Natija |
|--------|--------|
| `Vazifa qo'sh: API yozing` | Yangi vazifa |
| `Vazifalarni ko'rsat` | Ro'yxat |
| `1-vazifa bajarildi` | Belgilash |

### 📖 Kundalik (Journal)
| Buyruq | Natija |
|--------|--------|
| `Kundalikka yoz: bugun yaxshi kod yozdim` | Yozuv qo'shish |
| `Bugungi kundalikni o'qi` | Ko'rsatish |

### 🧠 Xotira
| Buyruq | Natija |
|--------|--------|
| `Mening ismim Ali, eslab qol` | Ismni saqlash |
| `Nimani eslab qolding?` | Ko'rsatish |

### ⏰ Eslatmalar
| Buyruq | Natija |
|--------|--------|
| `30 daqiqadan keyin choy iching, eslatib qo'y` | Taymer |
| `Soat 15 da yig'ilish bor, eslatib qo'y` | Absolyut vaqt |
| `Eslatmalarni ko'rsat` | Faol eslatmalar |

### 💱 Valyuta
| Buyruq | Natija |
|--------|--------|
| `Dollar kursi qancha?` | USD → UZS |
| `1000 so'm necha dollar?` | UZS → USD |
| `Evrodan dollarga kurs` | EUR → USD |

### 📰 Yangiliklar
| Buyruq | Natija |
|--------|--------|
| `Bugungi yangiliklar` | Top yangiliklar |
| `Texnologiya yangiliklari` | Mavzuga oid |

### 🌐 Tarjima
| Buyruq | Natija |
|--------|--------|
| `Hello ni o'zbekchaga tarjima qil` | Tarjima |
| `Bu matnni ruscha tarjima qil` | Tarjima |

### 🎵 Spotify
| Buyruq | Natija |
|--------|--------|
| `Spotify da Shaxriyor qo'y` | Qidirib ijro etish |
| `Spotify keyingi qo'shiq` | Next track |
| `Spotify pauza` | Pauza |
| `Hozir nima ijro etilmoqda?` | Joriy qo'shiq |

### 📱 Telegram
| Buyruq | Natija |
|--------|--------|
| `Bekzodga yoz` | Chat ochiladi |
| `Telegramda onaga yoz` | Chat ochiladi |

### ⚙️ Boshqaruv
| Buyruq | Natija |
|--------|--------|
| `Sozlamalar` | Sozlamalar oynasi |
| `Tarixi` | Buyruqlar tarixi |
| `Kompyuterni o'chir` | 30 soniyada shutdown |
| `Qayta yoq` | Restart |
| `Ekranni qulfla` | Lock screen |
| `Xayr` | Jarvis yopiladi |

---

## 📁 Fayl Tuzilmasi

```
jarvis/
├── jarvis.py          # Asosiy dastur
├── config.py          # Sozlamalar
├── .env               # 🔒 API kalitlar (yarating!)
├── .env.example       # Namuna
├── contacts.json      # Telegram kontaktlar
├── requirements.txt   # Kutubxonalar
├── setup.bat          # O'rnatuvchi
├── modules/
│   ├── logger.py      # Loglash
│   ├── memory_manager.py  # Xotira, kundalik, vazifalar
│   ├── reminders.py   # Eslatmalar
│   ├── media_control.py   # Spotify, oyna, clipboard
│   ├── web_services.py    # Valyuta, tarjima, yangiliklar
│   └── file_manager.py    # Fayl va jarayonlar
├── data/
│   ├── memory.json    # Xotira (avtomatik yaratiladi)
│   ├── tasks.json     # Vazifalar
│   └── journal.json   # Kundalik
└── logs/
    └── jarvis_YYYY-MM-DD.log  # Kundalik log
```

---

## 🔧 Muammolar

**Spotify ishlamayapti?**
1. `developer.spotify.com` → Create App
2. Redirect URI ga `http://localhost:8888/callback` qo'shing
3. `.env` ga client_id va client_secret yozing
4. Birinchi ishga tushirishda brauzer ochiladi → login qiling

**PyAudio o'rnatilmayapti?**
```bash
pip install pipwin
pipwin install pyaudio
```

**Tarjima ishlamayapti?**
```bash
pip install deep-translator
```

---

## 📝 Litsenziya
MIT — Erkin foydalaning.
