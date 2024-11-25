from aiogram import Router, types
from io import BytesIO
import time
import base64
import aiohttp
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton, InputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from database import get_product_list, get_user_role, purchase_product, add_product_to_db, get_all_products, \
    get_product_by_code, get_product_by_id
from aiogram.filters.state import StateFilter
from messages import *
from math import ceil
from bot import bot  # Импортируйте bot, если он определен в другом файле

router = Router()


# Состояния для добавления продукта
class AddProductForm(StatesGroup):
    name = State()  # Название продукта
    description = State()  # Описание продукта
    price = State()# Цена продукта
    image = State()
    category = State()
    is_subscription = State()  # Признак подписки
    subscription_period = State()  # Период подписки
    is_hidden = State()  # Добавьте это состояние
    search_product_by_code = State()


ITEMS_PER_PAGE = 5  # Количество продуктов на одной странице


@router.message(lambda message: message.text == "Продукты")
async def products(message: Message, state: FSMContext):
    user_role = await get_user_role(message.from_user.id)
    buttons = [
        [KeyboardButton(text="Купить продукт")],
    ]
    if user_role == 'partner':
        buttons.append([KeyboardButton(text="Добавить продукт")])
    buttons.append([KeyboardButton(text="Назад в главное меню")])

    # Указываем 'keyboard' как обязательное поле
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer("Выберите интересующий раздел:", reply_markup=keyboard)


# Обработка покупки продуктов (при нажатии на кнопку "Купить продукт")
@router.message(lambda message: message.text == "Купить продукт" or message.text == "Buy Product")
async def buy_product(message: Message):
    await send_product_page(message.chat.id, 1)  # Начинаем с первой страницы

async def send_product_page(chat_id, page: int):
    products = get_all_products()  # Получаем список продуктов
    # Фильтруем только те продукты, которые не скрыты
    visible_products = [p for p in products if not p.get("is_hidden", False)]

    total_pages = ceil(len(visible_products) / ITEMS_PER_PAGE)  # Количество страниц
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    products_to_show = visible_products[start_index:end_index]

    text = "📋 Список продуктов:\n\n"
    for product in products_to_show:
        name = product["name"] if not product.get("is_personal") else "Продукт доступен по коду"
        text += f"🔹 {name} — {product['price']} VED\n"

    keyboard_buttons = []

    for product in products_to_show:
        button_text = f"ℹ {product['name']} - {product['price']} VED"
        callback_data = f"product_info_{product['id']}"  # Используем ID продукта
        keyboard_buttons.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page-1}"))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"page_{page+1}"))

    keyboard_buttons.extend(navigation_buttons)
    keyboard_buttons.append(InlineKeyboardButton(text="🔍 Поиск по коду", callback_data="search_product_by_code"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[keyboard_buttons])

    await bot.send_message(chat_id, text, reply_markup=keyboard)

# Пагинация продуктов
@router.message(lambda message: message.text == "⬅️ Previous" or message.text == "➡️ Next")
async def paginate_products(message: Message, state: FSMContext):
    # Получаем текущую страницу и обрабатываем переход
    user_data = await state.get_data()
    current_page = user_data.get("current_page", 1)

    if message.text == "⬅️ Previous":
        current_page -= 1
    elif message.text == "➡️ Next":
        current_page += 1

    await state.update_data(current_page=current_page)

    # Отправляем новую страницу продуктов
    await send_product_page(message.chat.id, current_page)


@router.callback_query(lambda callback: callback.data == "search_product_by_code")
async def search_product_by_code_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код продукта для поиска.")  # Запрашиваем код продукта
    await state.set_state("search_product_by_code")  # Устанавливаем состояние, чтобы ожидать код
    await callback.answer()  # Ответ на инлайн кнопку


@router.message(StateFilter("search_product_by_code"))
async def search_product_by_code_input(message: Message, state: FSMContext):
    product_code = message.text.strip()  # Получаем введенный код

    # Получаем продукт по коду из базы данных
    product = get_product_by_code(product_code)

    if product:
        # Отправляем информацию о продукте
        text = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: {product['price']} VED"
        )
        # Отправляем изображение, если оно есть
        if product["image"]:
            await message.answer_photo(product["image"], caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(f"❌ Продукт с кодом {product_code} не найден.")

    await state.finish()  # Завершаем состояние после обработки




# Обработчик для команды "Добавить продукт"
@router.message(lambda message: message.text in ["Добавить продукт", "Add Product"])
async def add_product(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_role = await get_user_role(user_id)

    # Проверяем, что пользователь является партнером
    if user_role != 'partner':
        await message.answer("❌ У вас нет прав для добавления продуктов.")
        return

    # Начинаем процесс добавления продукта
    await message.answer("Введите название нового продукта:")
    await state.set_state(AddProductForm.name)

# Логика добавления названия продукта
@router.message(AddProductForm.name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание продукта:")
    await state.set_state(AddProductForm.description)

@router.message(AddProductForm.description)
async def add_product_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)

    # Добавить выбор категории
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Корпоративный ретрит", callback_data="category_retreat")],
            [InlineKeyboardButton(text="Онлайн-сессия с терапевтом", callback_data="category_session")],
            [InlineKeyboardButton(text="Другое", callback_data="category_other")],
        ]
    )
    await message.answer("Выберите категорию продукта:", reply_markup=keyboard)
    await state.set_state(AddProductForm.category)

@router.callback_query(lambda callback: callback.data.startswith("category_"))
async def add_product_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]  # Извлекаем категорию
    await state.update_data(category=category)
    await callback.message.answer("Введите цену продукта (в VED):")
    await state.set_state(AddProductForm.price)

# Логика добавления цены продукта
@router.message(AddProductForm.price)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)

        # Запрашиваем изображение
        await message.answer("Отправьте изображение продукта:")
        await state.set_state(AddProductForm.image)

    except ValueError:
        await message.answer("Цена должна быть числом. Попробуйте снова.")

# Логика добавления изображения
@router.message(AddProductForm.image)
async def add_product_image(message: Message, state: FSMContext):
    if not message.photo:  # Проверяем, содержит ли сообщение фотографию
        await message.answer("Пожалуйста, отправьте фотографию продукта.")
        return

    # Сохраняем фотографию
    photo = message.photo[-1]  # Берем фотографию наибольшего размера
    file_id = photo.file_id
    await state.update_data(image=file_id)

    await message.answer("Это подписка? (да/нет)")
    await state.set_state(AddProductForm.is_subscription)

# Логика выбора подписки (является ли продукт подпиской)
@router.message(AddProductForm.is_subscription)
async def add_is_subscription(message: Message, state: FSMContext):
    is_subscription = message.text.strip().lower()

    if is_subscription == "да":
        await state.update_data(is_subscription=True)
        await message.answer("Введите период подписки в месяцах:")
        await state.set_state(AddProductForm.subscription_period)
    elif is_subscription == "нет":
        await state.update_data(is_subscription=False)
        await ask_hide_product(message, state)
    else:
        await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")

# Логика добавления периода подписки
@router.message(AddProductForm.subscription_period)
async def add_subscription_period(message: Message, state: FSMContext):
    try:
        period = int(message.text)
        if period <= 0:
            raise ValueError

        await state.update_data(subscription_period=period)
        await ask_hide_product(message, state)
    except ValueError:
        await message.answer("Период подписки должен быть положительным числом. Попробуйте снова.")

# Вопрос о скрытии продукта
async def ask_hide_product(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Скрыть", callback_data="hide_product_yes")],
            [InlineKeyboardButton(text="Оставить видимым", callback_data="hide_product_no")],
        ]
    )
    await message.answer("Вы хотите скрыть продукт?", reply_markup=keyboard)
    await state.set_state(AddProductForm.is_hidden)

@router.callback_query(lambda callback: callback.data.startswith("hide_product_"))
async def set_product_visibility(callback: CallbackQuery, state: FSMContext):
    is_hidden = callback.data == "hide_product_yes"
    await state.update_data(is_hidden=is_hidden)

    # Сохраняем продукт
    await save_product(callback.message, state)
    visibility = "скрытым" if is_hidden else "видимым"
    await callback.message.answer(f"Продукт успешно добавлен и отмечен как {visibility}.")

async def save_product(message: Message, state: FSMContext):
    product_data = await state.get_data()

    # Получаем данные о продукте
    image = product_data.get("image")
    is_hidden = product_data.get("is_hidden", False)

    # Генерация уникального кода продукта
    product_code = f"PRD-{int(time.time())}"

    # Добавляем продукт в базу данных
    await add_product_to_db(
        name=product_data["name"],
        description=product_data["description"],
        price=product_data["price"],
        is_subscription=product_data["is_subscription"],
        partner_id=message.from_user.id,
        image=image,
        subscription_period=product_data.get("subscription_period"),
        code=product_code,
        is_hidden=is_hidden
    )

    await message.answer(f"Продукт успешно добавлен! Уникальный код продукта: {product_code}")
    await state.clear()



@router.callback_query(lambda callback: callback.data.startswith("product_info_"))
async def product_info_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])  # Извлекаем ID продукта
    product = get_product_by_id(product_id)  # Получаем продукт по ID

    if product:
        # Обработка скрытого продукта
        if product["is_hidden"]:
            await callback.message.answer("❌ Этот продукт скрыт.")
            return

        # Отправляем информацию о продукте
        text = (
            f"📦 <b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"💰 Цена: {product['price']} VED"
        )
        if product["image"]:
            await callback.message.answer_photo(product["image"], caption=text, parse_mode="HTML")
        else:
            await callback.message.answer(text, parse_mode="HTML")
    else:
        await callback.message.answer("❌ Продукт не найден.")




@router.callback_query(lambda callback: callback.data.startswith("page_"))
async def pagination_handler(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])  # Извлекаем номер страницы
    await send_product_page(callback.message.chat.id, page)  # Отправляем новую страницу продуктов
