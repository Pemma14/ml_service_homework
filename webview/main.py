import os
import sys
from datetime import datetime
import streamlit as st

# Добавляем корень проекта в путь поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Локальные импорты
from webview.core.styles import apply_custom_styles
from webview.core.config import DEFAULT_API, ICONS
from webview.services.state import init_session_state, ensure_health_check, is_admin
from webview.components.auth import show_auth_dialog
from webview.components.layout import render_sidebar, render_header

# Импорт страниц
from webview.pages.home import render_home
from webview.pages.cabinet.overview import render_overview
from webview.pages.cabinet.balance import render_balance
from webview.pages.cabinet.ml_requests import render_ml_requests
from webview.pages.cabinet.history import render_history
from webview.pages.cabinet.feedback import render_feedback
from webview.pages.admin import render_admin
from webview.pages.api_docs import render_api_docs

# НАСТРОЙКА СТРАНИЦЫ
st.set_page_config(
    page_title="PsyPharmPredict",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_custom_styles()

# ИНИЦИАЛИЗАЦИЯ
api = init_session_state(DEFAULT_API)
ensure_health_check(api)

# РЕНДЕРИНГ UI

# Сайдбар
with st.sidebar:
    render_sidebar(api)

# Хедер
render_header(api)

# Модальное окно авторизации
if st.session_state.get("show_auth_modal") and not st.session_state.get("token"):
    def on_login_success():
        st.session_state.active_tab = "cabinet"

    show_auth_dialog(api, on_success=on_login_success)


# ОСНОВНОЙ КОНТЕНТ

active_tab = st.session_state.get("active_tab", "home")

# 1. Главная страница
if active_tab == "home":
    render_home()

# 2. Личный кабинет
elif active_tab == "cabinet":
    if not st.session_state.get("token"):
        st.info("👋 Добро пожаловать! Пожалуйста, войдите в систему, чтобы получить доступ к личному кабинету.")
        render_home() # Показываем главную, если не авторизован
    else:
        # Формируем список вкладок
        tabs_labels = [
            f"{ICONS['info']} Общая информация",
            f"{ICONS['balance']} Баланс",
            f"{ICONS['ml']} Предсказание",
            f"{ICONS['history']} История",
            f"{ICONS['feedback']} Обратная связь"
        ]

        # Если админ - добавляем админ-панель первой
        if is_admin():
            tabs_labels.insert(0, f"{ICONS['admin']} Админ-панель")

        sub_tabs = st.tabs(tabs_labels)

        if is_admin():
            admin_tab, info_tab, balance_tab, ml_tab, history_tab, feedback_tab = sub_tabs
            with admin_tab:
                render_admin(api)
        else:
            info_tab, balance_tab, ml_tab, history_tab, feedback_tab = sub_tabs

        with info_tab:
            render_overview(api)
        with balance_tab:
            render_balance(api)
        with ml_tab:
            render_ml_requests(api)
        with history_tab:
            render_history(api)
        with feedback_tab:
            render_feedback(api)

# 3. REST API
elif active_tab == "api":
    render_api_docs(st.session_state.api_url)

# Футер
st.markdown("---")
col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    st.caption(f"© 2026 PsyPharmPredict | Powered by Streamlit")
with col_f2:
    st.caption(f"✨ Последнее обновление кода: {datetime.now().strftime('%H:%M:%S')}")

if "update_notified" not in st.session_state:
    st.toast("🚀 Интерфейс обновлен!", icon="✨")
    st.session_state.update_notified = True
