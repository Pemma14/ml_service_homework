from typing import Dict, Any

import requests
import streamlit as st
from webview.services.logger import logger
from webview.core.config import API_TIMEOUT, API_HEALTH_TIMEOUT


class APIError(Exception):
    """Базовая ошибка API."""
    def __init__(self, message: str, status_code: int | None = None, data: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.data = data


class UnauthorizedError(APIError):
    """Ошибка 401 — неавторизован."""
    pass


class APIClient:
    """Клиент для работы с ML Service API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        """Формирует заголовки для запросов."""
        h = {"Content-Type": "application/json"}
        if st.session_state.get("token"):
            h["Authorization"] = f"Bearer {st.session_state.token}"
        return h

    def _handle_error(self, response: requests.Response):
        """Обрабатывает ошибки от API: парсит ответ и выбрасывает исключение."""
        if response.ok:
            return
        status = response.status_code
        message = response.text
        data: Any | None = None
        try:
            data = response.json()
            # Часто useful сообщения находятся в полях message/detail
            msg = data.get("message") or data.get("detail") or data
            message = str(msg)
        except Exception:
            # Оставляем text, если json не распарсился
            pass

        # Логируем ошибку
        logger.error(f"API Error: {status} - {message}", path=response.request.path_url)

        if status == 401:
            # Автоматически сбрасываем состояние авторизации
            st.session_state.token = None
            st.session_state.me = None
            st.session_state.balance = None
            st.session_state.show_auth_modal = True
            raise UnauthorizedError(message, status_code=status, data=data)
        raise APIError(message, status_code=status, data=data)

    def post(self, path: str, payload: dict, timeout: int | None = None) -> dict:
        """Выполняет POST запрос."""
        url = self.base_url + path
        logger.debug(f"API POST Request: {url}", payload=payload)
        t = timeout or API_TIMEOUT
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=t)
        logger.debug(f"API POST Response: {resp.status_code}")
        self._handle_error(resp)
        return resp.json()

    def get(self, path: str) -> dict:
        """Выполняет GET запрос."""
        url = self.base_url + path
        logger.debug(f"API GET Request: {url}")
        resp = requests.get(url, headers=self._headers(), timeout=API_TIMEOUT)
        logger.debug(f"API GET Response: {resp.status_code}")
        self._handle_error(resp)
        return resp.json()

    # === Auth endpoints ===
    def login(self, email: str, password: str) -> dict:
        """Авторизация пользователя."""
        return self.post("/api/v1/users/login", {"email": email, "password": password})

    def register(self, email: str, password: str, first_name: str, last_name: str, phone_number: str) -> dict:
        """Регистрация нового пользователя."""
        return self.post("/api/v1/users/register", {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
        })

    def get_me(self) -> dict:
        """Получает информацию о текущем пользователе."""
        return self.get("/api/v1/users/me")

    # === Balance endpoints ===
    def check_balance(self) -> dict:
        """Проверяет текущий баланс."""
        return self.get("/api/v1/balance/check_balance")

    def replenish_balance(self, amount: float) -> dict:
        """Пополняет баланс."""
        return self.post("/api/v1/balance/replenish", {"amount": amount})

    def get_balance_history(self) -> list:
        """Получает историю транзакций."""
        return self.get("/api/v1/balance/history")

    # === ML Request endpoints ===
    def send_task(self, data: list) -> dict:
        """Отправляет задачу в очередь (асинхронно)."""
        return self.post("/api/v1/requests/send_task", {"data": data})

    def send_task_rpc(self, data: list) -> dict:
        """Отправляет задачу через RPC (синхронно)."""
        # Динамический таймаут для RPC: базовые 20с + 0.3с на строку (чуть больше, чем в бэкенде)
        num_rows = len(data) if isinstance(data, list) else 1
        dynamic_timeout = max(30, 20 + int(num_rows * 0.3))
        return self.post("/api/v1/requests/send_task_rpc", {"data": data}, timeout=dynamic_timeout)

    def get_request_history(self) -> list:
        """Получает историю ML-запросов."""
        return self.get("/api/v1/requests/history")

    def get_request_details(self, request_id: int) -> dict:
        """Получает детали конкретного запроса."""
        return self.get(f"/api/v1/requests/history/{request_id}")

    # === Admin endpoints ===
    def get_all_users(self) -> list:
        """Получает список всех пользователей (только для админа)."""
        return self.get("/api/v1/users/all")

    def update_user_balance(self, user_id: int, amount: float) -> dict:
        """Обновляет баланс пользователя (только для админа)."""
        return self.post(f"/api/v1/balance/admin/replenish/{user_id}", {"amount": amount})

    def get_all_transactions(self) -> list:
        """Получает список всех транзакций в системе (только для админа)."""
        return self.get("/api/v1/balance/admin/all")

    def approve_transaction(self, transaction_id: int) -> dict:
        """Одобряет транзакцию (только для админа)."""
        return self.post(f"/api/v1/balance/admin/approve/{transaction_id}", {})

    def reject_transaction(self, transaction_id: int) -> dict:
        """Отклоняет транзакцию (только для админа)."""
        return self.post(f"/api/v1/balance/admin/reject/{transaction_id}", {})

    # === Health check ===
    def health_check(self) -> dict:
        """Проверяет состояние сервиса c небольшим таймаутом, не инициируя авторизацию."""
        url = self.base_url + "/health"
        try:
            # Используем нейтральные заголовки, чтобы случайно не затриггерить 401-логику
            resp = requests.get(url, headers={"Content-Type": "application/json"}, timeout=API_HEALTH_TIMEOUT)
            if resp.ok:
                return resp.json()
            # Не провоцируем показ модалки логина при неуспешном health
            return {"status": "unknown", "code": resp.status_code}
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return {"status": "unknown", "error": str(e)}
