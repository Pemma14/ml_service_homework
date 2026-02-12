import os
from decimal import Decimal

# API Configuration
DEFAULT_API = os.getenv("API_BASE_URL", "http://localhost")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))  # seconds
API_HEALTH_TIMEOUT = int(os.getenv("API_HEALTH_TIMEOUT", "5"))  # seconds

# Cost Configuration
EXPECTED_REQUEST_COST = Decimal("10.0")

# Validation Configuration
MAX_AGE = 150
MIN_AGE = 0

# Mapping для русских названий полей
ALIAS_MAP = {
    "age": "Возраст",
    "vnn_pp": "ВНН/ПП",
    "clozapine": "Клозапин",
    "cyp2c19_1_2": "CYP2C19 1/2",
    "cyp2c19_1_17": "CYP2C19 1/17",
    "cyp2c19_17_17": "CYP2C19 *17/*17",
    "cyp2d6_1_3": "CYP2D6 1/3",
}

# Синонимы для умного поиска колонок (в нижнем регистре)
SYNONYMS_MAP = {
    "Возраст": ["age", "возраст", "лет", "age_years", "пациент_возраст"],
    "ВНН/ПП": ["vnn_pp", "внн", "пп", "vnn/pp", "vnn", "pp"],
    "Клозапин": ["clozapine", "клозапин", "clozapin"],
    "CYP2C19 1/2": ["cyp2c19_1_2", "cyp2c19 1/2", "2c19 1/2", "1/2", "cyp2c19 *1/*2", "*1/*2"],
    "CYP2C19 1/17": ["cyp2c19_1_17", "cyp2c19 1/17", "2c19 1/17", "1/17", "cyp2c19 *1/*17", "*1/*17"],
    "CYP2C19 *17/*17": ["cyp2c19_17_17", "cyp2c19 *17/*17", "cyp2c19 17/17", "17/17"],
    "CYP2D6 1/3": ["cyp2d6_1_3", "cyp2d6 1/3", "2d6 1/3", "1/3", "cyp2d6 *1/*3", "*1/*3"],
}

REQUIRED_ALIAS_ORDER = [
    "Возраст",
    "ВНН/ПП",
    "Клозапин",
    "CYP2C19 1/2",
    "CYP2C19 1/17",
    "CYP2C19 *17/*17",
    "CYP2D6 1/3",
]

# UI Configuration
ICONS = {
    "home": "🏠",
    "user": "👤",
    "balance": "💰",
    "ml": "🤖",
    "history": "📊",
    "admin": "🔧",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "pending": "⏳",
    "info": "ℹ️",
    "chart": "📈",
    "settings": "⚙️",
}

# Status mapping
STATUS_MAP = {
    "success": {"label": "Успех", "color": "success", "icon": "🟢"},
    "completed": {"label": "Завершено", "color": "success", "icon": "🟢"},
    "done": {"label": "Готово", "color": "success", "icon": "🟢"},
    "pending": {"label": "В ожидании", "color": "warning", "icon": "🟡"},
    "processing": {"label": "В обработке", "color": "warning", "icon": "🟡"},
    "in_progress": {"label": "В процессе", "color": "warning", "icon": "🟡"},
    "fail": {"label": "Ошибка", "color": "error", "icon": "🔴"},
    "error": {"label": "Ошибка", "color": "error", "icon": "🔴"},
    "failed": {"label": "Не удалось", "color": "error", "icon": "🔴"},
}
