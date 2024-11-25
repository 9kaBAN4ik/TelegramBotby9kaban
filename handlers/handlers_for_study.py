from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import (
    add_course, add_lesson, add_question, get_course_by_id,
    get_lesson_by_id, get_partner_for_course,
    get_questions_for_partner, get_all_courses,get_courses_by_partner, is_partner, get_lessons_for_course
)
from aiogram.filters import Command, CommandStart, StateFilter, BaseFilter
router = Router()
class PartnerFilter(BaseFilter):
    async def __call__(self, message: types.Message):
        return await is_partner(message.from_user.id)
class QuestionStates(StatesGroup):
    waiting_for_course_selection = State()
    waiting_for_lesson_selection = State()
    waiting_for_question_text = State()
    waiting_for_options = State()
    waiting_for_correct_option = State()
    waiting_for_more_questions = State()
async def update_state_and_ask(
    message: types.Message,
    state: FSMContext,
    key: str,
    value: str,
    next_question: str,
    next_state: str
):
    await state.update_data({key: value})
    await message.answer(next_question)
    await state.set_state(next_state)
@router.message(Command("add_course"), PartnerFilter())
async def add_course_command(message: types.Message, state: FSMContext):
    await message.answer("Введите название курса:")
    await state.set_state("waiting_for_course_title")

@router.message(StateFilter("waiting_for_course_title"))
async def process_course_title(message: types.Message, state: FSMContext):
    await update_state_and_ask(
        message, state,
        key="course_title",
        value=message.text,
        next_question="Введите описание курса:",
        next_state="waiting_for_course_description"
    )
@router.message(StateFilter("waiting_for_course_description"))
async def process_course_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    course_title = data.get("course_title")
    course_description = message.text

    partner_id = message.from_user.id
    course_id = await add_course(title=course_title, description=course_description, partner_id=partner_id)
    await state.update_data(course_id=course_id)
    await message.answer(f"Курс '{course_title}' добавлен. Теперь вы можете добавлять уроки.")
    await state.clear()
@router.message(CommandStart())
async def start_course(message: types.Message, state: FSMContext):
    course = await get_course_by_id(1)
    if course and course.lessons:
        first_lesson = course.lessons[0]
        await send_lesson_content(first_lesson, message)
        await state.update_data(lesson_id=first_lesson.id)
    else:
        await message.answer("Курс не найден или уроки отсутствуют.")
async def send_lesson_content(lesson, message: types.Message):
    await message.answer(f"Урок: {lesson.title}\nОписание: {lesson.description}")
    if lesson.material_link:
        await message.answer(f"Ссылка на материал: {lesson.material_link}")
    await send_question(lesson, message)
async def send_question(lesson, message: types.Message):
    for question in lesson.questions:
        options = question.options.split(",")
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        for option in options:
            markup.add(KeyboardButton(option))
        await message.answer(question.text, reply_markup=markup)
@router.message(lambda message: message.text in ["Option 1", "Option 2", "Option 3"])
async def check_answer(message: types.Message, state: FSMContext):
    selected_answer = message.text
    data = await state.get_data()
    lesson_id = data.get('lesson_id')
    lesson = await get_lesson_by_id(lesson_id)

    options = lesson.options.split(",")
    correct_answer = options[lesson.correct_answer]

    if selected_answer == correct_answer:
        await message.answer("Ответ верный! Переходим к следующему уроку.")
        next_lesson = await get_lesson_by_id(lesson_id + 1)
        if next_lesson:
            await send_lesson_content(next_lesson, message)
            await state.update_data(lesson_id=next_lesson.id)
        else:
            await message.answer("Поздравляем, вы завершили курс!")
    else:
        await message.answer("Ответ неверный. Попробуйте снова.")
        await send_question(lesson, message)
async def get_next_lesson(current_lesson_id):
    return await get_lesson_by_id(current_lesson_id + 1)
@router.message(Command("ask_question"))
async def ask_question(message: types.Message):
    course_id = 1
    partner_id = await get_partner_for_course(course_id)
    question = message.text
    await message.answer("Ваш вопрос был отправлен партнеру.")
    await router.bot.send_message(partner_id, f"Новый вопрос от пользователя: {question}")
@router.message(Command("view_questions"))
async def view_questions(message: types.Message):
    questions = await get_questions_for_partner(message.from_user.id)
    if questions:
        for question in questions:
            await message.answer(f"Вопрос: {question.text}\nОтветы: {question.options}")
    else:
        await message.answer("Вопросов не найдено.")
@router.message(Command("add_lesson"))
async def add_lesson_command(message: types.Message, state: FSMContext):
    partner_id = message.from_user.id
    courses = await get_courses_by_partner(partner_id)
    if not courses:
        await message.answer("У вас пока нет созданных курсов. Сначала создайте курс с помощью команды /add_course.")
        return
    buttons = [
        InlineKeyboardButton(text=course["title"], callback_data=f"select_course_{course['id']}")
        for course in courses
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    await message.answer("Выберите курс, к которому хотите добавить урок:", reply_markup=keyboard)
    await state.set_state("waiting_for_course_selection")
@router.callback_query(StateFilter("waiting_for_course_selection"))
async def process_course_selection(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if not data.startswith("select_course_"):
        await callback_query.message.answer("Неверный выбор. Попробуйте снова.")
        return
    course_id = int(data.replace("select_course_", ""))
    await state.update_data(course_id=course_id)
        await callback_query.message.answer("Введите название нового урока:")
    await state.set_state("waiting_for_lesson_title")
    await callback_query.answer()
@router.message(StateFilter("waiting_for_course_selection"))
async def process_course_selection(message: types.Message, state: FSMContext):
    course = await get_course_by_id(message.text)  # Ensure course title matches exactly
    if not course:
        await message.answer("Курс не найден. Попробуйте снова.")
        return
    await state.update_data(course_id=course.id)
    await message.answer("Введите название нового урока:")
    await state.set_state("waiting_for_lesson_title")
@router.message(StateFilter("waiting_for_lesson_title"))
async def process_lesson_title(message: types.Message, state: FSMContext):
    lesson_title = message.text
    await state.update_data(lesson_title=lesson_title)  # Сохраняем название урока в состоянии
    await message.answer("Введите описание для урока:")
    await state.set_state("waiting_for_lesson_description")
@router.message(StateFilter("waiting_for_lesson_description"))
async def process_lesson_description(message: types.Message, state: FSMContext):
    lesson_description = message.text
    data = await state.get_data()
    lesson_title = data.get("lesson_title")
    course_id = data.get("course_id")
    if not course_id:
        await message.answer("Ошибка: ID курса не найден. Сначала создайте курс с помощью команды /add_course.")
        return
    await add_lesson(course_id=course_id, title=lesson_title, description=lesson_description)
    await message.answer(f"Урок '{lesson_title}' добавлен в курс.")
    await state.clear()
@router.message(StateFilter("waiting_for_course_description"))
async def process_course_description(message: types.Message, state: FSMContext):
    course_description = message.text
    data = await state.get_data()
    course_title = data.get("course_title")
    course_id = await add_course(title=course_title, description=course_description)
    await state.update_data(course_id=course_id)

    await message.answer(f"Курс '{course_title}' (ID: {course_id}) добавлен! Теперь вы можете добавлять уроки.")
    await state.clear()
@router.message(Command("view_courses"))
async def view_courses(message: types.Message):
    courses = await get_all_courses()
    if courses:
        for course in courses:
            await message.answer(f"Курс: {course.title}\nОписание: {course.description}")
            await asyncio.sleep(0.5)
    else:
        await message.answer("Курсы не найдены.")
@router.message(Command("view_course"))
async def view_course(message: types.Message):
    try:
        course = await get_course_by_id()
        await message.answer(f"Курс: {course.title}\nОписание: {course.description}")
    except ValueError as e:
        await message.answer(str(e))
@router.message(Command("add_tags"))
async def add_tags_command(message: types.Message, state: FSMContext):
    await message.answer("Введите теги через запятую:")
    await state.set_state("waiting_for_tags")
@router.message(StateFilter("waiting_for_tags"))
async def process_tags(message: types.Message, state: FSMContext):
    tags = message.text.split(",")
    data = await state.get_data()
    course_id = data.get("course_id")
    if not course_id:
        await message.answer("Ошибка: Сначала выберите курс.")
        return
    await update_course_tags(course_id, tags)
    await message.answer("Теги обновлены.")
    await state.clear()
@router.message(Command("search_by_tag"))
async def search_courses_by_tag(message: types.Message):
    await message.answer("Введите тег для поиска курсов:")
    await state.set_state("waiting_for_tag_search")
@router.message(StateFilter("waiting_for_tag_search"))
async def process_tag_search(message: types.Message, state: FSMContext):
    tag = message.text.strip()
    courses = await get_courses_by_tag(tag)
    if courses:
        for course in courses:
            await message.answer(f"Курс: {course['title']}\nОписание: {course['description']}")
    else:
        await message.answer("Курсы по данному тегу не найдены.")
    await state.clear()
@router.message(Command("ask_master"))
async def ask_master_command(message: types.Message, state: FSMContext):
    await message.answer("Введите ваш вопрос:")
    await state.set_state("waiting_for_master_question")
@router.message(StateFilter("waiting_for_master_question"))
async def process_master_question(message: types.Message, state: FSMContext):
    question_text = message.text
    data = await state.get_data()
    course_id = data.get("course_id")
    partner_id = await get_partner_for_course(course_id)
    if not partner_id:
        await message.answer("Ошибка: Мастер для данного курса не найден.")
        return
    await router.bot.send_message(partner_id, f"Новый вопрос от пользователя: {question_text}")
    await message.answer("Ваш вопрос отправлен мастеру.")
    await state.clear()
@router.message(Command("answer_question"))
async def answer_question_command(message: types.Message, state: FSMContext):
    await message.answer("Введите ID вопроса и ваш ответ в формате:\n`<ID вопроса>: <ответ>`", parse_mode="Markdown")
    await state.set_state("waiting_for_answer")


@router.message(StateFilter("waiting_for_answer"))
async def process_answer(message: types.Message, state: FSMContext):
    try:
        question_id, answer_text = map(str.strip, message.text.split(":"))
        question_id = int(question_id)

        user_id = await get_user_for_question(question_id)
        if user_id:
            await router.bot.send_message(user_id, f"Мастер ответил на ваш вопрос: {answer_text}")
            await message.answer("Ответ отправлен пользователю.")
        else:
            await message.answer("Ошибка: Пользователь для данного вопроса не найден.")
    except ValueError:
        await message.answer("Ошибка формата. Попробуйте снова.")
    finally:
        await state.clear()

@router.message(Command("my_progress"))
async def view_progress(message: types.Message):
    user_id = message.from_user.id
    courses = await get_all_courses()
    progress_text = ""

    for course in courses:
        completed_lessons = await get_completed_lessons(user_id, course.id)
        total_lessons = len(course.lessons)
        remaining_lessons = total_lessons - completed_lessons

        # Прогресс по вопросам
        completed_questions = await get_completed_questions(user_id, course.id)
        total_questions = sum(len(lesson.questions) for lesson in course.lessons)
        remaining_questions = total_questions - completed_questions

        progress_text += (
            f"Курс: {course.title}\n"
            f"Завершено уроков: {completed_lessons} из {total_lessons}\n"
            f"Осталось уроков: {remaining_lessons}\n"
            f"Завершено вопросов: {completed_questions} из {total_questions}\n"
            f"Осталось вопросов: {remaining_questions}\n\n"
        )

    if progress_text:
        await message.answer(progress_text)
    else:
        await message.answer("Ваш прогресс не найден. Начните обучение!")

@router.message(Command("delete_course"))
async def delete_course_command(message: types.Message):
    await message.answer("Введите ID курса, который хотите удалить:")
    await state.set_state("waiting_for_course_deletion")


@router.message(StateFilter("waiting_for_course_deletion"))
async def process_course_deletion(message: types.Message, state: FSMContext):
    course_id = int(message.text)
    await delete_course(course_id)
    await message.answer("Курс удалён.")
    await state.clear()


@router.message(Command("edit_lesson"))
async def edit_lesson_command(message: types.Message):
    await message.answer("Введите ID урока для редактирования:")
    await state.set_state("waiting_for_lesson_edit")


@router.message(StateFilter("waiting_for_lesson_edit"))
async def process_lesson_edit(message: types.Message, state: FSMContext):
    lesson_id = int(message.text)
    lesson = await get_lesson_by_id(lesson_id)
    if lesson:
        await message.answer(f"Текущий урок: {lesson['title']}\nВведите новое название:")
        await state.update_data(lesson_id=lesson_id)
        await state.set_state("waiting_for_new_lesson_title")
    else:
        await message.answer("Урок не найден.")


@router.message(StateFilter("waiting_for_new_lesson_title"))
async def process_new_lesson_title(message: types.Message, state: FSMContext):
    lesson_id = (await state.get_data()).get("lesson_id")
    new_title = message.text
    await update_lesson_title(lesson_id, new_title)
    await message.answer("Название урока обновлено.")
    await state.clear()

@router.message(Command("delete_lesson"))
async def delete_lesson_command(message: types.Message, state: FSMContext):
    await message.answer("Введите ID урока, который хотите удалить:")
    await state.set_state("waiting_for_lesson_deletion")

@router.message(StateFilter("waiting_for_lesson_deletion"))
async def process_lesson_deletion(message: types.Message, state: FSMContext):
    lesson_id = int(message.text)
    await delete_lesson(lesson_id)
    await message.answer("Урок удалён.")
    await state.clear()


@router.message(Command("add_question"))
async def add_question_command(message: types.Message, state: FSMContext):
    partner_id = message.from_user.id
    courses = await get_courses_by_partner(partner_id)

    if not courses:
        await message.answer("У вас пока нет созданных курсов. Сначала создайте курс с помощью команды /add_course.")
        return

    lessons = []
    for course in courses:
        lessons.extend(await get_lessons_for_course(course["id"]))  # Используем уже готовую функцию

    if not lessons:
        await message.answer("У вас пока нет уроков. Сначала создайте уроки.")
        return

    buttons = [
        InlineKeyboardButton(text=lesson["title"], callback_data=f"select_lesson_{lesson['id']}")
        for lesson in lessons
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons[i:i+2] for i in range(0, len(buttons), 2)])
    await message.answer("Выберите урок, к которому хотите добавить вопрос:", reply_markup=keyboard)
    await state.set_state(QuestionStates.waiting_for_lesson_selection)



# 2. Обработка выбора урока
@router.callback_query(lambda c: c.data.startswith("select_lesson_"))
async def handle_lesson_selection(callback_query: CallbackQuery, state: FSMContext):
    lesson_id = int(callback_query.data.split("_")[2])
    await state.update_data(selected_lesson_id=lesson_id)

    await callback_query.message.answer("Введите текст вопроса:")
    await state.set_state(QuestionStates.waiting_for_question_text)


# 3. Обработка текста вопроса
@router.message(StateFilter(QuestionStates.waiting_for_question_text))
async def process_question_text(message: types.Message, state: FSMContext):
    question_text = message.text
    await state.update_data(question_text=question_text)

    await message.answer("Введите варианты ответа через запятую (не более трех):")
    await state.set_state(QuestionStates.waiting_for_options)


# 4. Обработка ввода вариантов ответа
@router.message(StateFilter(QuestionStates.waiting_for_options))
async def process_options(message: Message, state: FSMContext):
    options = message.text.split(",")
    if len(options) > 3:
        await message.answer("Можно указать не более трех вариантов. Попробуйте снова.")
        return

    await state.update_data(options=options)

    await message.answer("Введите номер правильного ответа (1, 2 или 3):")
    await state.set_state(QuestionStates.waiting_for_correct_option)


# 5. Обработка правильного ответа
@router.message(StateFilter(QuestionStates.waiting_for_correct_option))
async def process_correct_option(message: Message, state: FSMContext):
    try:
        correct_option = int(message.text)
        if correct_option not in [1, 2, 3]:
            raise ValueError

        await state.update_data(correct_option=correct_option)
        data = await state.get_data()

        # Сохраняем вопрос в базу данных
        await add_question(
            question_text=data["question_text"],  # Используйте question_text вместо text
            options=",".join(data["options"]),
            correct_answer=correct_option,
            lesson_id=data["selected_lesson_id"]
        )

        await message.answer("Вопрос успешно добавлен!")

        # Спрашиваем, хочет ли пользователь добавить ещё вопрос
        await message.answer("Хотите добавить ещё один вопрос? Ответьте 'да' или 'нет'.")
        await state.set_state(QuestionStates.waiting_for_more_questions)

    except ValueError:
        await message.answer("Введите корректный номер ответа (1, 2 или 3).")


# 6. Обработка продолжения добавления вопросов
@router.message(StateFilter(QuestionStates.waiting_for_more_questions))
async def process_more_questions(message: types.Message, state: FSMContext):
    if message.text.lower() in ["да", "yes"]:
        await message.answer("Введите текст следующего вопроса:")
        await state.set_state(QuestionStates.waiting_for_question_text)
    else:
        await message.answer("Добавление вопросов завершено.")
        await state.clear()
