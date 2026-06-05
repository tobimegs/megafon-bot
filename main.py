import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

class AddressForm(StatesGroup):
    city = State()
    street = State()
    house = State()
    apartment = State()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для проверки подключения интернета МегаФон.\n\n"
        "Напиши /check чтобы начать проверку адреса."
    )

@dp.message(Command("check"))
async def cmd_check(message: Message, state: FSMContext):
    await state.set_state(AddressForm.city)
    await message.answer("🏙️ В каком городе нужно проверить адрес?")

@dp.message(AddressForm.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(AddressForm.street)
    await message.answer("🛣️ Введите улицу:")

@dp.message(AddressForm.street)
async def process_street(message: Message, state: FSMContext):
    await state.update_data(street=message.text)
    await state.set_state(AddressForm.house)
    await message.answer("🏠 Введите номер дома:")

@dp.message(AddressForm.house)
async def process_house(message: Message, state: FSMContext):
    await state.update_data(house=message.text)
    await state.set_state(AddressForm.apartment)
    await message.answer("🚪 Введите номер квартиры (или напишите 'нет', если не нужно):")

@dp.message(AddressForm.apartment)
async def process_apartment(message: Message, state: FSMContext):
    await state.update_data(apartment=message.text)
    data = await state.get_data()
    await state.clear()

    address = f"{data['city']}, {data['street']}, д. {data['house']}, кв. {data['apartment']}"
    await message.answer(f"✅ Адрес принят:\n{address}\n\n🔍 Сейчас проверяем... (пока заглушка)")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
