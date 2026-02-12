import streamlit as st
import pandas as pd
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
                df = pd.DataFrame(users)

                # Форматирование
                if "created_at" in df.columns:
                    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

                display_cols = [c for c in ["id", "email", "first_name", "last_name", "balance", "is_admin", "created_at"] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
                st.caption(f"Всего пользователей: {len(users)}")
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
                            if st.button("✅ Одобрить", key=f"appr_{tx['id']}", use_container_width=True):
                                api.approve_transaction(tx['id'])
                                st.success(f"Транзакция {tx['id']} одобрена")
                                st.rerun()

                        with c3:
                            if st.button("❌ Отклонить", key=f"rejl_{tx['id']}", use_container_width=True, type="secondary"):
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

            if st.form_submit_button("Пополнить баланс", use_container_width=True):
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

                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Транзакций пока нет")
        except Exception as e:
            handle_api_error(e)
