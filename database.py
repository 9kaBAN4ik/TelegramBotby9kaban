import sqlite3
from config import DB_PATH



# Функция для подключения к базе данных
def connect_db():
    return sqlite3.connect(DB_PATH)


def initialize_db():
    with connect_db() as conn:
        cursor = conn.cursor()

        # Создание таблицы пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'en',
            balance REAL DEFAULT 0,
            referral_link TEXT,
            role TEXT DEFAULT 'user'  -- Добавляем новый столбец для роли
        )
        """)
        # Создание таблицы продуктов (с добавлением столбца partner_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                is_subscription INTEGER NOT NULL,
                subscription_period TEXT,
                partner_id INTEGER NOT NULL,
                image TEXT,
                type TEXT,  -- Тип продукта (например, "Корпоративный ретрит", "Онлайн-сессия")
                code TEXT UNIQUE,  -- Уникальный код продукта
                is_hidden INTEGER DEFAULT 0  -- Признак, скрыт ли продукт (0 - не скрыт, 1 - скрыт)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                purchase_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)

        # Таблица для хранения информации о рефералах
        cursor.execute("""
               CREATE TABLE IF NOT EXISTS referrals (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   referrer_id INTEGER,  -- ID пользователя, который пригласил
                   referred_id INTEGER,  -- ID приглашённого пользователя
                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
               )
               """)
        # Таблица для курсов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                partner_id INTEGER
            )
        """)

        # Таблица для уроков
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    title TEXT,
                    description TEXT,
                    material_link TEXT,
                    FOREIGN KEY(course_id) REFERENCES courses(id)
                )
                """)

        # Таблица для вопросов
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id INTEGER,
                    text TEXT,
                    options TEXT,
                    correct_answer INTEGER,
                    FOREIGN KEY(lesson_id) REFERENCES lessons(id)
                )
                """)
        # Таблица для отслеживания прогресса пользователя
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,  -- ID пользователя
                    lesson_id INTEGER,  -- ID урока
                    completed BOOLEAN DEFAULT FALSE,  -- Флаг завершения урока
                    completion_date DATETIME,  -- Дата завершения
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(lesson_id) REFERENCES lessons(id)
                )
                """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                credo TEXT NOT NULL,
                logo_url TEXT,
                show_in_list BOOLEAN DEFAULT TRUE
            )
        """)
        conn.commit()



# Функция для добавления пользователя в базу данных, если его ещё нет
async def add_user(user_id: int, username: str, first_name: str):
    conn = connect_db()
    cursor = conn.cursor()

    # Проверка, существует ли уже пользователь в базе данных
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("""
        INSERT INTO users (user_id, username, first_name, role)
        VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, "user"))  # Устанавливаем роль по умолчанию
        conn.commit()
    conn.close()
def add_partner(name: str, credo: str, logo_url: str = None, show_in_list: bool = True):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO partners (name, credo, logo_url, show_in_list)
            VALUES (?, ?, ?, ?)
        """, (name, credo, logo_url, show_in_list))
        conn.commit()
def get_visible_partners():
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, credo, logo_url
            FROM partners
            WHERE show_in_list = 1
        """)
        return cursor.fetchall()

# Функция для установки роли пользователя
async def set_user_role(user_id: int, role: str):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    conn.commit()
    conn.close()


# Функция для получения роли пользователя
async def get_user_role(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

async def is_partner(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0] == "partner"
# Получение баланса пользователя
async def get_user_balance(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]  # Возвращаем баланс
    else:
        return 0  # Если пользователь не найден, возвращаем 0

async def process_payment(user_id: int, product_id: int) -> bool:
    """
    Проверяет баланс пользователя, списывает стоимость продукта и возвращает статус оплаты.
    :param user_id: ID пользователя
    :param product_id: ID продукта
    :return: True, если оплата прошла успешно, иначе False
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Получаем баланс пользователя
        user_balance = await get_user_balance(user_id)

        # Получаем стоимость продукта
        cursor.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return False  # Продукт не найден
        product_price = product[0]

        # Проверяем, достаточно ли средств на балансе
        if user_balance < product_price:
            return False  # Недостаточно средств

        # Списываем стоимость продукта с баланса пользователя
        new_balance = user_balance - product_price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

        # Фиксируем покупку в таблице `purchases`
        cursor.execute("""
        INSERT INTO purchases (user_id, product_id)
        VALUES (?, ?)
        """, (user_id, product_id))

        conn.commit()
        return True  # Оплата прошла успешно

    except Exception as e:
        print(f"Ошибка при обработке оплаты: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()

async def get_user_referral_link(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Проверяем, есть ли пользователь в базе данных
        cursor.execute("SELECT referral_link FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result and result[0]:
            # Если ссылка уже существует, возвращаем её
            return result[0]

        # Если ссылки нет, проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()

        if not user_exists:
            # Если пользователь отсутствует, выбрасываем исключение или обрабатываем это явно
            raise ValueError("Пользователь не найден в базе данных. Сначала зарегистрируйтесь через /start.")

        # Создаём новую реферальную ссылку
        referral_link = f"https://t.me/botkworktest_bot?start=ref{user_id}"
        cursor.execute(
            "UPDATE users SET referral_link = ? WHERE user_id = ?",
            (referral_link, user_id),
        )
        conn.commit()

        return referral_link

async def get_courses_by_partner(partner_id: int) -> list[dict]:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title FROM courses WHERE partner_id = ?
    """, (partner_id,))
    courses = cursor.fetchall()
    conn.close()

    # Возвращаем курсы в виде списка словарей
    return [{"id": course[0], "title": course[1]} for course in courses]

async def is_user_partner(user_id: int) -> bool:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 'partner'
# Получение списка продуктов
async def get_product_list():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products")
    products = cursor.fetchall()
    conn.close()
    return [{"name": product[0], "price": product[1]} for product in products]

async def is_user_partner(user_id: int) -> bool:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_partner FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] == 1 if result else False

# Добавление нового продукта
async def add_product(name: str, description: str, price: float, partner_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (name, description, price, partner_id)
        VALUES (?, ?, ?, ?)
    """, (name, description, price, partner_id))
    conn.commit()
    conn.close()
# Функция для добавления нового продукта
async def add_product_to_db(
    name: str,
    description: str,
    price: float,
    is_subscription: bool,
    partner_id: int,
    image: str = None,
    subscription_period: int = None,
    type: str = None,  # Тип продукта (например, "Корпоративный ретрит", "Онлайн-сессия")
    code: str = None,  # Уникальный код продукта
    is_hidden: bool = False  # Признак, скрыт ли продукт
):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO products (name, description, price, is_subscription, partner_id, image, subscription_period, type, code, is_hidden)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, description, price, is_subscription, partner_id, image, subscription_period, type, code, is_hidden))
    conn.commit()
    conn.close()





async def purchase_product(user_id: int, price: float) -> bool:
    conn = connect_db()
    cursor = conn.cursor()

    # Проверяем, хватает ли баланса у пользователя
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result and result[0] >= price:
        # Обновляем баланс
        new_balance = result[0] - price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()
        conn.close()
        return True  # Покупка успешна
    else:
        conn.close()
        return False  # Недостаточно средств

async def add_course(title: str, description: str, partner_id: int) -> int:
    """
    Добавляет новый курс в базу данных.

    :param title: Название курса.
    :param description: Описание курса.
    :param partner_id: ID партнера, связанного с курсом.
    :return: ID добавленного курса.
    """
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO courses (title, description, partner_id)
            VALUES (?, ?, ?)
        """, (title, description, partner_id))
        conn.commit()
        course_id = cursor.lastrowid
        return course_id
    except sqlite3.Error as e:
        # Логирование ошибки
        print(f"Ошибка при добавлении курса: {e}")
        raise
    finally:
        # Закрытие соединения в любом случае
        if conn:
            conn.close()


async def get_courses_for_partner(partner_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM courses WHERE partner_id = ?", (partner_id,))
    courses = cursor.fetchall()
    conn.close()
    return [{"id": course[0], "title": course[1], "description": course[2]} for course in courses]


async def get_course_by_id(course_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()
    conn.close()
    if not course:
        raise ValueError(f"Курс с ID {course_id} не найден.")
    return {"id": course[0], "title": course[1], "description": course[2]}


async def get_all_courses():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM courses")
    courses = cursor.fetchall()
    conn.close()
    return [{"id": course[0], "title": course[1], "description": course[2]} for course in courses]

async def add_lesson(course_id: int, title: str, description: str, material_link: str = None):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO lessons (course_id, title, description, material_link)
    VALUES (?, ?, ?, ?)
    """, (course_id, title, description, material_link))
    conn.commit()
    conn.close()

async def get_lesson_by_id(lesson_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, material_link FROM lessons WHERE id = ?", (lesson_id,))
    lesson = cursor.fetchone()
    conn.close()
    return {"id": lesson[0], "title": lesson[1], "description": lesson[2], "material_link": lesson[3]} if lesson else None

async def get_lessons_for_course(course_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM lessons WHERE course_id = ?", (course_id,))
    lessons = cursor.fetchall()
    conn.close()
    return [{"id": lesson[0], "title": lesson[1], "description": lesson[2]} for lesson in lessons]

async def add_question(question_text: str, options: str, correct_answer: int, lesson_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions (text, options, correct_answer, lesson_id) 
        VALUES (?, ?, ?, ?)
    """, (question_text, options, correct_answer, lesson_id))
    conn.commit()
    conn.close()


async def get_questions_for_lesson(lesson_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, options, correct_answer FROM questions WHERE lesson_id = ?", (lesson_id,))
    questions = cursor.fetchall()
    conn.close()
    return [{"id": question[0], "text": question[1], "options": question[2], "correct_answer": question[3]} for question in questions]

async def get_partner_for_course(course_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM partners WHERE course_id = ?", (course_id,))
    partner = cursor.fetchone()
    conn.close()
    return partner[0] if partner else None


async def get_questions_for_partner(partner_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    query = """
    SELECT q.text, q.options
    FROM questions q
    JOIN lessons l ON q.lesson_id = l.id
    JOIN courses c ON l.course_id = c.id
    WHERE c.partner_id = ?
    """

    cursor.execute(query, (partner_id,))
    questions = cursor.fetchall()

    conn.close()

    question_list = []
    for question in questions:
        question_list.append({
            "text": question[0],
            "options": question[1]
        })

    return question_list

async def update_course_tags(course_id: int, tags: list[str]):
    conn = connect_db()
    cursor = conn.cursor()
    tags_str = ",".join(tags)
    cursor.execute("UPDATE courses SET tags = ? WHERE id = ?", (tags_str, course_id))
    conn.commit()
    conn.close()

async def get_courses_by_tag(tag: str):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM courses WHERE tags LIKE ?", (f"%{tag}%",))
    courses = cursor.fetchall()
    conn.close()
    return [{"id": course[0], "title": course[1]} for course in courses]

async def get_user_progress(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT lesson_id) as completed, 
               (SELECT COUNT(*) FROM lessons) as total
        FROM user_progress WHERE user_id = ?
    """, (user_id,))
    progress = cursor.fetchone()
    conn.close()
    return {"completed_lessons": progress[0], "total_lessons": progress[1]} if progress else None

async def update_user_progress(user_id: int, lesson_id: int):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO user_progress (user_id, lesson_id)
        VALUES (?, ?)
    """, (user_id, lesson_id))
    conn.commit()
    conn.close()

async def delete_course(course_id):
    await db_execute("DELETE FROM courses WHERE id = ?", (course_id,))
    await db_execute("DELETE FROM lessons WHERE course_id = ?", (course_id,))

async def update_lesson_title(lesson_id, new_title):
    query = "UPDATE lessons SET title = ? WHERE id = ?"
    await db_execute(query, (new_title, lesson_id))

async def get_user_for_question(question_id):
    query = "SELECT user_id FROM questions WHERE id = ?"
    result = await db_fetchone(query, (question_id,))
    return result['user_id'] if result else None


def mark_lesson_as_completed(user_id, lesson_id):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO user_progress (user_id, lesson_id, completed, completion_date)
        VALUES (?, ?, TRUE, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, lesson_id) 
        DO UPDATE SET completed = TRUE, completion_date = CURRENT_TIMESTAMP
        """, (user_id, lesson_id))
        conn.commit()

async def get_completed_lessons(user_id, course_id):
    # Получить количество завершённых уроков для данного пользователя и курса
    completed_lessons = await db.fetch_all(
        "SELECT COUNT(*) FROM lesson_progress WHERE user_id = ? AND course_id = ? AND is_completed = TRUE",
        user_id, course_id
    )
    return completed_lessons[0][0] if completed_lessons else 0

async def get_completed_questions(user_id, course_id):
    # Получить количество завершённых вопросов для данного пользователя и курса
    completed_questions = await db.fetch_all(
        "SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND course_id = ? AND is_completed = TRUE",
        user_id, course_id
    )
    return completed_questions[0][0] if completed_questions else 0

async def update_question_progress(user_id, course_id, lesson_id, question_id, is_completed):
    await db.execute(
        "INSERT INTO user_progress (user_id, course_id, lesson_id, question_id, is_completed) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, course_id, lesson_id, question_id) "
        "DO UPDATE SET is_completed = ?",
        user_id, course_id, lesson_id, question_id, is_completed, is_completed
    )
async def update_lesson_progress(user_id, course_id, lesson_id, is_completed):
    await db.execute(
        "INSERT INTO lesson_progress (user_id, course_id, lesson_id, is_completed) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, course_id, lesson_id) "
        "DO UPDATE SET is_completed = ?",
        user_id, course_id, lesson_id, is_completed, is_completed
    )
async def check_course_completion(user_id, course_id):
    completed_lessons = await get_completed_lessons(user_id, course_id)
    total_lessons = len(await get_lessons_for_course(course_id))  # Получаем все уроки курса

    if completed_lessons == total_lessons:
        await notify_user_course_completed(user_id, course_id)

async def get_referral_count(user_id: int) -> int:
    """Получает количество приглашённых пользователей."""
    query = """
    SELECT COUNT(*) FROM referrals
    WHERE referrer_id = ?
    """
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    count = cursor.fetchone()[0]
    return count

def get_user_earnings(user_id: int) -> int:
    """
    Получить заработок пользователя на основе приглашённых рефералов.
    :param user_id: ID пользователя
    :return: Заработанные бонусы
    """
    query = """
    SELECT COUNT(*) 
    FROM referrals 
    WHERE referrer_id = ?
    """
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    referral_count = result[0] if result else 0  # Если результата нет, то 0
    cursor.close()
    conn.close()

    # Каждый приглашённый приносит 10 Ved
    earnings = referral_count * 10
    return earnings
def get_all_products():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return [
        {"id": row[0], "name": row[1], "description": row[2], "price": row[3], "is_personal": bool(row[6])}
        for row in products
    ]
def get_product_by_id(product_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, description, price, image, type, is_hidden
        FROM products 
        WHERE id = ?
    """, (product_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "type": row[5],
            "is_hidden": bool(row[6])
        }
    return None
# Функция для получения продукта по коду (с учетом скрытия)
def get_product_by_code(code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, description, price, image, type, is_hidden 
        FROM products 
        WHERE code = ?
    """, (code,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "type": row[5],
            "is_hidden": bool(row[6])  # Не проверяем скрытость, все показываем
        }
    return None


# Функция для получения всех видимых продуктов (где is_hidden = 0)
def get_visible_products():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, image, type FROM products WHERE is_hidden = 0")
    rows = cursor.fetchall()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "type": row[5]
        })
    return products

# Функция для получения всех продуктов, включая скрытые (по коду)
def get_all_products():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, image, type, is_hidden FROM products")
    rows = cursor.fetchall()
    conn.close()

    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "type": row[5],
            "is_hidden": bool(row[6])
        })
    return products

def mark_product_as_purchased(user_id, product_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO purchases (user_id, product_id)
    VALUES (?, ?)
    """, (user_id, product_id))
    conn.commit()
    conn.close()

async def purchase_course(user_id: int, product_id: int):
    with connect_db() as conn:
        cursor = conn.cursor()

        # Проверяем наличие продукта
        cursor.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return "Продукт не найден."

        price = product[0]

        # Проверяем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return "Пользователь не найден."

        balance = user[0]
        if balance < price:
            return "Недостаточно средств для покупки."

        # Списываем сумму с баланса
        new_balance = balance - price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

        # Добавляем покупку
        cursor.execute("INSERT INTO purchases (user_id, product_id) VALUES (?, ?)", (user_id, product_id))

        # Получаем курс, связанный с продуктом
        cursor.execute("SELECT id FROM courses WHERE id = ?", (product_id,))
        course = cursor.fetchone()
        if not course:
            return "Курс не найден, но покупка зарегистрирована."

        conn.commit()
        return f"Покупка успешно завершена. Вы получили доступ к курсу с ID {course[0]}."


async def get_next_lesson(user_id: int, course_id: int):
    with connect_db() as conn:
        cursor = conn.cursor()

        # Проверяем, куплен ли курс
        cursor.execute("""
            SELECT 1 FROM purchases
            WHERE user_id = ? AND product_id = ?
        """, (user_id, course_id))
        if not cursor.fetchone():
            return "У вас нет доступа к этому курсу."

        # Ищем первый незавершённый урок
        cursor.execute("""
            SELECT l.id, l.title, l.description, l.material_link
            FROM lessons l
            LEFT JOIN user_progress up ON l.id = up.lesson_id AND up.user_id = ?
            WHERE l.course_id = ? AND (up.completed IS NULL OR up.completed = 0)
            ORDER BY l.id LIMIT 1
        """, (user_id, course_id))
        lesson = cursor.fetchone()
        if not lesson:
            return "Все уроки курса завершены."

        lesson_id, title, description, material_link = lesson
        return f"Следующий урок:\n{title}\n{description}\nМатериалы: {material_link}"
async def complete_lesson(user_id: int, lesson_id: int):
    with connect_db() as conn:
        cursor = conn.cursor()

        # Проверяем, существует ли урок
        cursor.execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,))
        if not cursor.fetchone():
            return "Урок не найден."

        # Проверяем, завершал ли пользователь этот урок
        cursor.execute("""
            SELECT completed FROM user_progress
            WHERE user_id = ? AND lesson_id = ?
        """, (user_id, lesson_id))
        progress = cursor.fetchone()
        if progress and progress[0]:
            return "Вы уже завершили этот урок."

        # Отмечаем урок завершённым
        cursor.execute("""
            INSERT INTO user_progress (user_id, lesson_id, completed, completion_date)
            VALUES (?, ?, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, lesson_id) DO UPDATE SET completed = TRUE, completion_date = CURRENT_TIMESTAMP
        """, (user_id, lesson_id))
        conn.commit()
        return "Урок завершён."


# Функция для создания таблиц при запуске бота
if __name__ == "__main__":
    initialize_db()
