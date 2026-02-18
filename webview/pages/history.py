import streamlit as st
from webview.core.config import ICONS
from webview.core.utils import (
    requests_to_df,
    transactions_to_df,
    show_prediction_result,
    prepare_results_df,
    create_excel_download
)
from webview.services.state import handle_api_error
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, ColumnsAutoSizeMode

def render_history(api):
    hist_tabs = st.tabs([
        f"{ICONS['ml']} ML-запросы",
        f"{ICONS['balance']} Транзакции"
    ])

    with hist_tabs[0]:
        st.markdown("### История ML-запросов")

        try:
            with st.spinner("Загрузка истории запросов..."):
                requests = api.get_request_history()

            # Поиск по ID
            request_id = st.text_input("ID запроса", key="history_id_input", help="Введите ID для просмотра деталей")
            if st.button("Показать детали", key="history_details_btn") and request_id:
                try:
                    rid = int(request_id)
                    details = api.get_request_details(rid)
                    show_prediction_result(details)

                    # Добавляем экспорт для конкретного запроса
                    input_data = details.get("input_data", [])
                    prediction = details.get("prediction")

                    if input_data:
                        results_df = prepare_results_df(input_data, prediction)
                        with st.expander(f"📥 Экспорт данных запроса"):
                            st.dataframe(results_df, width='stretch', hide_index=True)
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                st.download_button(
                                    "📊 Скачать CSV",
                                    data=results_df.to_csv(index=False, sep=';').encode("utf-8-sig"),
                                    file_name=f"ml_request_{rid}.csv",
                                    mime="text/csv",
                                    width='stretch',
                                    key=f"dl_csv_{rid}"
                                )
                            with ec2:
                                try:
                                    excel_data = create_excel_download(results_df, sheet_name=f"Request {rid}")
                                    st.download_button(
                                        "📗 Скачать Excel",
                                        data=excel_data,
                                        file_name=f"ml_request_{rid}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        width='stretch',
                                        key=f"dl_excel_{rid}"
                                    )
                                except Exception as ex:
                                    st.error(f"Ошибка Excel: {ex}")
                except Exception as e:
                    handle_api_error(e)

            # Таблица с пагинацией (AgGrid - встроенная)
            if requests:
                page_size = st.session_state.get("page_size", 10)

                df = requests_to_df(requests).reset_index(drop=True)
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)

                # Настройка колонок для предотвращения горизонтального скролла
                gb.configure_column("ID", width=80, flex=0)
                gb.configure_column("Дата", width=120, flex=0)
                gb.configure_column("Статус", width=120, flex=0)
                gb.configure_column("Списание", width=100, flex=0)
                gb.configure_column("Модель", minWidth=150, flex=1, wrapText=True, autoHeight=True)
                gb.configure_column("Предсказание", minWidth=200, flex=2, wrapText=True, autoHeight=True)

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
                st.info("История пуста")
        except Exception as e:
            handle_api_error(e)

    with hist_tabs[1]:
        st.markdown("### История транзакций")

        try:
            with st.spinner("Загрузка транзакций..."):
                transactions = api.get_balance_history()
            # Таблица с пагинацией (AgGrid - встроенная)
            if transactions:
                page_size = st.session_state.get("page_size", 10)

                df = transactions_to_df(transactions).reset_index(drop=True)
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_default_column(filter=True, sortable=True, resizable=True, editable=False)

                # Настройка колонок
                gb.configure_column("ID", width=80, flex=0)
                gb.configure_column("Дата", width=120, flex=0)
                gb.configure_column("Статус", width=120, flex=0)
                gb.configure_column("Тип", minWidth=150, flex=1)
                gb.configure_column("Сумма", width=100, flex=0)

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
                st.info("История пуста")
        except Exception as e:
            handle_api_error(e)
