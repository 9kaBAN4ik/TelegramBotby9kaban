from aiogram import Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database import get_visible_partners, add_partner
router = Router()

class PartnerStates(StatesGroup):
    waiting_partner_info = State()


# Главное меню информации
@router.message(lambda message: message.text == "Инфо")
async def info_main_menu(message: Message):
    buttons = [
        [KeyboardButton(text="О нас")],
        [KeyboardButton(text="Правила")],
        [KeyboardButton(text="Обратная связь")],
        [KeyboardButton(text="Партнеры")],
        [KeyboardButton(text="Назад в главное меню")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Выберите интересующий раздел:", reply_markup=keyboard)

# Подменю "О нас"
@router.message(lambda message: message.text == "О нас")
async def about_us(message: Message):
    about_text = (
        "RaJah.WS — мы группа энтузиастов, открывших инструменты комплексного развития.\n\n"
        "Свято верим в децентрализацию и коллективное решение общих вопросов.\n\n"
        "Полезные ссылки:\n"
        "- 📚 [База знаний](https://example.com/knowledge-base)\n"
        "- 🏋️‍♀️ [Воркаут и кроссфит](https://example.com/workout)\n"
        "- 📰 [Новости спорта и науки](https://example.com/news)"
    )
    await message.answer(about_text, disable_web_page_preview=True)

# Подменю "Правила"
@router.message(lambda message: message.text == "Правила")
async def rules(message: Message):
    rules_text = (
        "Честность, порядочность, дисциплинированность, склонность к развитию и забота об окружающем мире…\n\n"
        "Каждый сам выбирает, что его делает в жизни сильней.\n"
        "Подробнее об обязанностях сторон: [Ссылка на статью](https://example.com/rules)"
    )
    await message.answer(rules_text, disable_web_page_preview=True)

# Подменю "Обратная связь"
@router.message(lambda message: message.text == "Обратная связь")
async def feedback(message: Message):
    feedback_text = (
        "Если у вас есть вопросы или предложения, напишите нам:\n\n"
        "- 📧 Email: support@rajah.ws\n"
        "- 📞 Телефон: +1234567890\n"
        "- 🌐 [Связаться через сайт](https://example.com/contact)"
    )
    await message.answer(feedback_text, disable_web_page_preview=True)

@router.message(lambda message: message.text == "Партнеры")
async def partners_menu(message: Message):
    buttons = [
        [KeyboardButton(text="Информация о партнерах")],
        [KeyboardButton(text="Стать партнером")],
        [KeyboardButton(text="Назад в главное меню")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.message(lambda message: message.text == "Информация о партнёрах")
async def partner_info(message: Message):
    partners = get_visible_partners()

    if not partners:
        await message.answer("Пока что список партнёров пуст.")
        return

    response = "Партнёры клуба:\n\n"
    for name, credo, logo_url in partners:
        response += f"🔹 {name}\n"
        response += f"Кредо: {credo}\n"
        if logo_url:
            response += f"Логотип: [Ссылка]({logo_url})\n"
        response += "\n"

    await message.answer(response, disable_web_page_preview=False)

@router.message(lambda message: message.text == "Стать партнёром")
async def become_partner(message: Message, state: FSMContext):
    await message.answer(
        "Чтобы стать партнёром, отправьте следующие данные в формате:\n\n"
        "1. Имя партнёра\n"
        "2. Ваше кредо\n"
        "3. Ссылка на логотип (необязательно)\n\n"
        "Каждый пункт должен быть на новой строке."
    )
    await state.set_state(PartnerStates.waiting_partner_info)

@router.message(StateFilter(PartnerStates.waiting_partner_info))
async def process_partner_info(message: Message, state: FSMContext):
    data = message.text.split("\n")
    if len(data) < 2:
        await message.answer("Ошибка: укажите как минимум имя и кредо.")
        return

    name = data[0].strip()
    credo = data[1].strip()
    logo_url = data[2].strip() if len(data) > 2 else None

    add_partner(name, credo, logo_url)
    await state.clear()

    await message.answer("Ваши данные успешно добавлены в список партнёров!")

@router.message(lambda message: message.text == "Назад в главное меню")
async def back_to_main_menu(message: Message):
    buttons = [
        [KeyboardButton(text="Продукты")],
        [KeyboardButton(text="Для друзей")],
        [KeyboardButton(text="Баланс")],
        [KeyboardButton(text="Партнеры")],
        [KeyboardButton(text="Инфо")],
    ]
    menu_markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Вы вернулись в главное меню.", reply_markup=menu_markup)
