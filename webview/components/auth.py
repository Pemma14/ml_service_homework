import streamlit as st
from webview.services.state import refresh_user_data, set_auth

@st.dialog("Вход или регистрация", width="large")
def show_auth_dialog(api, on_success=lambda: None):
    tab_login, tab_register = st.tabs(["Вход", "Регистрация"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="user@example.com")
            password = st.text_input("Пароль", type="password")

            if st.form_submit_button("Войти", use_container_width=True):
                try:
                    data = api.login(email, password)
                    set_auth(data.get("access_token"))
                    refresh_user_data(api)
                    st.session_state.show_auth_modal = False
                    on_success()
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка входа: {e}")

    with tab_register:
        with st.form("register_form"):
            r_email = st.text_input("Email", placeholder="user@example.com", key="reg_email")
            r_first = st.text_input("Имя")
            r_last = st.text_input("Фамилия")
            r_phone = st.text_input("Телефон", placeholder="+79990000000")
            r_pwd1 = st.text_input("Пароль", type="password")
            r_pwd2 = st.text_input("Повторите пароль", type="password")

            if st.form_submit_button("Зарегистрироваться", use_container_width=True):
                if r_pwd1 != r_pwd2:
                    st.error("Пароли не совпадают!")
                else:
                    try:
                        api.register(r_email, r_pwd1, r_first, r_last, r_phone)
                        st.success("Регистрация успешна! Теперь войдите.")
                    except Exception as e:
                        st.error(f"Ошибка регистрации: {e}")
