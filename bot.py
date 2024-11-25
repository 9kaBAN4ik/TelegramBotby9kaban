from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton
import asyncio
import logging
from config import TOKEN
from handlers import (
    start_handler,
    balance_handler,
    add_product_handler,
)
from handlers.handlers_for_study import router as study_router  # Подключаем весь маршрутизатор для учебных хэндлеров
from handlers.referrals import referral_router  # Хэндлер для реферальной системы
from database import initialize_db
from admin import router as admin_router  # Подключаем админский маршрутизатор
from handlers.info_handler import router as info_router
from handlers.personal_info import router as myinfo

# Настроим логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/balance", description="Показать баланс"),
        BotCommand(command="/products", description="Посмотреть доступные продукты"),
        BotCommand(command="/referral_link", description="Получить реферальную ссылку"),  # Новая команда для ссылки
        BotCommand(command="/add_partner", description="Добавить партнёра"),  # Команда для админа
        BotCommand(command="/add_course", description="Добавить новый курс"),
        BotCommand(command="/start_course", description="Начать курс"),
        BotCommand(command="/view_courses", description="Посмотреть доступные курсы"),
        BotCommand(command="/add_lesson", description="Добавить новый урок"),
        BotCommand(command="/add_question", description="Добавить вопрос к уроку"),
        BotCommand(command="/view_questions", description="Посмотреть вопросы")
    ]
    await bot.set_my_commands(commands)

async def main():
    logger.info("Запуск бота...")
    await set_commands(bot)

    # Подключаем все маршрутизаторы
    dp.include_router(start_handler.router)
    dp.include_router(balance_handler.router)
    dp.include_router(add_product_handler.router)
    dp.include_router(study_router)  # Подключаем study_router
    dp.include_router(referral_router)  # Подключаем реферальную систему
    dp.include_router(info_router)
    dp.include_router(admin_router)  # Подключаем админский роутер
    dp.include_router(myinfo)
    logger.info("Начинаем polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    initialize_db()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Бот остановлен!")
