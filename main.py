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
    search_query = State()
    manual_address = State()
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
        [InlineKeyboardButton(text="🔎 Найти адрес", callback_data="find_address")],
        [InlineKeyboardButton(text="📊 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton(text="📺 ТВ", callback_data="tv")]
    ])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Привет! Выбери действие:", reply_markup=get_main_menu())


@dp.message(Command("add_address"))
async def cmd_add_address(message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("Только для владельца.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /add_address <адрес>")
    addr = parts[1].lower().strip()
    addresses = load_addresses()
    if addr in addresses:
        return await message.answer("Уже есть.")
    addresses.append(addr)
    save_addresses(addresses)
    await message.answer(f"✅ Добавлен: {addr}")


@dp.callback_query(F.data == "find_address")
async def start_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔎 Введите часть адреса (минимум 2 буквы):\n"
        "Например: `газгольдерная` или `ленина`"
    )
    await state.set_state(AddressForm.search_query)
    await callback.answer()


@dp.message(AddressForm.search_query)
async def search_address(message: Message, state: FSMContext):
    query = message.text.lower().strip()
    if len(query) < 2:
        return await message.answer("Введите минимум 2 буквы.")

    addresses = load_addresses()
    matches = [addr for addr in addresses if query in addr]

    if not matches:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Моего адреса нет", callback_data="manual_input")]
        ])
        await message.answer("Ничего не найдено.", reply_markup=keyboard)
        return

    buttons = [[InlineKeyboardButton(text=addr, callback_data=f"select_{addr}")] for addr in matches[:10]]
    buttons.append([InlineKeyboardButton(text="➕ Моего адреса нет", callback_data="manual_input")])

    await message.answer("Выберите адрес:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(F.data.startswith("select_"))
async def address_selected(callback: CallbackQuery, state: FSMContext):
    address = callback.data.replace("select_", "")
    await state.update_data(selected_address=address)
    await state.set_state(AddressForm.phone)
    await callback.message.edit_text(f"✅ Вы выбрали: {address}\n\n📱 Введите ваш номер телефона:")
    await callback.answer()


@dp.callback_query(F.data == "manual_input")
async def manual_input(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📍 Введите ваш адрес полностью:")
    await state.set_state(AddressForm.manual_address)
    await callback.answer()


@dp.message(AddressForm.manual_address)
async def process_manual_address(message: Message, state: FSMContext):
    await state.update_data(manual_address=message.text.strip())
    await state.set_state(AddressForm.phone)
    await message.answer("📱 Введите ваш номер телефона:")


@dp.message(AddressForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    data = await state.get_data()
    await state.clear()

    phone = data['phone']
    address = data.get("selected_address") or data.get("manual_address", "Не указан")

    text = f"✅ Заявка принята!\n📍 {address}\n📱 {phone}\n\nМенеджер свяжется с вами."
    await message.answer(text, reply_markup=get_main_menu())

    # Отправляем лид владельцу
    await bot.send_message(
        OWNER_ID,
        f"🆕 **Новый лид**\n\n📍 {address}\n📱 {phone}"
    )


@dp.callback_query(F.data.in_(["tariffs", "tv"]))
async def placeholder(callback: CallbackQuery):
    await callback.message.edit_text("Информация будет позже.")
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
