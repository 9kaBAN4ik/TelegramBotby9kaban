from aiogram import Router, types
from aiogram.dispatcher.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import get_user_courses, get_course_progress  # Функции для работы с БД

router = Router()

# Обработчик кнопки "Личный кабинет"
@router.message(lambda message: message.text.lower() == "личный кабинет")
async def personal_info_menu(message: types.Message):
    """Меню личного кабинета."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton(text="Мои покупки"),
        KeyboardButton(text="Настройки")
    )
    await message.answer(
        MESSAGES["personal_info"]["welcome"],
        reply_markup=keyboard
    )


# Обработчик кнопки "Мои покупки"
@router.message(lambda message: message.text.lower() == "мои покупки")
async def show_purchases(message: types.Message):
    """Отображение списка приобретённых курсов."""
    user_id = message.from_user.id
    courses = get_user_courses(user_id)  # Получаем список курсов из БД

    if not courses:
        await message.answer(MESSAGES["personal_info"]["no_purchases"])
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for course in courses:
        keyboard.add(KeyboardButton(text=course["title"]))

    await message.answer(
        MESSAGES["personal_info"]["purchases_list"],
        reply_markup=keyboard
    )


# Обработчик кнопки курса
@router.message(lambda message: any(
    course["title"].lower() in message.text.lower() for course in get_user_courses(message.from_user.id)))
async def show_course_progress(message: types.Message):
    """Отображение прогресса по выбранному курсу."""
    user_id = message.from_user.id
    course_title = message.text
    course = next(course for course in get_user_courses(user_id) if course["title"] == course_title)
    progress = get_course_progress(user_id, course["id"])  # Получаем прогресс из БД

    if not progress:
        await message.answer(MESSAGES["personal_info"]["no_progress"])
        return

    # Формируем текст с прогрессом
    text = (
        f"📚 {progress['course_title']}\n\n"
        f"Уроков пройдено: {progress['completed_lessons']}/{progress['total_lessons']}\n"
        f"Вопросов пройдено: {progress['completed_questions']}/{progress['total_questions']}"
    )
    await message.answer(text)


# Обработчик кнопки "Настройки"
@router.message(lambda message: message.text.lower() == "настройки")
async def show_settings(message: types.Message):
    """Отображение настроек личного кабинета."""
    # Пример настроек, можно расширить
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton(text="Изменить язык"),
        KeyboardButton(text="Сменить пароль")
    )
    await message.answer(MESSAGES["personal_info"]["settings"], reply_markup=keyboard)


# Пример локализации сообщений
MESSAGES = {
    "main_menu": {
        "welcome": "Добро пожаловать! Выберите действие:",
    },
    "personal_info": {
        "welcome": "Вы в личном кабинете! Выберите действие:",
        "no_purchases": "У вас пока нет приобретённых курсов.",
        "purchases_list": "Ваши приобретённые курсы:",
        "no_progress": "Прогресс по этому курсу отсутствует.",
        "settings": "Настройки личного кабинета:"
    }
}
