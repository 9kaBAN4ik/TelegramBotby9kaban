# admin.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_ID  # Импортируем ADMIN_ID из config
from database import set_user_role  # Обновим импорт с учетом получения роли

router = Router()

@router.message(Command(commands=["add_partner"]))
async def add_partner(message: Message):
    # Проверка на админский ID
    if message.from_user.id != int(ADMIN_ID):  # Преобразуем ADMIN_ID в int
        await message.answer("Только администратор может добавлять партнёров.")
        return

    try:
        user_id = int(message.text.split()[1])  # Разделяем команду и user_id
    except (IndexError, ValueError):
        await message.answer("Пожалуйста, укажите user_id для добавления в партнёры.")
        return

    # Устанавливаем роль пользователя как партнёр
    await set_user_role(user_id, 'partner')

    await message.answer(f"Пользователь с user_id {user_id} теперь партнёр!")
