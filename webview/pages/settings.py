import streamlit as st
from webview.core.config import ICONS
from webview.services.state import refresh_user_data, handle_api_error


def render_settings(api):
    st.markdown(f"### {ICONS['settings']} Настройки профиля")

    me = st.session_state.get("me") or {}
    if not st.session_state.get("token"):
        st.info("Чтобы изменить данные профиля, пожалуйста, войдите в систему.")
        return

    # Текущие значения
    curr_first = me.get("first_name", "")
    curr_last = me.get("last_name", "")
    curr_phone = me.get("phone_number", "")
    email = me.get("email", "")
    role = me.get("role", "user")

    with st.container(border=True):
        col_title, col_refresh = st.columns([4, 1])
        with col_title:
            st.markdown("#### Текущая учетная запись")
        with col_refresh:
            if st.button("🔄 Обновить", use_container_width=True, help="Загрузить актуальные данные с сервера"):
                refresh_user_data(api)
                st.rerun()

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.text_input("Email", value=email, disabled=True)
        with col2:
            st.text_input("Роль", value=str(role), disabled=True)
        with col3:
            st.text_input("ID", value=str(me.get("id", "")), disabled=True)

    st.markdown("---")
    st.markdown("#### Обновление данных")

    with st.form("settings_form"):
        nf = st.text_input("Имя", value=curr_first)
        nl = st.text_input("Фамилия", value=curr_last)
        ph = st.text_input("Телефон", value=curr_phone, placeholder="+79991234567")

        submitted = st.form_submit_button("Сохранить изменения", use_container_width=True)

    if submitted:
        # Собираем только изменившиеся поля
        payload = {}
        if nf != curr_first:
            payload["first_name"] = nf.strip()
        if nl != curr_last:
            payload["last_name"] = nl.strip()
        if ph != curr_phone:
            payload["phone_number"] = ph.strip()

        if not payload:
            st.info("Изменений не обнаружено")
            return

        try:
            with st.spinner("Сохранение..."):
                api.update_me(payload)
            st.success("✅ Данные успешно обновлены")
            refresh_user_data(api)
            st.rerun()
        except Exception as e:
            handle_api_error(e)
