import asyncio
import json
import logging
import os
import re
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
OWNER_ID = int(os.getenv("OWNER_ID"))

ADDRESSES_FILE = Path("connected_addresses.json")

dp = Dispatcher()


class AddressForm(StatesGroup):
    address = State()
    phone = State()


def load_addresses():
    if not ADDRESSES_FILE.exists():
        return []
    with open(ADDRESSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_addresses(addresses):
    with open(ADDRESSES_FILE, "w", encoding="utf-8") as f:
        json.dump(addresses, f, ensure_ascii=False, indent=2)


def normalize(text: str) -> str:
    """Убирает заглавные буквы, запятые, точки и лишние пробелы"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)   # убираем запятые, точки и т.д.
    text = re.sub(r'\s+', ' ', text).strip()  # убираем лишние пробелы
    return text


def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить адрес", callback_data="check_address")],
        [InlineKeyboardButton(text="📊 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton(text="📺 ТВ", callback_data="tv")]
    ])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Выбери действие:", reply_markup=get_main_menu())


@dp.message(Command("add_address"))
async def cmd_add_address(message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("Команда доступна только владельцу.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /add_address москва ленина 25")
    addr = parts[1].strip()
    addresses = load_addresses()
    if normalize(addr) in [normalize(a) for a in addresses]:
        return await message.answer("Этот адрес уже есть в списке.")
    addresses.append(addr)
    save_addresses(addresses)
    await message.answer(f"✅ Адрес добавлен: {addr}")


@dp.callback_query(F.data == "check_address")
async def start_check(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📍 Введите адрес **одной строкой**.\n\n"
        "Пример: `Москва Газгольдерная 10`\n"
        "Или: `Москва, Ленина, д.25`"
    )
    await state.set_state(AddressForm.address)
    await callback.answer()


@dp.message(AddressForm.address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(raw_address=message.text.strip())
    await state.set_state(AddressForm.phone)
    await message.answer("📱 Введите ваш номер телефона:")


@dp.message(AddressForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    data = await state.get_data()
    await state.clear()

    raw = data["raw_address"]
    phone = data["phone"]
    addresses = load_addresses()

    user_normalized = normalize(raw)
    is_connected = False

    for addr in addresses:
        if normalize(addr) in user_normalized or user_normalized in normalize(addr):
            is_connected = True
            break

    if is_connected:
        text = (
            f"✅ **Дом подключён!**\n\n"
            f"📍 {raw}\n"
            f"📱 {phone}\n\n"
            f"**Менеджер:** `89998719968`"
        )
        await bot.send_message(OWNER_ID, f"🆕 Лид (подключён)\n{raw}\n{phone}")
    else:
        text = (
            f"📍 Адрес принят: {raw}\n"
            f"📱 {phone}\n\n"
            "🔍 Проверяем возможность подключения.\n"
            "Менеджер свяжется с вами."
        )
        await bot.send_message(OWNER_ID, f"🆕 Новый лид\n{raw}\n{phone}")

    await message.answer(text, reply_markup=get_main_menu())


@dp.callback_query(F.data.in_(["tariffs", "tv"]))
async def placeholder(callback: CallbackQuery):
    await callback.message.edit_text("Информация будет добавлена позже.")
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
