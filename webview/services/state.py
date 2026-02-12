from decimal import Decimal
import streamlit as st
from webview.services.api_client import APIClient, UnauthorizedError
from webview.services.logger import logger

DEFAULTS = {
    "api_url": None,
    "token": None,
    "me": None,
    "balance": None,
    "show_auth_modal": False,
    "api_health": None,
    "send_mode": "⏱️ В очередь (фоновый режим)",
    "use_confirmations": True,
    "page_size": 10,
    "show_ml_confirm": False,
    "show_balance_confirm": False,
    "ml_to_send": [],
    "ml_send_mode": "",
    "ml_est_cost": Decimal("0"),
    "balance_amount": 0.0,
    "ml_confirmed": False,
    "balance_confirmed": False,
    "_health_checked_once": False,
    "_app_started_logged": False,
}

def init_session_state(default_api_url: str) -> APIClient:
    """Инициализирует session_state и возвращает APIClient."""
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if not st.session_state._app_started_logged:
        logger.info("Application started (new session)")
        st.session_state._app_started_logged = True
    else:
        logger.debug("Session already initialized")

    if st.session_state.api_url is None:
        st.session_state.api_url = default_api_url

    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient(st.session_state.api_url)

    return st.session_state.api_client

def ensure_health_check(api: APIClient) -> None:
    """Выполняет проверку здоровья API один раз при запуске."""
    if st.session_state.get("api_health") is None and not st.session_state.get("_health_checked_once"):
        try:
            st.session_state.api_health = api.health_check()
        except Exception:
            st.session_state.api_health = {"status": "unknown"}
        finally:
            st.session_state._health_checked_once = True

def set_auth(token: str | None) -> None:
    """Устанавливает или сбрасывает токен авторизации."""
    st.session_state.token = token
    if token is None:
        logger.info("User logged out")
        st.session_state.me = None
        st.session_state.balance = None
    else:
        logger.info("User logged in (token set)")

def refresh_user_data(api: APIClient) -> None:
    """Обновляет данные профиля и баланс из API."""
    try:
        st.session_state.me = api.get_me()
        bal = api.check_balance()
        st.session_state.balance = Decimal(str(bal.get("balance", 0)))
    except Exception as e:
        handle_api_error(e)

def is_admin() -> bool:
    """Проверяет, является ли текущий пользователь администратором."""
    me = st.session_state.get("me", {})
    if not me:
        return False
    return me.get("is_admin", False) or me.get("role") == "admin"

def handle_api_error(e: Exception):
    """Централизованная обработка ошибок API."""
    if isinstance(e, UnauthorizedError):
        # APIClient уже сбросил состояние в session_state
        st.error("Сессия истекла. Пожалуйста, войдите снова.")
        st.rerun()
    else:
        st.error(f"Ошибка API: {e}")
