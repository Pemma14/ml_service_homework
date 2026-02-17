import streamlit as st

from webview.core.config import ICONS
from webview.core.styles import COLORS
from webview.services.state import refresh_user_data, handle_api_error


@st.dialog("💳 Подтверждение пополнения")
def confirm_replenishment_dialog(api, amount):
    st.markdown(f"Вы собираетесь пополнить баланс на **{amount:.0f}** кредитов.")
    st.info("Пожалуйста, подтвердите операцию. Средства будут зачислены после нажатия кнопки.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Подтвердить", use_container_width=True, key="balance_confirm_btn_dialog"):
            st.session_state.balance_confirmed = True
            st.session_state.show_balance_confirm = False
            st.session_state.balance_amount = amount
            st.rerun()
    with col2:
        if st.button("❌ Отмена", use_container_width=True, key="balance_cancel_btn_dialog"):
            st.session_state.show_balance_confirm = False
            st.rerun()

def render_balance(api):
    # Обработка подтвержденного пополнения
    if st.session_state.get("balance_confirmed"):
        st.session_state.balance_confirmed = False
        amount = st.session_state.get("balance_amount", 0)
        try:
            st.toast("💳 Выполнение пополнения...")
            with st.spinner("Пополнение..."):
                api.replenish_balance(amount)
            st.success(f"{ICONS['success']} Баланс успешно пополнен!")
            st.session_state.last_input = 0
            refresh_user_data(api)
            st.rerun()
        except Exception as e:
            handle_api_error(e)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 💰 Текущий баланс")

        if st.session_state.balance is not None:
            st.markdown(f"""
            <div class="custom-card" style="min-height: 200px; display: flex; flex-direction: column; justify-content: center;">
                <h1 style="color: {COLORS['primary']}; margin: 0; line-height: 1.2;">
                    {st.session_state.balance}
                </h1>
                <p style="color: {COLORS['text_secondary']}; margin-top: 0.5rem; margin-bottom: 0;">
                    кредитов
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Баланс недоступен")

    with col2:
        st.markdown("### 💳 Пополнить баланс")
        with st.form("replenish_form", clear_on_submit=True):
            amount = st.number_input(
                "Сумма пополнения",
                min_value=0.0,
                max_value=50000.0,
                step=1.0,
                value=0.0,
                format="%.0f",
                help="Укажите сумму для пополнения"
            )
            submitted = st.form_submit_button("Пополнить", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("Сумма пополнения должна быть больше 0")
            else:
                st.session_state.last_input = amount
                # Открываем диалог только при нажатии кнопки и корректной сумме
                confirm_replenishment_dialog(api, amount)
