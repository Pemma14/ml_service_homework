import streamlit as st
import pandas as pd
from app.models import UserRole
from webview.core.config import ICONS
from webview.core.utils import transactions_to_df, requests_to_df
from webview.services.state import handle_api_error
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, ColumnsAutoSizeMode

def render_admin(api):
    st.markdown(f"### {ICONS['admin']} Панель администратора")

    admin_tabs = st.tabs(["👥 Пользователи", "🤖 Все предсказания", "💰 Пополнение", "📊 Все транзакции"])

    # 1. ПОЛЬЗОВАТЕЛИ
    with admin_tabs[0]:
        st.markdown("#### Список всех пользователей")
        try:
            with st.spinner("Загрузка пользователей..."):
                users = api.get_all_users()
            if users:
                df = pd.DataFrame(users)
                if not df.empty and "created_at" in df.columns:
                    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

                display_cols = [c for c in ["id", "email", "first_name", "last_name", "balance", "role", "created_at"] if c in df.columns]
                df_display = df[display_cols] if not df.empty else df

                page_size = st.session_state.get("page_size", 10)
                gb = GridOptionsBuilder.from_dataframe(df_display)
                gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)
                # Узкие фиксированные колонки
                if "id" in df_display.columns:
                    gb.configure_column("id", header_name="ID", width=80, flex=0)
                if "created_at" in df_display.columns:
                    gb.configure_column("created_at", header_name="Дата", width=120, flex=0)
                if "role" in df_display.columns:
                    gb.configure_column("role", header_name="Роль", width=100, flex=0)
                if "balance" in df_display.columns:
                    gb.configure_column("balance", header_name="Баланс", width=110, flex=0)
                # Остальные
                if "email" in df_display.columns:
                    gb.configure_column("email", header_name="Email", minWidth=200, flex=2, wrapText=True, autoHeight=True)
                if "first_name" in df_display.columns:
                    gb.configure_column("first_name", header_name="Имя", minWidth=120, flex=1)
                if "last_name" in df_display.columns:
                    gb.configure_column("last_name", header_name="Фамилия", minWidth=120, flex=1)

                gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
                gb.configure_grid_options(domLayout='autoHeight')
                grid_options = gb.build()
                AgGrid(
                    df_display,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    theme='streamlit',
                    use_container_width=True,
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW
                )
                st.caption(f"Всего пользователей: {len(users)}")

                # Выбор пользователя и детальная панель
                selected_user = st.selectbox(
                    "Управление пользователем",
                    options=[None] + users,
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
                                    df_display = hdf[display] if display else hdf

                                    page_size = st.session_state.get("page_size", 10)
                                    gb = GridOptionsBuilder.from_dataframe(df_display)
                                    gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)
                                    if "id" in df_display.columns:
                                        gb.configure_column("id", header_name="ID", width=80, flex=0)
                                    if "created_at" in df_display.columns:
                                        gb.configure_column("created_at", header_name="Дата", width=120, flex=0)
                                    if "cost" in df_display.columns:
                                        gb.configure_column("cost", header_name="Списание", width=100, flex=0)
                                    if "model_id" in df_display.columns:
                                        gb.configure_column("model_id", header_name="Модель", minWidth=120, flex=1)
                                    if "status" in df_display.columns:
                                        gb.configure_column("status", header_name="Статус", minWidth=120, flex=1)
                                    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
                                    gb.configure_grid_options(domLayout='autoHeight')
                                    grid_options = gb.build()
                                    AgGrid(
                                        df_display,
                                        gridOptions=grid_options,
                                        update_mode=GridUpdateMode.MODEL_CHANGED,
                                        theme='streamlit',
                                        use_container_width=True,
                                        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW
                                    )
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
                                    page_size = st.session_state.get("page_size", 10)
                                    gb = GridOptionsBuilder.from_dataframe(tx_df)
                                    gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)
                                    # Настройка колонок
                                    for col, cfg in {
                                        "ID": {"width": 80, "flex": 0},
                                        "Дата": {"width": 120, "flex": 0},
                                        "Статус": {"width": 120, "flex": 0},
                                        "Тип": {"minWidth": 150, "flex": 1},
                                        "Сумма": {"width": 100, "flex": 0},
                                    }.items():
                                        if col in tx_df.columns:
                                            gb.configure_column(col, **cfg)
                                    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
                                    gb.configure_grid_options(domLayout='autoHeight')
                                    grid_options = gb.build()
                                    AgGrid(
                                        tx_df,
                                        gridOptions=grid_options,
                                        update_mode=GridUpdateMode.MODEL_CHANGED,
                                        theme='streamlit',
                                        use_container_width=True,
                                        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW
                                    )
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

    # 2. Все предсказания
    with admin_tabs[1]:
        st.markdown("#### Все предсказания в системе")
        try:
            with st.spinner("Загрузка всех ML-запросов..."):
                all_reqs = api.get_all_ml_requests()
            if all_reqs:
                hdf = requests_to_df(all_reqs)
                # Добавим User ID в таблицу, так как это админ-панель
                raw_df = pd.DataFrame(all_reqs)
                if not raw_df.empty and "user_id" in raw_df.columns:
                    hdf["Пользователь ID"] = raw_df["user_id"]

                page_size = st.session_state.get("page_size", 10)
                gb = GridOptionsBuilder.from_dataframe(hdf)
                gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)
                # Узкие колонки
                for col, cfg in {
                    "ID": {"width": 80, "flex": 0},
                    "Дата": {"width": 120, "flex": 0},
                    "Статус": {"width": 120, "flex": 0},
                    "Списание": {"width": 100, "flex": 0},
                    "Пользователь ID": {"width": 120, "flex": 0},
                }.items():
                    if col in hdf.columns:
                        gb.configure_column(col, **cfg)
                # Длинные колонки с переносом
                if "Модель" in hdf.columns:
                    gb.configure_column("Модель", minWidth=150, flex=1, wrapText=True, autoHeight=True)
                if "Предсказание" in hdf.columns:
                    gb.configure_column("Предсказание", minWidth=200, flex=2, wrapText=True, autoHeight=True)

                gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
                gb.configure_grid_options(domLayout='autoHeight')
                grid_options = gb.build()
                AgGrid(
                    hdf,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    theme='streamlit',
                    use_container_width=True,
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW
                )
            else:
                st.info("Предсказаний пока нет")
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

                page_size = st.session_state.get("page_size", 10)
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)
                # Настройка колонок
                for col, cfg in {
                    "ID": {"width": 80, "flex": 0},
                    "Дата": {"width": 120, "flex": 0},
                    "Статус": {"width": 120, "flex": 0},
                    "Тип": {"minWidth": 150, "flex": 1},
                    "Сумма": {"width": 100, "flex": 0},
                    "Пользователь ID": {"width": 120, "flex": 0},
                }.items():
                    if col in df.columns:
                        gb.configure_column(col, **cfg)

                gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
                gb.configure_grid_options(domLayout='autoHeight')
                grid_options = gb.build()
                AgGrid(
                    df,
                    gridOptions=grid_options,
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    theme='streamlit',
                    use_container_width=True,
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW
                )
            else:
                st.info("Транзакций пока нет")
        except Exception as e:
            handle_api_error(e)
