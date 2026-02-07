import httpx
from logging import getLogger
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.config import settings

logger = getLogger(__name__)
router = Router()

# Состояния для формы заполнения данных
class PredictForm(StatesGroup):
    age = State()
    vnn_pp = State()
    clozapine = State()
    cyp2c19_1_2 = State()
    cyp2c19_1_17 = State()
    cyp2c19_17_17 = State()
    cyp2d6_1_3 = State()

def get_binary_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="0")
    builder.button(text="1")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я бот сервиса PsyPharmPredict.\n\n"
        "Я помогу тебе рассчитать риски побочных эффектов.\n"
        "Используй /predict чтобы начать анкетирование."
    )

@router.message(Command("predict"))
async def cmd_predict(message: types.Message, state: FSMContext):
    await message.answer("Шаг 1/7: Введите возраст пациента (число):")
    await state.set_state(PredictForm.age)

@router.message(PredictForm.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = float(message.text.replace(",", "."))
        await state.update_data(age=age)
        await message.answer("Шаг 2/7: ВНН/ПП (выберите 0 или 1):", reply_markup=get_binary_keyboard())
        await state.set_state(PredictForm.vnn_pp)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для возраста.")

@router.message(PredictForm.vnn_pp)
async def process_vnn(message: types.Message, state: FSMContext):
    if message.text not in ["0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки 0 или 1.")
    await state.update_data(vnn_pp=int(message.text))
    await message.answer("Шаг 3/7: Клозапин (выберите 0 или 1):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.clozapine)

@router.message(PredictForm.clozapine)
async def process_clozapine(message: types.Message, state: FSMContext):
    if message.text not in ["0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки 0 или 1.")
    await state.update_data(clozapine=int(message.text))
    await message.answer("Шаг 4/7: Генетический маркер CYP2C19 1/2 (0 или 1):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2c19_1_2)

@router.message(PredictForm.cyp2c19_1_2)
async def process_cyp1(message: types.Message, state: FSMContext):
    if message.text not in ["0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки 0 или 1.")
    await state.update_data(cyp2c19_1_2=int(message.text))
    await message.answer("Шаг 5/7: Генетический маркер CYP2C19 1/17 (0 или 1):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2c19_1_17)

@router.message(PredictForm.cyp2c19_1_17)
async def process_cyp2(message: types.Message, state: FSMContext):
    if message.text not in ["0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки 0 или 1.")
    await state.update_data(cyp2c19_1_17=int(message.text))
    await message.answer("Шаг 6/7: Генетический маркер CYP2C19 *17/*17 (0 или 1):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2c19_17_17)

@router.message(PredictForm.cyp2c19_17_17)
async def process_cyp3(message: types.Message, state: FSMContext):
    if message.text not in ["0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки 0 или 1.")
    await state.update_data(cyp2c19_17_17=int(message.text))
    await message.answer("Шаг 7/7: Генетический маркер CYP2D6 1/3 (0 или 1):", reply_markup=get_binary_keyboard())
    await state.set_state(PredictForm.cyp2d6_1_3)

async def get_bot_token():
    """Получает JWT-токен для бота, используя демо-данные."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.api_url}/api/v1/users/login",
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
    if message.text not in ["0", "1"]:
        return await message.answer("Пожалуйста, используйте кнопки 0 или 1.")

    data = await state.get_data()
    data['cyp2d6_1_3'] = int(message.text)

    await message.answer("Обработка данных, пожалуйста, подождите...", reply_markup=types.ReplyKeyboardRemove())

    try:
        # 1. Получаем токен
        token = await get_bot_token()
        if not token:
            return await message.answer("Ошибка авторизации в сервисе. Попробуйте позже.")

        # 2. Подготавливаем данные для API
        payload = {
            "data": [{
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
                f"{settings.api_url}/api/v1/requests/predict",
                json=payload,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                result = response.json()
                prediction = result["predictions"][0]
                await message.answer(f"Результат предсказания:\n\n{prediction}")
            else:
                error_detail = response.json().get("message", "Неизвестная ошибка")
                await message.answer(f"Ошибка API: {error_detail}")

    except Exception as e:
        logger.error(f"Ошибка в боте: {e}")
        await message.answer("Произошла ошибка при обращении к сервису.")
    finally:
        await state.clear()
