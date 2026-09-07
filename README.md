# IxlosJarimabot

O'qituvchi va xodimlarning jarimalarini kiritish hamda kunlik / haftalik /
oylik / yillik hisobotlarni Excel formatida yuklab olish uchun Telegram bot +
Telegram MiniApp.

## 📦 Tarkibi

```
ixlosjarimabot/
├── bot/
│   ├── bot.py          # Asosiy Telegram bot (aiogram3)
│   ├── database.py     # SQLite bilan ishlash
│   └── reports.py      # Excel hisobotlarni generatsiya qilish
├── webapp/
│   ├── server.py        # FastAPI — MiniApp uchun API va statik fayllar
│   ├── telegram_auth.py # Telegram initData ni tekshirish (xavfsizlik)
│   └── static/
│       ├── app.html      # Oddiy foydalanuvchi MiniApp (jarima kiritish)
│       └── admin.html    # Admin panel MiniApp
├── exports/              # Generatsiya qilingan Excel fayllar shu yerga tushadi
├── run_all.py            # Bot + serverni birgalikda ishga tushirish
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ 1-qadam: O'rnatish

```bash
cd ixlosjarimabot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 🔑 2-qadam: Sozlash (.env)

`.env.example` faylidan nusxa oling:

```bash
cp .env.example .env
```

`.env` faylini oching va quyidagilarni to'ldiring:

| O'zgaruvchi | Tavsif |
|---|---|
| `BOT_TOKEN` | @BotFather dan olingan bot tokeni |
| `WEBAPP_URL` | MiniApp joylashgan domen (https bo'lishi shart, masalan `https://jarima.ixlos.uz`) |
| `SUPER_ADMIN_IDS` | Bosh administrator(lar) chat_id'lari, vergul bilan (masalan `111111,222222`) |
| `PORT` | FastAPI server porti (standart: 8000) |

> 💡 O'zingizning chat_id raqamingizni bilish uchun: botni ishga tushirgach
> unga `/id` buyrug'ini yuboring.

## 🚀 3-qadam: BotFather'da sozlash

1. [@BotFather](https://t.me/BotFather) ga o'ting, `/newbot` orqali bot yarating (nomi: `IxlosJarimabot` yoki xohlagan nom).
2. `/mybots` → botingizni tanlang → **Bot Settings → Menu Button** → **Configure Menu Button**
   → URL sifatida `https://SIZNING_DOMENINGIZ/app` kiriting (bu tugma har doim ochilib turadi).
3. MiniApp ishlashi uchun **HTTPS domen** shart (localhost'da Telegram ichida ochilmaydi,
   lekin brauzerda test qilish uchun pastdagi "Lokal test" bo'limiga qarang).

## ▶️ 4-qadam: Ishga tushirish

Eng oson yo'l — botni va serverni birga ishga tushirish:

```bash
python run_all.py
```

Yoki alohida-alohida (masalan, ikkita alohida serverga joylashtirmoqchi bo'lsangiz):

```bash
# 1-terminal — Telegram bot
python -m bot.bot

# 2-terminal — MiniApp API server
uvicorn webapp.server:app --host 0.0.0.0 --port 8000
```

Serverni internetga chiqarish uchun (masalan VPS'da) nginx + SSL sertifikat
(Let's Encrypt / Certbot) yoki Cloudflare Tunnel ishlatishingiz mumkin.
`WEBAPP_URL` shu domenga mos bo'lishi kerak.

### 🧪 Lokal brauzerda tekshirish (Telegram'siz)

`.env` fayliga `DEV_MODE=1` qo'shsangiz, `X-Init-Data` tekshiruvi o'chiriladi va
`SUPER_ADMIN_IDS` dagi birinchi ID admin sifatida ishlatiladi — shu orqali
`http://localhost:8000/app` va `http://localhost:8000/admin` sahifalarini
oddiy brauzerda ochib ko'rishingiz mumkin. **Ishga tushirishdan oldin buni
o'chirib qo'yishni unutmang!**

## 🧑‍🏫 Botdan foydalanish

### Oddiy foydalanuvchi (jarima kirituvchi xodim)
1. Botga `/start` yuboradi → chiroyli xush kelibsiz xabari chiqadi.
2. **«📲 Ilovani ochish»** tugmasini bosadi → MiniApp ochiladi.
3. Ro'yxatdan kerakli o'qituvchini qidiradi/tanlaydi.
4. Jarima turini tanlaydi (summasi avtomatik to'ldiriladi, xohlasa o'zgartirishi mumkin).
5. Kerak bo'lsa izoh yozadi va tasdiqlaydi — jarima bazaga saqlanadi.

### Administrator
- `/admin` — admin panel (MiniApp) va hisobotlar menyusiga kirish.
- **Admin panel** ichida 4 ta bo'lim:
  - **O'qituvchilar** — qo'shish / tahrirlash / o'chirish (ism-familiya, lavozim, telefon).
  - **Jarima turlari** — qo'shish / tahrirlash / o'chirish, har biriga alohida summa.
  - **Hisobotlar** — Kunlik / Haftalik / Shu oy / Shu yil bo'yicha jamlama ko'rish
    va Excel faylni yuklab olish.
  - **Adminlar** — chat_id orqali yangi admin qo'shish (faqat bosh admin qila oladi).
- `/hisobot` — botning o'zida tugmalar orqali kunlik/haftalik/oylik/yillik va
  o'tgan 12 oy uchun Excel hisobotni to'g'ridan-to'g'ri Telegram'ga yuboradi.
- `/admin_qosh <chat_id>` — yangi admin qo'shish (faqat bosh admin).
- `/admin_ol <chat_id>` — adminlikdan olib tashlash (faqat bosh admin).
- `/admin_royxat` — barcha adminlar ro'yxati.
- `/id` — o'zingizning chat_id raqamingizni ko'rish.

## 📊 Hisobotlar haqida

Har bir Excel hisobotda 2 ta varaq bo'ladi:
1. **Jamlama** — har bir o'qituvchi bo'yicha jarimalar soni va umumiy summa.
2. **Batafsil** — barcha jarimalarning to'liq ro'yxati (sana, xodim, jarima turi, summa, izoh).

O'tgan oylar uchun hisobotni oxirgi 12 oy ichidan istalganini tanlab olish mumkin
(botda `/hisobot` → «⏪ O'tgan oylar» yoki admin paneldagi oy tanlagichi orqali).

## 🔒 Xavfsizlik

MiniApp'dan kelayotgan har bir so'rov Telegram'ning rasmiy `initData` HMAC
tekshiruvidan o'tadi (`webapp/telegram_auth.py`), shuning uchun botdan
tashqarida (masalan to'g'ridan-to'g'ri linkni ochib) hech kim ma'lumotlarga
kira olmaydi. Admin huquqi talab qiladigan barcha amallar (`/api/admin/...`)
qo'shimcha ravishda foydalanuvchi bazadagi `admins` jadvalida borligini tekshiradi.

## 🗄 Ma'lumotlar bazasi

Standart holatda SQLite (`jarimabot.db`) ishlatiladi — alohida server o'rnatish
shart emas, fayl avtomatik yaratiladi. Katta hajmda foydalanish rejalashtirilsa,
`bot/database.py` ni PostgreSQL'ga oson moslashtirish mumkin (SQL so'rovlar
deyarli standart ko'rinishda yozilgan).

## 🛠 Texnologiyalar

- **aiogram 3** — Telegram bot
- **FastAPI** — MiniApp uchun REST API va statik fayllarni berish
- **SQLite** — ma'lumotlar bazasi
- **openpyxl** — Excel hisobotlarni generatsiya qilish
- **Vanilla HTML/CSS/JS** — MiniApp interfeysi (Telegram WebApp SDK bilan, tungi/kunduzgi
  Telegram temasiga avtomatik moslashadi)

## ❓ Muammo yuzaga kelsa

- Bot javob bermasa — `.env` dagi `BOT_TOKEN` to'g'riligini va internetga ulanishni tekshiring.
- MiniApp ochilmasa — `WEBAPP_URL` https bo'lishi va real domenga ishora qilishi kerakligini tekshiring (Telegram http yoki localhost'ni MiniApp sifatida ochmaydi).
- "Faqat administratorlar uchun" xabari chiqsa — `/id` orqali chat_id oling va uni `SUPER_ADMIN_IDS` ga yoki admin panel orqali qo'shing.
