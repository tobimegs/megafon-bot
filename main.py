import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


class AddressForm(StatesGroup):
    city = State()
    street = State()
    house = State()
    apartment = State()


# ==================== КНОПКИ ====================
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверить адрес", callback_data="check_address")],
        [InlineKeyboardButton(text="📊 Посмотреть актуальные тарифы", callback_data="tariffs")]
    ])
    return keyboard


# ==================== /start ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для проверки подключения интернета МегаФон.\n\n"
        "Выбери действие:",
        reply_markup=get_main_menu()
    )


# ==================== /cancel ====================
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "❌ Действие отменено.\n\n"
        "Выбери действие:",
        reply_markup=get_main_menu()
    )


# ==================== КНОПКА "ПРОВЕРИТЬ АДРЕС" ====================
@dp.callback_query(F.data == "check_address")
async def start_check_address(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🏙️ В каком городе нужно проверить адрес?")
    await state.set_state(AddressForm.city)
    await callback.answer()


# ==================== КНОПКА "ТАРИФЫ" ====================
@dp.callback_query(F.data == "tariffs")
async def show_tariffs(callback: CallbackQuery):
    text = """📊 **Актуальные тарифы МегаФон #ДляДома** (Москва)

**🔥 #ДляДома Турбо**  
⚡️ **500 Мбит/с**  
💰 **310 ₽**/мес (с 5-го месяца — **620 ₽**)

**🔥 #ДляДома Максимум**  
⚡️ **500 Мбит/с**  
🖥 **250 Смарт ТВ-каналов**  
💰 **385 ₽**/мес (с 5-го месяца — **770 ₽**)

**🔥 Тариф «Максимум»**  
⚡️ **500 Мбит/с**  
📶 **1 SIM** (1000 мин) + безлимит  
💰 **700 ₽** (30% навсегда)

**👑 «VIP»**  
⚡️ **500 Мбит/с** + 250 ТВ + 3 SIM  
💰 **910 ₽**

**⭐ Для абонентов «Персональный»**  
⚡️ **500 Мбит/с** + 250 ТВ  
💰 **50 ₽** (с 4-го месяца — **310 ₽**)"""

    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


# ==================== FSM: СБОР АДРЕСА ====================
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
    await message.answer("🚪 Введите номер квартиры (или напишите «нет»):")


@dp.message(AddressForm.apartment)
async def process_apartment(message: Message, state: FSMContext):
    await state.update_data(apartment=message.text)
    data = await state.get_data()
    await state.clear()

    address = f"{data['city']}, {data['street']}, д.{data['house']}, кв.{data['apartment']}"

    await message.answer(
        f"✅ **Адрес принят:**\n{address}\n\n"
        "🔍 Сейчас проверяем возможность подключения...\n"
        "(пока заглушка — скоро добавим реальную проверку и отправку лидов)"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
