from aiogram import Router
import asyncio
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from database import get_user_referral_link  # Функция для получения реферальной ссылки
from database import get_referral_count, get_user_earnings  # Функции для подсчёта рефералов и заработка
from config import CURRENCY  # Обозначение валюты
from messages import *  # Импортируем сообщения

referral_router = Router()

# Кнопка "Для друзей"
@referral_router.message(lambda message: message.text == "Для друзей")
async def friends_menu(message: Message):
    buttons = [
        [KeyboardButton(text="Реферальная ссылка")],
        [KeyboardButton(text="Инфо о реф. сети")],
        [KeyboardButton(text="Назад в главное меню")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Выберите действие:", reply_markup=keyboard)

@referral_router.message(lambda message: message.text == "Реферальная ссылка")
async def handle_referral_link_button(message: Message):
    user_id = message.from_user.id
    user_language = message.from_user.language_code  # Получаем язык пользователя

    # Предполагается, что эта функция возвращает ссылку
    referral_link = await get_user_referral_link(user_id)

    if referral_link:
        if user_language == 'en':
            await message.answer(referral_link_message_en.format(referral_link=referral_link))
        else:
            await message.answer(referral_link_message_ru.format(referral_link=referral_link))
    else:
        if user_language == 'en':
            await message.answer(referral_link_error_en)
        else:
            await message.answer(referral_link_error_ru)

@referral_router.message(lambda message: message.text == "Инфо о реф. сети")
async def referral_network_info(message: Message):
    user_id = message.from_user.id

    # Получаем количество приглашённых пользователей
    referral_count = await get_referral_count(user_id)

    # Используем run_in_executor для вызова синхронной функции
    loop = asyncio.get_event_loop()
    earnings = await loop.run_in_executor(None, get_user_earnings, user_id)

    # Формируем текст сообщения
    info_text = (
        "🤝 Ваша реферальная сеть позволяет вам получать бонусы за приглашённых пользователей!\n\n"
        "📌 Как это работает:\n"
        "1️⃣ Поделитесь своей реферальной ссылкой с друзьями.\n"
        "2️⃣ Когда ваш друг регистрируется, вы получаете бонус на ваш баланс.\n"
        "3️⃣ Чем больше друзей — тем больше бонусов!\n\n"
        "📊 Текущая статистика:\n"
        f"👥 Приглашено пользователей: {referral_count}\n"
        f"💰 Заработано бонусов: {earnings} {CURRENCY}\n\n"
        "Не упустите возможность рассказать друзьям о RaJah.WS и получить больше наград!"
    )

    await message.answer(info_text)

