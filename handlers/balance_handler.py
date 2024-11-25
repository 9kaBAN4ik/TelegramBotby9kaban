from aiogram import Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_user_balance  # Функция для получения баланса
from config import CURRENCY
from messages import balance_message_ru, balance_message_en  # Ваши сообщения

router = Router()

# Обработчик кнопки "Баланс"
@router.message(lambda message: message.text == "Баланс")
async def balance_button_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Получаем язык пользователя из состояния
    user_data = await state.get_data()
    user_language = user_data.get('language', 'ru')  # По умолчанию русский

    # Получаем баланс пользователя
    balance = await get_user_balance(user_id)

    # Формируем сообщение с балансом
    balance_message = ""
    if user_language == 'en':
        balance_message = balance_message_en.format(balance=balance, currency=CURRENCY)
    else:
        balance_message = balance_message_ru.format(balance=balance, currency=CURRENCY)

    balance_buttons = [
        [KeyboardButton(text="Пополнить баланс")],
        [KeyboardButton(text="Вывести средства")],
        [KeyboardButton(text="Перевести средства")],
        [KeyboardButton(text="Вернуться в главное меню")]
    ]
    balance_markup = ReplyKeyboardMarkup(keyboard=balance_buttons, resize_keyboard=True)

    await message.answer(balance_message, reply_markup=balance_markup)

# Обработчик для возврата в главное меню
@router.message(lambda message: message.text == "Вернуться в главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    menu_buttons = [
        [KeyboardButton(text="Продукты")],
        [KeyboardButton(text="Для друзей")],
        [KeyboardButton(text="Баланс")],
        [KeyboardButton(text="Партнеры")],
        [KeyboardButton(text="Инфо")],
    ]
    menu_markup = ReplyKeyboardMarkup(keyboard=menu_buttons, resize_keyboard=True)

    # Отправляем главное меню
    await message.answer("Вы вернулись в главное меню.", reply_markup=menu_markup)


