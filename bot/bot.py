"""
IxlosJarimabot — asosiy Telegram bot fayli (aiogram 3).
- /start — chiroyli xush kelibsiz xabari + MiniApp ochish tugmasi
- Admin buyruqlari: /admin, /hisobot, /admin_qosh, /admin_royxat, /admin_ol
- Chat har doim toza turishi uchun: yangi menyu ko'rsatilganda avvalgi
  bot xabari (va imkon bo'lsa foydalanuvchining buyruq xabari) o'chiriladi.
"""
import os
import asyncio
import logging
from datetime import date
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, FSInputFile, BotCommand,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from . import database as db
from . import reports

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
SUPER_ADMIN_IDS = [int(x) for x in os.getenv("SUPER_ADMIN_IDS", "").split(",") if x.strip().isdigit()]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ixlosjarimabot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# chat_id -> oxirgi bot menyu xabarining message_id'si.
# Har safar yangi menyu ko'rsatilganda avvalgisi o'chiriladi, shu tufayli
# suhbatda faqat bitta faol menyu xabari qoladi va chat "toza" turadi.
_last_menu_msg: dict[int, int] = {}


async def _safe_delete(chat_id: int, message_id):
    """Xabarni o'chirishga urinadi, xato bo'lsa (allaqachon o'chirilgan/48soatdan
    o'tgan/ruxsat yo'q va h.k.) jim e'tibor bermaydi."""
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass
    except Exception:
        pass


async def show_menu(chat_id: int, text: str, kb: InlineKeyboardMarkup = None):
    """Avvalgi menyu xabarini o'chirib, yangisini yuboradi va uni kuzatib boradi.
    Barcha asosiy navigatsiya (start, admin, hisobotlar) shu funksiya orqali
    ko'rsatiladi — shunday qilib chatda eski tugmali xabarlar to'planib qolmaydi."""
    await _safe_delete(chat_id, _last_menu_msg.get(chat_id))
    msg = await bot.send_message(chat_id, text, reply_markup=kb)
    _last_menu_msg[chat_id] = msg.message_id
    return msg


async def clear_command_message(message: Message):
    """Foydalanuvchi yuborgan /buyruqni ham o'chiradi (chat yanada toza bo'lishi uchun)."""
    await _safe_delete(message.chat.id, message.message_id)


# ------------------------------------------------------------- Klaviaturalar
def main_menu_kb(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📲 Ilovani ochish", web_app=WebAppInfo(url=f"{WEBAPP_URL}/app"))],
    ])
    if db.is_admin(chat_id):
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="🛠 Admin panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"))]
        )
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="📊 Hisobotlar", callback_data="reports_menu")]
        )
    return kb


def reports_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Kunlik", callback_data="rep:today"),
            InlineKeyboardButton(text="🗓 Haftalik", callback_data="rep:week"),
        ],
        [
            InlineKeyboardButton(text="📆 Shu oy", callback_data="rep:month"),
            InlineKeyboardButton(text="📈 Shu yil", callback_data="rep:year"),
        ],
        [InlineKeyboardButton(text="⏪ O'tgan oylar (12 oy)", callback_data="rep:pastmonths")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home_menu")],
    ])


WELCOME_TEXT = (
    "🏫 <b>IxlosJarimabot</b>ga xush kelibsiz!\n\n"
    "Ushbu bot orqali o'qituvchi va xodimlarga belgilangan "
    "jarimalarni tez va qulay tarzda kiritishingiz mumkin.\n\n"
    "📱 Pastdagi <b>«Ilovani ochish»</b> tugmasini bosing va ro'yxatdan "
    "kerakli o'qituvchini tanlab, jarima turini belgilang.\n\n"
    "ℹ️ Savol va takliflar bo'lsa — administratorga murojaat qiling."
)


# ------------------------------------------------------------- /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    db.upsert_user(message.from_user.id, message.from_user.full_name, message.from_user.username or "")
    await clear_command_message(message)
    await show_menu(message.chat.id, WELCOME_TEXT, main_menu_kb(message.from_user.id))


# ------------------------------------------------------------- /admin
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    await clear_command_message(message)
    if not db.is_admin(message.from_user.id):
        await show_menu(message.chat.id, "⛔ Bu buyruq faqat administratorlar uchun.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Admin panelni ochish", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"))],
        [InlineKeyboardButton(text="📊 Hisobotlar", callback_data="reports_menu")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home_menu")],
    ])
    await show_menu(message.chat.id, "🛠 <b>Admin panel</b>", kb)


# ------------------------------------------------------------- Hisobotlar
@dp.message(Command("hisobot"))
async def cmd_hisobot(message: Message):
    await clear_command_message(message)
    if not db.is_admin(message.from_user.id):
        await show_menu(message.chat.id, "⛔ Bu buyruq faqat administratorlar uchun.")
        return
    await show_menu(message.chat.id, "📊 Qaysi davr uchun hisobot kerak?", reports_main_kb())


@dp.callback_query(F.data == "reports_menu")
async def cb_reports_menu(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    await show_menu(call.message.chat.id, "📊 Qaysi davr uchun hisobot kerak?", reports_main_kb())


@dp.callback_query(F.data == "rep:pastmonths")
async def cb_past_months(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    today = date.today()
    buttons = []
    row = []
    y, m = today.year, today.month
    for i in range(12):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        label = f"{reports.UZ_MONTHS[mm]} {yy}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"rep:mp:{yy}:{mm}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="reports_menu")])
    buttons.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home_menu")])
    await call.answer()
    # Bu yerda xabar turi bir xil (matn) bo'lgani uchun to'g'ridan-to'g'ri
    # tahrirlaymiz — vizual jihatdan silliqroq (flicker bo'lmaydi).
    try:
        await call.message.edit_text("Qaysi oy uchun hisobot kerak?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        _last_menu_msg[call.message.chat.id] = call.message.message_id
    except TelegramBadRequest:
        await show_menu(call.message.chat.id, "Qaysi oy uchun hisobot kerak?", InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(F.data == "home_menu")
async def cb_home_menu(call: CallbackQuery):
    await call.answer()
    await show_menu(call.message.chat.id, "🏠 <b>Bosh menyu</b>", main_menu_kb(call.from_user.id))


async def _send_report(chat_id: int, period: str, year=None, month=None):
    fpath, label, total, count = reports.build_excel_report(period, year=year, month=month)
    caption = (
        f"📊 <b>{label}</b>\n\n"
        f"Jarimalar soni: <b>{count}</b>\n"
        f"Umumiy summa: <b>{total:,}</b> so'm".replace(",", " ")
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Yana hisobot", callback_data="reports_menu")],
        [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home_menu")],
    ])
    # Hisobot fayli hujjat sifatida yuborilgani uchun mavjud xabarni "tahrirlash"
    # imkonsiz — shuning uchun avvalgi menyuni o'chirib, hujjatni yangi xabar
    # sifatida yuboramiz va uni keyingi navigatsiya uchun kuzatib boramiz.
    await _safe_delete(chat_id, _last_menu_msg.get(chat_id))
    msg = await bot.send_document(chat_id, FSInputFile(fpath), caption=caption, reply_markup=kb)
    _last_menu_msg[chat_id] = msg.message_id


@dp.callback_query(F.data.startswith("rep:"))
async def cb_report(call: CallbackQuery):
    if not db.is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    parts = call.data.split(":")
    period = parts[1]
    await call.answer("Hisobot tayyorlanmoqda...")
    try:
        if period == "mp":
            yy, mm = int(parts[2]), int(parts[3])
            await _send_report(call.message.chat.id, "month_pick", year=yy, month=mm)
        elif period in ("today", "week", "month", "year"):
            await _send_report(call.message.chat.id, period)
    except Exception as e:
        logger.exception("Hisobot xatosi")
        await show_menu(call.message.chat.id, f"❌ Hisobot yaratishda xatolik: {e}", reports_main_kb())


# ------------------------------------------------------------- Admin qo'shish/olish (chat_id orqali)
@dp.message(Command("admin_qosh"))
async def cmd_admin_qosh(message: Message):
    await clear_command_message(message)
    if not db.is_super_admin(message.from_user.id):
        await show_menu(message.chat.id, "⛔ Faqat bosh administrator yangi admin qo'sha oladi.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().lstrip("-").isdigit():
        await show_menu(message.chat.id, "Foydalanish: <code>/admin_qosh 123456789</code>\n(chat_id raqamini yuboring)")
        return
    chat_id = int(args[1].strip())
    db.add_admin(chat_id)
    await show_menu(message.chat.id, f"✅ {chat_id} endi administrator sifatida qo'shildi.", main_menu_kb(message.from_user.id))
    try:
        await bot.send_message(chat_id, "🎉 Sizga IxlosJarimabot administratori huquqi berildi. /admin buyrug'ini yuboring.")
    except Exception:
        pass


@dp.message(Command("admin_ol"))
async def cmd_admin_ol(message: Message):
    await clear_command_message(message)
    if not db.is_super_admin(message.from_user.id):
        await show_menu(message.chat.id, "⛔ Faqat bosh administrator admin huquqini olib tashlay oladi.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip().lstrip("-").isdigit():
        await show_menu(message.chat.id, "Foydalanish: <code>/admin_ol 123456789</code>")
        return
    chat_id = int(args[1].strip())
    db.remove_admin(chat_id)
    await show_menu(message.chat.id, f"✅ {chat_id} administratorlikdan olib tashlandi.", main_menu_kb(message.from_user.id))


@dp.message(Command("admin_royxat"))
async def cmd_admin_royxat(message: Message):
    await clear_command_message(message)
    if not db.is_admin(message.from_user.id):
        await show_menu(message.chat.id, "⛔ Bu buyruq faqat administratorlar uchun.")
        return
    admins = db.list_admins()
    lines = ["👥 <b>Administratorlar ro'yxati:</b>\n"]
    for a in admins:
        badge = "⭐ Bosh admin" if a["is_super"] else "🛡 Admin"
        lines.append(f"• <code>{a['chat_id']}</code> — {badge}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home_menu")]])
    await show_menu(message.chat.id, "\n".join(lines), kb)


@dp.message(Command("id"))
async def cmd_id(message: Message):
    await clear_command_message(message)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home_menu")]])
    await show_menu(message.chat.id, f"Sizning chat_id: <code>{message.from_user.id}</code>", kb)


# ------------------------------------------------------------- ishga tushirish
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="admin", description="Admin panel"),
        BotCommand(command="hisobot", description="Hisobotlarni yuklab olish"),
        BotCommand(command="admin_qosh", description="Yangi admin qo'shish (chat_id)"),
        BotCommand(command="admin_ol", description="Admin huquqini olib tashlash"),
        BotCommand(command="admin_royxat", description="Adminlar ro'yxati"),
        BotCommand(command="id", description="Mening chat_id raqamim"),
    ])


async def main():
    db.init_db(super_admin_ids=SUPER_ADMIN_IDS)
    await set_commands()
    logger.info("IxlosJarimabot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
