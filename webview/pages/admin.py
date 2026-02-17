import streamlit as st
import pandas as pd
from app.models import UserRole
from webview.core.config import ICONS
from webview.core.utils import transactions_to_df
from webview.services.state import handle_api_error

def render_admin(api):
    st.markdown(f"### {ICONS['admin']} Панель администратора")

    admin_tabs = st.tabs(["👥 Пользователи", "⚖️ Модерация", "💰 Пополнение", "📊 Все транзакции"])

    # 1. ПОЛЬЗОВАТЕЛИ
    with admin_tabs[0]:
        st.markdown("#### Список всех пользователей")
        try:
            with st.spinner("Загрузка пользователей..."):
                users = api.get_all_users()
            if users:
                # Поиск
                q = st.text_input("Поиск по Email или ID", placeholder="Введите email или ID")
                filtered = users
                if q:
                    q_lower = str(q).strip().lower()
                    def _match(u: dict) -> bool:
                        email = str(u.get("email", "")).lower()
                        uid = str(u.get("id", ""))
                        return (q_lower in email) or (q_lower == uid) or (q_lower in uid)
                    filtered = [u for u in users if _match(u)]

                df = pd.DataFrame(filtered)
                if not df.empty and "created_at" in df.columns:
                    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

                display_cols = [c for c in ["id", "email", "first_name", "last_name", "balance", "role", "created_at"] if c in df.columns]
                st.dataframe(df[display_cols] if not df.empty else df, width='stretch', hide_index=True)
                st.caption(f"Пользователей: {len(filtered)} / всего {len(users)}")

                # Выбор пользователя и детальная панель
                selected_user = st.selectbox(
                    "Управление пользователем",
                    options=[None] + filtered,
                    format_func=lambda u: f"{u.get('email', '')} (ID: {u.get('id')})" if u else "-- Выберите пользователя --",
                    index=0
                )

                if selected_user:
                    user_id = selected_user["id"]
                    user_data = selected_user

                    if user_data:
                        u_tabs = st.tabs(["📝 Профиль", "🤖 История предсказаний", "💳 Финансы"])

                        # 1) Профиль
                        with u_tabs[0]:
                            with st.form(f"edit_user_{user_id}"):
                                c1, c2 = st.columns(2)
                                with c1:
                                    first_name = st.text_input("Имя", value=user_data.get("first_name", ""))
                                    phone_number = st.text_input("Телефон", value=user_data.get("phone_number", ""))
                                with c2:
                                    last_name = st.text_input("Фамилия", value=user_data.get("last_name", ""))
                                    role_options = [r.value for r in UserRole]
                                    current_role = user_data.get("role", "user")
                                    role_index = role_options.index(current_role) if current_role in role_options else 0
                                    role = st.selectbox("Роль", options=role_options, index=role_index)

                                submitted = st.form_submit_button("Сохранить изменения", width='stretch')
                                if submitted:
                                    payload = {}
                                    if first_name != user_data.get("first_name"): payload["first_name"] = first_name
                                    if last_name != user_data.get("last_name"): payload["last_name"] = last_name
                                    if phone_number != user_data.get("phone_number"): payload["phone_number"] = phone_number
                                    if role != user_data.get("role"): payload["role"] = role
                                    try:
                                        if payload:
                                            api.update_user_data(user_id, payload)
                                            st.success("Данные пользователя обновлены")
                                            st.rerun()
                                        else:
                                            st.info("Нет изменений для сохранения")
                                    except Exception as e:
                                        handle_api_error(e)

                        # 2) История предсказаний
                        with u_tabs[1]:
                            st.markdown("История предсказаний")
                            try:
                                with st.spinner("Загрузка истории ML..."):
                                    history = api.get_user_ml_requests(user_id)
                                if history:
                                    hdf = pd.DataFrame(history)
                                    if "created_at" in hdf.columns:
                                        hdf["created_at"] = pd.to_datetime(hdf["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

                                    def _map_status(s: str) -> str:
                                        ls = str(s).lower()
                                        if "success" in ls:
                                            return "✅ success"
                                        if "fail" in ls:
                                            return "❌ fail"
                                        return "⏳ pending"

                                    if "status" in hdf.columns:
                                        hdf["status"] = hdf["status"].apply(_map_status)

                                    display = [c for c in ["id", "model_id", "cost", "status", "created_at"] if c in hdf.columns]
                                    st.dataframe(hdf[display] if display else hdf, width='stretch', hide_index=True)
                                else:
                                    st.info("История отсутствует")
                            except Exception as e:
                                handle_api_error(e)

                        # 3) Финансы
                        with u_tabs[2]:
                            st.markdown("Финансы пользователя")
                            try:
                                with st.spinner("Загрузка транзакций..."):
                                    user_tx = api.get_user_transactions(user_id)
                                if user_tx:
                                    tx_df = transactions_to_df(user_tx)
                                    st.dataframe(tx_df, width='stretch', hide_index=True)
                                else:
                                    st.info("Нет транзакций для пользователя")

                                st.divider()
                                st.markdown("Быстрое пополнение")
                                with st.form(f"replenish_{user_id}"):
                                    amount = st.number_input("Сумма пополнения", min_value=0.0, step=10.0, value=100.0, key=f"repl_amt_{user_id}")
                                    if st.form_submit_button("Пополнить", width='stretch'):
                                        try:
                                            api.update_user_balance(user_id, amount)
                                            st.success(f"Баланс пополнен на {amount}")
                                            st.rerun()
                                        except Exception as e:
                                            handle_api_error(e)
                            except Exception as e:
                                handle_api_error(e)
                else:
                    st.info("Выберите пользователя для управления")
            else:
                st.info("Пользователей нет")
        except Exception as e:
            handle_api_error(e)

    # 2. МОДЕРАЦИЯ
    with admin_tabs[1]:
        st.markdown("#### Ожидающие пополнения")
        try:
            with st.spinner("Загрузка транзакций..."):
                all_tx = api.get_all_transactions()

            pending_tx = [tx for tx in all_tx if str(tx.get("status", "")).lower() == "pending"]

            if not pending_tx:
                st.success("Нет транзакций, ожидающих модерации")
            else:
                for tx in pending_tx:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2, 1, 1])
                        with c1:
                            st.markdown(f"**ID:** `{tx['id']}` | **User ID:** `{tx['user_id']}`")
                            st.markdown(f"**Сумма:** `{tx['amount']}` кредитов")
                            st.caption(f"Дата: {tx.get('created_at', '')}")

                        with c2:
                            if st.button("✅ Одобрить", key=f"appr_{tx['id']}", width='stretch'):
                                api.approve_transaction(tx['id'])
                                st.success(f"Транзакция {tx['id']} одобрена")
                                st.rerun()

                        with c3:
                            if st.button("❌ Отклонить", key=f"rejl_{tx['id']}", width='stretch', type="secondary"):
                                api.reject_transaction(tx['id'])
                                st.warning(f"Транзакция {tx['id']} отклонена")
                                st.rerun()
        except Exception as e:
            handle_api_error(e)

    # 3. ПОПОЛНЕНИЕ (Прямое)
    with admin_tabs[2]:
        st.markdown("#### Прямое пополнение баланса")
        st.info("Используйте это поле для ручной корректировки баланса пользователя (без создания запроса от пользователя).")

        with st.form("admin_replenish_form"):
            user_id = st.number_input("ID пользователя", min_value=1, step=1)
            amount = st.number_input("Сумма пополнения", min_value=0.0, step=10.0, value=100.0)

            if st.form_submit_button("Пополнить баланс", width='stretch'):
                try:
                    api.update_user_balance(int(user_id), amount)
                    st.success(f"{ICONS['success']} Баланс пользователя #{user_id} пополнен на {amount} кредитов")
                except Exception as e:
                    handle_api_error(e)

    # 4. ТРАНЗАКЦИИ
    with admin_tabs[3]:
        st.markdown("#### Все транзакции в системе")
        try:
            with st.spinner("Загрузка истории..."):
                all_tx = api.get_all_transactions()
            if all_tx:
                df = transactions_to_df(all_tx)
                # Добавим User ID в таблицу, так как это админ-панель
                raw_df = pd.DataFrame(all_tx)
                if "user_id" in raw_df.columns:
                    df["Пользователь ID"] = raw_df["user_id"]

                st.dataframe(df, width='stretch', hide_index=True)
            else:
                st.info("Транзакций пока нет")
        except Exception as e:
            handle_api_error(e)
