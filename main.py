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
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
OWNER_ID = int(os.getenv("OWNER_ID"))
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ADDRESSES_FILE = Path("connected_addresses.json")

dp = Dispatcher()


class AddressForm(StatesGroup):
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


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def gpt_parse_address(text: str):
    """GPT извлекает город, улицу и дом"""
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты эксперт по российским адресам. Извлеки только город, улицу и номер дома. Верни JSON с ключами: city, street, house. Если не можешь — верни null."},
                {"role": "user", "content": text}
            ],
            temperature=0,
            max_tokens=150
        )
        content = response.choices[0].message.content
        if content and "null" not in content.lower():
            return json.loads(content)
        return None
    except:
        return None


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
        return await message.answer("Команда только для владельца.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /add_address москва газгольдерная 10")
    addr = parts[1].strip()
    addresses = load_addresses()
    if normalize(addr) in [normalize(a) for a in addresses]:
        return await message.answer("Этот адрес уже есть.")
    addresses.append(addr)
    save_addresses(addresses)
    await message.answer(f"✅ Адрес добавлен: {addr}")


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

    full_address = f"{city}, {street}, д.{house}, кв.{apartment}"

    # Пытаемся понять адрес через GPT
    parsed = await gpt_parse_address(f"{city} {street} {house}")

    addresses = load_addresses()
    is_connected = False

    if parsed:
        gpt_text = f"{parsed.get('city', '')} {parsed.get('street', '')} {parsed.get('house', '')}"
        for addr in addresses:
            if normalize(gpt_text) in normalize(addr) or normalize(addr) in normalize(gpt_text):
                is_connected = True
                break

    if is_connected:
        text = f"✅ **ДОМ ПОДКЛЮЧЁН!**\n\n📍 {full_address}\n📱 {phone}\n\n**Менеджер:** `89998719968`"
        await bot.send_message(OWNER_ID, f"🆕 ЛИД (ПОДКЛЮЧЁН)\n{full_address}\n{phone}")
    else:
        text = f"📍 Адрес принят:\n{full_address}\n📱 {phone}\n\n🔍 Проверяем..."
        await bot.send_message(OWNER_ID, f"🆕 Новый лид\n{full_address}\n{phone}")

    await message.answer(text, reply_markup=get_main_menu())


@dp.callback_query(F.data.in_(["tariffs", "tv"]))
async def placeholder(callback: CallbackQuery):
    await callback.message.edit_text("Информация будет позже.")
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
