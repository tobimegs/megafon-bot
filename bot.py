from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import os
import re

TOKEN = "ТОКЕН_БОТА_ЗДЕСЬ"
ADMIN_ID = 123456789          # ← ВСТАВЬ СВОЙ TELEGRAM ID

GOOD_ADDRESSES_FILE = "good_addresses.json"

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\b(кв|квартира|кв\.|дом|д\.|ул|улица|пр|проспект)\b', '', text)
    return text.strip()

def load_good_addresses():
    if os.path.exists(GOOD_ADDRESSES_FILE):
        with open(GOOD_ADDRESSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_good_addresses(addresses):
    with open(GOOD_ADDRESSES_FILE, "w", encoding="utf-8") as f:
        json.dump(addresses, f, ensure_ascii=False, indent=2)

good_addresses = load_good_addresses()

def is_address_connected(user_address: str) -> bool:
    norm_user = normalize(user_address)
    for good in good_addresses:
        if normalize(good) in norm_user or norm_user in normalize(good):
            return True
    return False

# ================== КОМАНДЫ ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Напиши адрес, я проверю, подключен ли он к МегаФону."
    )

async def add_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только администратор может добавлять адреса.")
        return

    if not context.args:
        await update.message.reply_text("Использование:\n/addaddress Москва, Ленинский проспект, 15")
        return

    new_address = ' '.join(context.args)
    good_addresses.append(new_address)
    save_good_addresses(good_addresses)

    await update.message.reply_text(f"✅ Адрес добавлен!\n{new_address}\n\nВсего адресов в базе: {len(good_addresses)}")

async def list_addresses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not good_addresses:
        await update.message.reply_text("Список адресов пуст. Добавь через /addaddress")
        return

    text = "📋 Список подключённых адресов:\n\n"
    for i, addr in enumerate(good_addresses, 1):
        text += f"{i}. {addr}\n"
    await update.message.reply_text(text)

async def check_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()

    if is_address_connected(address):
        msg = "✅ **Есть подключение!** По этому адресу можно подключать МегаФон."
    else:
        msg = "❌ В моей базе такого адреса нет. Отправь адрес + телефон — проверю вручную."

    await update.message.reply_text(msg, parse_mode="Markdown")

    # Отправляем тебе копию
    lead = f"📍 Пользователь проверил адрес:\n{address}\n\nРезультат: {'Подключен ✅' if is_address_connected(address) else 'Нет в базе ❌'}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=lead)

# ================== ЗАПУСК БОТА ==================

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addaddress", add_address))
app.add_handler(CommandHandler("listaddresses", list_addresses))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_address))

print("Бот запущен. Используй /addaddress чтобы добавлять адреса.")
app.run_polling()
