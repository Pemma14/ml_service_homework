import httpx
from logging import getLogger
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from bot.config import settings

logger = getLogger(__name__)
router = Router()

# Хранилище токенов пользователей (в памяти: user_id -> token)
user_tokens = {}

# Состояния для формы заполнения данных
class PredictForm(StatesGroup):
    patient_id = State()
    age = State()
    vnn_pp = State()
    clozapine = State()
    cyp2c19_1_2 = State()
    cyp2c19_1_17 = State()
    cyp2c19_17_17 = State()
    cyp2d6_1_3 = State()

# Состояния для авторизации
class LoginForm(StatesGroup):
    email = State()
    password = State()

def get_binary_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Нет")
    builder.button(text="Да")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# Главное меню с командами (кнопки отправляют слэш-команды)
# Для авторизованных и неавторизованных разные наборы
def get_main_menu_keyboard(authorized: bool):
    kb = ReplyKeyboardBuilder()
    if authorized:
        # Ряд 1
        kb.button(text="/predict")
        kb.button(text="/history")
        # Ряд 2
        kb.button(text="/balance")
        kb.button(text="/me")
        # Ряд 3
        kb.button(text="/help")
        kb.button(text="/logout")
    else:
        # Ряд 1
        kb.button(text="/login")
        kb.button(text="/help")
        # Ряд 2
        kb.button(text="/start")
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=False)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_auth = message.from_user.id in user_tokens
    kb = get_main_menu_keyboard(is_auth)
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я бот сервиса PsyPharmPredict. Помогу рассчитать риски побочных эффектов.\n\n"
        "Внизу — кнопки с основными командами. Начните с /login, а затем используйте /predict.\n"
        "Полный список команд: /help",
        reply_markup=kb
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🆘 Справка по командам:\n\n"
        "🔐 **Авторизация:**\n"
        "1️⃣ /login — Привязывает ваш аккаунт PsyPharmPredict к Telegram.\n"
        "2️⃣ /logout — Сбрасывает авторизацию в боте.\n"
        "3️⃣ /me — Показывает информацию о текущем профиле.\n\n"
        "🧠 **Функции:**\n"
        "4️⃣ /predict — Запускает пошаговую анкету (8 шагов) для получения предсказания.\n"
        "5️⃣ /balance — Показывает ваш текущий баланс кредитов.\n"
        "6️⃣ /history — Выводит 5 последних запросов.\n"
        "7️⃣ /start — Главное меню."
    )

@router.message(Command("login"))
async def cmd_login(message: types.Message, state: FSMContext):
    if message.from_user.id in user_tokens:
        return await message.answer("Вы уже авторизованы! Используйте /logout, если хотите сменить аккаунт.")
    await message.answer("Пожалуйста, введите ваш Email:")
    await state.set_state(LoginForm.email)

@router.message(LoginForm.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("Теперь введите ваш пароль:")
    await state.set_state(LoginForm.password)

@router.message(LoginForm.password)
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    email = data.get("email")
    password = message.text

    await message.answer("Проверка данных...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.bot.API_URL}/api/v1/users/login",
                json={"email": email, "password": password},
                timeout=10.0
            )
            if response.status_code == 200:
                token = response.json().get("access_token")
                user_tokens[message.from_user.id] = token
                await message.answer("✅ Авторизация успешна! Теперь вы можете использовать все функции бота.", reply_markup=get_main_menu_keyboard(True))
            else:
                await message.answer("❌ Ошибка входа. Проверьте Email/пароль и попробуйте /login снова.")
        except Exception as e:
            logger.error(f"Ошибка при логине: {e}")
            await message.answer("Произошла ошибка при подключении к сервису.")
    await state.clear()

@router.message(Command("logout"))
async def cmd_logout(message: types.Message):
    if message.from_user.id in user_tokens:
        del user_tokens[message.from_user.id]
        await message.answer("🚪 Вы успешно вышли из системы.", reply_markup=get_main_menu_keyboard(False))
    else:
        await message.answer("Вы и так не авторизованы.")

@router.message(Command("me"))
async def cmd_me(message: types.Message):
    token = await get_bot_token(message.from_user.id)
    if not token:
        return await message.answer("Пожалуйста, сначала авторизуйтесь с помощью команды /login")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.bot.API_URL}/api/v1/users/read_me",
                headers=headers,
                timeout=5.0
            )
            if response.status_code == 200:
                user = response.json()
                text = (
                    f"👤 **Ваш профиль:**\n\n"
                    f"📧 Email: {user.get('email')}\n"
                    f"📝 Имя: {user.get('first_name')} {user.get('last_name')}\n"
                    f"📞 Телефон: {user.get('phone_number')}\n"
                    f"💰 Баланс: {user.get('balance')} кредитов\n"
                    f"🎖 Роль: {user.get('role')}"
                )
                await message.answer(text, parse_mode="Markdown")
            else:
                await message.answer("Не удалось получить данные профиля. Возможно, сессия истекла, попробуйте /login.")
        except Exception as e:
            logger.error(f"Ошибка получения профиля: {e}")
            await message.answer("Ошибка при получении профиля.")

@router.message(Command("balance"))
async def cmd_balance(message: types.Message):
    token = await get_bot_token(message.from_user.id)
    if not token:
        return await message.answer("Пожалуйста, сначала авторизуйтесь с помощью команды /login")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.bot.API_URL}/api/v1/balance/check_balance",
                headers=headers,
                timeout=5.0
            )
            if response.status_code == 200:
                balance = response.json().get("balance", 0)
                await message.answer(f"💰 Ваш текущий баланс: {balance} кредитов")
            else:
                await message.answer("Не удалось получить баланс.")
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            await message.answer("Произошла ошибка при запросе баланса.")

@router.message(Command("history"))
async def cmd_history(message: types.Message):
    token = await get_bot_token(message.from_user.id)
    if not token:
        return await message.answer("Пожалуйста, сначала авторизуйтесь с помощью команды /login")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.bot.API_URL}/api/v1/requests/history",
                headers=headers,
                timeout=5.0
            )
            if response.status_code == 200:
                history = response.json()
                if not history:
                    return await message.answer("История запросов пуста.")

                # Берем последние 5
                last_5 = history[:5]
                text = "📊 Последние 5 запросов:\n\n"
                for i, req in enumerate(last_5, 1):
                    status = "✅" if req.get("status") == "success" else "⏳" if req.get("status") == "pending" else "❌"
                    date_str = req.get("created_at", "")[:16].replace("T", " ")
                    pred = req.get("prediction", "Нет данных")
                    if isinstance(pred, list) and pred:
                        pred = pred[0]
                    text += f"{i}. {status} {date_str}\n   Результат: {pred}\n\n"
                await message.answer(text)
            else:
                await message.answer("Не удалось получить историю.")
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            await message.answer("Произошла ошибка при запросе истории.")

@router.message(Command("predict"))
async def cmd_predict(message: types.Message, state: FSMContext):
    token = await get_bot_token(message.from_user.id)
    if not token:
        return await message.answer("Пожалуйста, сначала авторизуйтесь с помощью команды /login")

    await message.answer("Шаг 1/8: Введите номер пациента (или отправьте '-', чтобы пропустить):")
    await state.set_state(PredictForm.patient_id)

@router.message(PredictForm.patient_id)
async def process_patient_id(message: types.Message, state: FSMContext):
    p_id = message.text
    if p_id == "-":
        p_id = None
    await state.update_data(patient_id=p_id)
    await message.answer("Шаг 2/8: Введите возраст пациента (число):")
    await state.set_state(PredictForm.age)

@router.message(PredictForm.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = float(message.text.replace(",", "."))
        await state.update_data(age=age)
        await message.answer("Шаг 3/8: ВНН/ПП (выберите Да или Нет):", reply_markup=get_binary_keyboard())
        await state.set_state(PredictForm.vnn_pp)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для возраста.")

@router.message(PredictForm.vnn_pp)
async def process_vnn(message: types.Message, state: FSMContext):
    if message.text not in ["Нет", "Да", "0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки Да или Нет.")
    val = 1 if message.text in ["Да", "1"] else 0
    await state.update_data(vnn_pp=val)
    await message.answer("Шаг 4/8: Клозапин (выберите Да или Нет):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.clozapine)

@router.message(PredictForm.clozapine)
async def process_clozapine(message: types.Message, state: FSMContext):
    if message.text not in ["Нет", "Да", "0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки Да или Нет.")
    val = 1 if message.text in ["Да", "1"] else 0
    await state.update_data(clozapine=val)
    await message.answer("Шаг 5/8: Генетический маркер CYP2C19 1/2 (Да или Нет):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2c19_1_2)

@router.message(PredictForm.cyp2c19_1_2)
async def process_cyp1(message: types.Message, state: FSMContext):
    if message.text not in ["Нет", "Да", "0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки Да или Нет.")
    val = 1 if message.text in ["Да", "1"] else 0
    await state.update_data(cyp2c19_1_2=val)
    await message.answer("Шаг 6/8: Генетический маркер CYP2C19 1/17 (Да или Нет):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2c19_1_17)

@router.message(PredictForm.cyp2c19_1_17)
async def process_cyp2(message: types.Message, state: FSMContext):
    if message.text not in ["Нет", "Да", "0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки Да или Нет.")
    val = 1 if message.text in ["Да", "1"] else 0
    await state.update_data(cyp2c19_1_17=val)
    await message.answer("Шаг 7/8: Генетический маркер CYP2C19 *17/*17 (Да или Нет):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2c19_17_17)

@router.message(PredictForm.cyp2c19_17_17)
async def process_cyp3(message: types.Message, state: FSMContext):
    if message.text not in ["Нет", "Да", "0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки Да или Нет.")
    val = 1 if message.text in ["Да", "1"] else 0
    await state.update_data(cyp2c19_17_17=val)
    await message.answer("Шаг 8/8: Генетический маркер CYP2D6 1/3 (Да или Нет):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2d6_1_3)

async def get_bot_token(user_id: int = None):
    """Получает JWT-токен пользователя из хранилища."""
    if user_id and user_id in user_tokens:
        return user_tokens[user_id]

    # Для обратной совместимости или системных действий можно оставить демо-токен,
    # но в текущей реализации мы требуем авторизацию.
    # Если токена нет, возвращаем None.
    return None

async def _get_demo_token():
    """Получает JWT-токен для бота, используя демо-данные."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.bot.API_URL}/api/v1/users/login",
                json={
                    "email": settings.seed.DEMO_EMAIL,
                    "password": settings.seed.DEMO_PASSWORD
                },
                timeout=5.0
            )
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"Ошибка авторизации бота: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Исключение при получении токена: {e}")
        return None

@router.message(PredictForm.cyp2d6_1_3)
async def process_final(message: types.Message, state: FSMContext):
    if message.text not in ["Нет", "Да", "0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки Да или Нет.")

    data = await state.get_data()
    data['cyp2d6_1_3'] = 1 if message.text in ["Да", "1"] else 0

    await message.answer("Обработка данных, пожалуйста, подождите...", reply_markup=types.ReplyKeyboardRemove())

    try:
        # 1. Получаем токен
        token = await get_bot_token(message.from_user.id)
        if not token:
            return await message.answer("Сессия авторизации потеряна. Пожалуйста, войдите снова (/login).")

        # 2. Подготавливаем данные для API
        payload = {
            "data": [{
                "№ Пациента": data.get('patient_id'),
                "Возраст": data['age'],
                "ВНН/ПП": data['vnn_pp'],
                "Клозапин": data['clozapine'],
                "CYP2C19 1/2": data['cyp2c19_1_2'],
                "CYP2C19 1/17": data['cyp2c19_1_17'],
                "CYP2C19 *17/*17": data['cyp2c19_17_17'],
                "CYP2D6 1/3": data['cyp2d6_1_3']
            }]
        }

        # 3. Выполняем запрос с токеном
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.bot.API_URL}/api/v1/requests/predict",
                json=payload,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                result = response.json()
                if "prediction" in result:
                    prediction = result["prediction"]
                    if isinstance(prediction, list):
                        prediction = prediction[0]
                    await message.answer(f"✅ Предсказание готово:\n\n{prediction}")
                else:
                    await message.answer(f"✅ Задача выполнена: {result.get('message', 'Успешно')}")
            elif response.status_code == 202:
                result = response.json()
                request_id = result.get("request_id")
                await message.answer(
                    f"✅ Задача успешно принята и поставлена в очередь!\n\n"
                    f"🆔 ID запроса: {request_id}\n"
                    f"📊 Статус: {result.get('status')}\n\n"
                    f"Результат будет доступен в истории запросов через некоторое время."
                )
            else:
                try:
                    error_detail = response.json().get("message", "Неизвестная ошибка")
                except:
                    error_detail = response.text
                await message.answer(f"Ошибка API ({response.status_code}): {error_detail}")

    except Exception as e:
        logger.error(f"Ошибка в боте: {e}")
        await message.answer("Произошла ошибка при обращении к сервису.")
    finally:
        await state.clear()
