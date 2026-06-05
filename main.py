import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для проверки возможности подключения интернета МегаФон.\n\n"
        "Напиши /check чтобы начать проверку адреса."
    )

@dp.message(Command("check"))
async def cmd_check(message: Message):
    await message.answer("🔍 Функция проверки адреса пока в разработке.\nСкоро запустим.")

@dp.message()
async def echo(message: Message):
    await message.answer(f"Ты написал: {message.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
