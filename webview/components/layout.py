import streamlit as st
from webview.core.config import ICONS
from webview.services.state import is_admin, refresh_user_data, set_auth, handle_api_error
from webview.core.utils import is_valid_url

#САЙДБАР
def render_sidebar(api):
    # Навигация
    if st.button(f"{ICONS['home']} Главная", use_container_width=True, key="sidebar_home"):
        st.session_state.active_tab = "home"
        st.rerun()

    if st.session_state.get("token"):
        if st.button(f"{ICONS['user']} Личный кабинет", use_container_width=True, key="sidebar_cabinet"):
            st.session_state.active_tab = "cabinet"
            st.rerun()

    if st.session_state.get("token"):
        if st.button(f"{ICONS['settings']} Настройки", use_container_width=True, key="sidebar_settings"):
            st.session_state.active_tab = "settings"
            st.rerun()

    # Профиль пользователя
    if st.session_state.get("token"):
        st.markdown("---")
        st.markdown(f"### {ICONS['user']} Профиль")

        if st.session_state.me:
            email = st.session_state.me.get("email", "")
            first_name = st.session_state.me.get("first_name", "")
            last_name = st.session_state.me.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip() or email

            st.markdown(f"**Пользователь:** {full_name}")
            st.caption(f"📧 {email}")

            if is_admin():
                st.success("👑 Администратор")

        if st.session_state.balance is not None:
            st.markdown(f"**{ICONS['balance']} Баланс:** {st.session_state.balance} кредитов")

        if st.button("🔄 Обновить данные", use_container_width=True, key="sidebar_refresh"):
            with st.spinner("Обновление..."):
                refresh_user_data(api)
            st.rerun()

    # Настройки приложения
    with st.sidebar.expander(f"{ICONS['settings']} Настройки интерфейса", expanded=False):
        st.session_state.use_confirmations = st.toggle(
            "Подтверждение операций",
            value=st.session_state.use_confirmations,
            help="Показывать окна подтверждения перед пополнением баланса или отправкой запросов"
        )

        st.session_state.send_mode = st.radio(
            "Способ обработки ML",
            ["⏱️ В очередь (фоновый режим)", "⚡ Прямой ответ (ожидание)"],
            index=0 if st.session_state.send_mode.startswith("⏱️") else 1,
            help="Глобальная настройка способа обработки запросов"
        )

        st.session_state.page_size = st.select_slider(
            "Записей на страницу",
            options=[5, 10, 20, 50],
            value=st.session_state.page_size
        )

    # Технические настройки
    with st.sidebar.expander(f"{ICONS['admin']} Технические настройки", expanded=False):
        if st.button(f"{ICONS['info']} Документация REST API", use_container_width=True):
            st.session_state.active_tab = "api"
            st.rerun()

        st.markdown("---")
        new_api_url = st.text_input(
            "API URL",
            value=st.session_state.api_url,
            help="Базовый URL для API",
            key="sidebar_api_url"
        )
        st.caption(f"Текущий клиент: {api.base_url}")
        if st.button("Применить API URL", use_container_width=True):
            if not is_valid_url(new_api_url):
                st.error(f"{ICONS['error']} Некорректный формат URL. Используйте формат: http://example.com или https://example.com:8000")
            else:
                st.session_state.api_url = new_api_url
                st.session_state.api_client = type(api)(new_api_url)
                st.session_state.api_health = None
                st.success("Новый API URL применён")
                st.rerun()

        # Health check
        if st.button("Проверить состояние API", use_container_width=True, key="sidebar_health_check"):
            try:
                with st.spinner("Проверка состояния API..."):
                    health = api.health_check()
                st.session_state.api_health = health
                status = health.get("status", "unknown")
                if status == "ok":
                    st.success(f"{ICONS['success']} API работает нормально")
                elif status == "degraded":
                    st.warning(f"{ICONS['warning']} API работает с ограничениями")
                else:
                    st.error(f"{ICONS['error']} API недоступен")
                st.json(health)
            except Exception as e:
                handle_api_error(e)

#ХЕДЕР
def render_header(api):
    # Определение доступных вкладок
    tabs = []

    # Инициализация активной вкладки
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "home"

    # Хедер
    with st.container(key="header-container"):
        # Динамический расчет весов для кнопок: Лого, Спейсер, Вкладки..., Профиль/Логин
        logo_weight = 2.5
        spacer_weight = 28.0

        # Веса для вкладок
        tab_weights = [1.2 for t in tabs]

        # Вес для кнопки авторизации/профиля
        auth_weight = 2.5

        weights = [logo_weight, spacer_weight] + tab_weights + [auth_weight]
        cols = st.columns(weights, vertical_alignment="center", gap="small")

        with cols[0]:
            st.markdown('<div class="header-item"></div>', unsafe_allow_html=True)
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 0.8rem;">
                    <span style="font-size: 3.0rem;">🧠</span>
                    <div class="header-logo">PsyPharmPredict</div>
                </div>
            """, unsafe_allow_html=True)

        # cols[1] - spacer

        # Навигационные кнопки
        for i, tab in enumerate(tabs):
            with cols[i + 2]:
                is_active = st.session_state.get("active_tab") == tab["id"]
                active_class = "header-item-active" if is_active else ""
                st.markdown(f'<div class="header-item {active_class}">', unsafe_allow_html=True)
                if st.button(tab["label"], key=f"header_btn_{tab['id']}"):
                    st.session_state.active_tab = tab["id"]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Кнопка профиля / логина
        with cols[-1]:
            st.markdown('<div class="header-item"></div>', unsafe_allow_html=True)
            if st.session_state.get("token") and st.session_state.get("me"):
                email = st.session_state.me.get("email", "user")
                username = email.split('@')[0]
                if len(username) > 12:
                    username = username[:10] + "..."

                with st.popover(f"👤"):
                    st.markdown(f"👤 **{email}**")
                    if st.session_state.balance is not None:
                        st.markdown(f"💰 **Баланс:** `{st.session_state.balance}` кр.")
                    st.markdown("---")
                    if st.button("Выйти", use_container_width=True, key="header_logout"):
                        set_auth(None)
                        st.session_state.active_tab = "home"
                        st.rerun()
            else:
                if st.button("Войти", key="header_login"):
                    st.session_state.show_auth_modal = True
                    st.rerun()
