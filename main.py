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
    city = State()
    street = State()
    house = State()
    apartment = State()
    phone = State()


# ==================== УЛУЧШЕННАЯ РАБОТА С АДРЕСАМИ ====================
def load_addresses():
    if not ADDRESSES_FILE.exists():
        return []
    try:
        with open(ADDRESSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_addresses(addresses):
    with open(ADDRESSES_FILE, "w", encoding="utf-8") as f:
        json.dump(addresses, f, ensure_ascii=False, indent=2)


def normalize(text: str) -> set:
    """Супер нормализация — убирает всё лишнее"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)      # убираем запятые, точки, дефисы и т.д.
    text = re.sub(r'\s+', ' ', text).strip()  # убираем лишние пробелы
    return set(text.split())


def is_address_connected(user_input: str) -> bool:
    """Проверяет совпадение адреса"""
    addresses = load_addresses()
    user_words = normalize(user_input)

    for addr in addresses:
        addr_words = normalize(addr)
        if addr_words.issubset(user_words) or user_words.issubset(addr_words):
            return True
    return False


# ==================== МЕНЮ ====================
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить адрес", callback_data="check_address")],
        [InlineKeyboardButton(text="📊 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton(text="📺 ТВ", callback_data="tv")]
    ])


# ==================== КОМАНДЫ ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Выбери действие:", reply_markup=get_main_menu())


@dp.message(Command("add_address"))
async def cmd_add_address(message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("❌ Команда только для владельца.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование:\n/add_address москва газгольдерная 10")
    
    addr = parts[1].strip()
    addresses = load_addresses()
    
    if normalize(addr) in [normalize(a) for a in addresses]:
        return await message.answer("❌ Этот адрес уже есть.")
    
    addresses.append(addr)
    save_addresses(addresses)
    await message.answer(f"✅ Адрес добавлен:\n{addr}")


# ==================== FSM ====================
@dp.callback_query(F.data == "check_address")
async def start_check(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🏙️ Введите город:")
    await state.set_state(AddressForm.city)
    await callback.answer()


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


@dp.message(AddressForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    data = await state.get_data()
    await state.clear()

    city = data['city']
    street = data['street']
    house = data['house']
    apartment = data['apartment']
    phone = data['phone']

    full_address = f"{city} {street} {house}"

    if is_address_connected(full_address):
        text = (
            f"✅ **ДОМ ПОДКЛЮЧЁН!**\n\n"
            f"📍 {city}, {street}, д.{house}, кв.{apartment}\n"
            f"📱 {phone}\n\n"
            f"**Менеджер:** `89998719968`"
        )
        await bot.send_message(OWNER_ID, f"🆕 ЛИД (ПОДКЛЮЧЁН)\n{city}, {street}, д.{house}\n{phone}")
    else:
        text = (
            f"📍 Адрес принят:\n{city}, {street}, д.{house}, кв.{apartment}\n"
            f"📱 {phone}\n\n"
            "🔍 Проверяем возможность подключения.\n"
            "Менеджер свяжется с вами."
        )
        await bot.send_message(OWNER_ID, f"🆕 Новый лид\n{city}, {street}, д.{house}\n{phone}")

    await message.answer(text, reply_markup=get_main_menu())


@dp.callback_query(F.data.in_(["tariffs", "tv"]))
async def placeholder(callback: CallbackQuery):
    await callback.message.edit_text("Информация будет добавлена позже.")
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
