import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from addresses import add_address, is_address_connected, load_addresses

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
OWNER_ID = int(os.getenv("OWNER_ID"))

dp = Dispatcher()


class AddressForm(StatesGroup):
    city = State()
    street = State()
    house = State()
    apartment = State()
    phone = State()


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

    if add_address(parts[1]):
        await message.answer(f"✅ Адрес добавлен: {parts[1]}")
    else:
        await message.answer("Этот адрес уже есть в списке.")


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
            f"✅ **Дом подключён!**\n\n"
            f"📍 {city}, {street}, д.{house}, кв.{apartment}\n"
            f"📱 {phone}\n\n"
            f"**Менеджер:** `89998719968`"
        )
        await bot.send_message(OWNER_ID, f"🆕 Лид (подключён)\n{city}, {street}, д.{house}\n{phone}")
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
