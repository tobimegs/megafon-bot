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
    full_address = State()      # ввод одной строкой
    city = State()
    street = State()
    house = State()
    apartment = State()
    phone = State()


def load_addresses():
    if not ADDRESSES_FILE.exists():
        return []
    with open(ADDRESSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_addresses(addresses):
    with open(ADDRESSES_FILE, "w", encoding="utf-8") as f:
        json.dump(addresses, f, ensure_ascii=False, indent=2)


def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить адрес", callback_data="check_address")],
        [InlineKeyboardButton(text="📊 Посмотреть актуальные тарифы", callback_data="tariffs")],
        [InlineKeyboardButton(text="📺 ТВ", callback_data="tv")]
    ])


def get_address_input_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ввести одной строкой", callback_data="full_address")],
        [InlineKeyboardButton(text="📋 Ввести по шагам", callback_data="step_by_step")]
    ])


def parse_full_address(text: str) -> dict:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    parts = text.split()

    return {
        "city": parts[0] if len(parts) > 0 else "",
        "street": parts[1] if len(parts) > 1 else "",
        "house": parts[2] if len(parts) > 2 else "",
        "raw": text
    }


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Выбери действие:", reply_markup=get_main_menu())


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=get_main_menu())


@dp.message(Command("add_address"))
async def cmd_add_address(message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("Команда только для владельца.")

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /add_address <адрес>")

    new_addr = parts[1].lower().strip()
    addresses = load_addresses()
    if new_addr in addresses:
        return await message.answer("Адрес уже есть.")

    addresses.append(new_addr)
    save_addresses(addresses)
    await message.answer(f"✅ Добавлен: {new_addr}")


@dp.callback_query(F.data == "check_address")
async def choose_address_input(callback: CallbackQuery):
    await callback.message.edit_text(
        "Как хотите ввести адрес?",
        reply_markup=get_address_input_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "full_address")
async def start_full_address(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📍 Введите адрес **одной строкой** (например: Москва Газгольдерная 10)")
    await state.set_state(AddressForm.full_address)
    await callback.answer()


@dp.callback_query(F.data == "step_by_step")
async def start_step_by_step(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🏙️ Введите город:")
    await state.set_state(AddressForm.city)
    await callback.answer()


@dp.message(AddressForm.full_address)
async def process_full_address(message: Message, state: FSMContext):
    parsed = parse_full_address(message.text)
    await state.update_data(
        city=parsed["city"],
        street=parsed["street"],
        house=parsed["house"],
        raw_address=parsed["raw"]
    )
    await state.set_state(AddressForm.phone)
    await message.answer("📱 Введите ваш номер телефона:")


# ==================== Пошаговый ввод ====================
@dp.message(AddressForm.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.lower().strip())
    await state.set_state(AddressForm.street)
    await message.answer("🛣️ Введите улицу:")


@dp.message(AddressForm.street)
async def process_street(message: Message, state: FSMContext):
    await state.update_data(street=message.text.lower().strip())
    await state.set_state(AddressForm.house)
    await message.answer("🏠 Введите номер дома:")


@dp.message(AddressForm.house)
async def process_house(message: Message, state: FSMContext):
    await state.update_data(house=message.text.lower().strip())
    await state.set_state(AddressForm.apartment)
    await message.answer("🚪 Введите номер квартиры (или «нет»):")


@dp.message(AddressForm.apartment)
async def process_apartment(message: Message, state: FSMContext):
    await state.update_data(apartment=message.text.lower().strip())
    await state.set_state(AddressForm.phone)
    await message.answer("📱 Введите ваш номер телефона:")


# ==================== Финальная обработка ====================
@dp.message(AddressForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    data = await state.get_data()
    await state.clear()

    phone = data['phone']
    raw = data.get("raw_address", f"{data.get('city','')} {data.get('street','')} {data.get('house','')}")
    addresses = load_addresses()

    is_connected = any(
        addr.replace(",", " ").replace(".", " ") in raw.replace(",", " ").replace(".", " ")
        for addr in addresses
    )

    if is_connected:
        text = f"✅ **Дом подключён!**\n📍 {raw}\n📱 {phone}\n\nМенеджер: `89998719968`"
        await bot.send_message(OWNER_ID, f"🆕 Лид (подключён)\n{raw}\n{phone}")
    else:
        text = f"📍 Адрес принят: {raw}\n📱 {phone}\n\nПроверяем подключение..."
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
