import asyncio
import json
import logging
import os
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


def load_addresses():
    if not ADDRESSES_FILE.exists():
        return []
    with open(ADDRESSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_addresses(addresses):
    with open(ADDRESSES_FILE, "w", encoding="utf-8") as f:
        json.dump(addresses, f, ensure_ascii=False, indent=2)


def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить адрес", callback_data="check_address")],
        [InlineKeyboardButton(text="📊 Посмотреть актуальные тарифы", callback_data="tariffs")],
        [InlineKeyboardButton(text="📺 ТВ", callback_data="tv")]
    ])
    return keyboard


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для проверки подключения интернета МегаФон.\n\n"
        "Выбери действие:",
        reply_markup=get_main_menu()
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu())


@dp.message(Command("add_address"))
async def cmd_add_address(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Эта команда доступна только владельцу бота.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование:\n`/add_address москва ленина 25`", parse_mode="Markdown")
        return

    new_address = parts[1].lower().strip()
    addresses = load_addresses()

    if new_address in addresses:
        await message.answer("Этот адрес уже есть в списке.")
        return

    addresses.append(new_address)
    save_addresses(addresses)
    await message.answer(f"✅ Адрес успешно добавлен:\n`{new_address}`", parse_mode="Markdown")


@dp.callback_query(F.data == "check_address")
async def start_check_address(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🏙️ В каком городе нужно проверить адрес?")
    await state.set_state(AddressForm.city)
    await callback.answer()


@dp.callback_query(F.data == "tariffs")
async def show_tariffs(callback: CallbackQuery):
    await callback.message.edit_text("📊 Информация о тарифах будет здесь.")
    await callback.answer()


@dp.callback_query(F.data == "tv")
async def show_tv(callback: CallbackQuery):
    await callback.message.edit_text("📺 Информация о ТВ будет здесь.")
    await callback.answer()


# ==================== FSM ====================
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
    await message.answer("🚪 Введите номер квартиры (или напишите «нет»):")


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

    full_address = f"{data['city']} {data['street']} {data['house']}"
    phone = data['phone']
    addresses = load_addresses()

    is_connected = any(addr in full_address for addr in addresses)

    if is_connected:
        text = (
            f"✅ **Дом подключён!**\n\n"
            f"📍 {full_address}\n"
            f"📱 {phone}\n\n"
            f"**Свяжитесь с менеджером:**\n"
            f"📞 `89998719968`"
        )
        await bot.send_message(OWNER_ID, f"🆕 Лид (подключён)\n{full_address}\n{phone}")
    else:
        text = (
            f"📍 Адрес принят: {full_address}\n"
            f"📱 {phone}\n\n"
            "🔍 Проверяем возможность подключения.\n"
            "Менеджер свяжется с вами."
        )
        await bot.send_message(OWNER_ID, f"🆕 Новый лид\n{full_address}\n{phone}")

    await message.answer(text, reply_markup=get_main_menu())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
