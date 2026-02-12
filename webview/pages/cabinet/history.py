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

            # Фильтры
            col1, col2 = st.columns([3, 1])
            with col1:
                if requests:
                    all_statuses = sorted(set(str(x.get("status", "")).lower() for x in requests))
                    selected_statuses = st.multiselect(
                        "Фильтр по статусам",
                        options=all_statuses,
                        default=[],
                        format_func=lambda s: s.upper(),
                        key="history_status_filter"
                    )
                    if selected_statuses:
                        requests = [r for r in requests if str(r.get("status", "")).lower() in selected_statuses]

            with col2:
                request_id = st.text_input("ID запроса", key="history_id_input")
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
                            with st.expander(f"📥 Экспорт данных запроса #{rid}"):
                                st.dataframe(results_df, use_container_width=True, hide_index=True)
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    st.download_button(
                                        "📊 Скачать CSV",
                                        data=results_df.to_csv(index=False).encode("utf-8"),
                                        file_name=f"ml_request_{rid}.csv",
                                        mime="text/csv",
                                        use_container_width=True,
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
                                            use_container_width=True,
                                            key=f"dl_excel_{rid}"
                                        )
                                    except Exception as ex:
                                        st.error(f"Ошибка Excel: {ex}")
                    except Exception as e:
                        handle_api_error(e)

            # Таблица с пагинацией
            if requests:
                page_size = st.session_state.get("page_size", 10)
                total_pages = (len(requests) - 1) // page_size + 1
                page_num = st.number_input("Страница", 1, total_pages, 1, key="history_requests_page")
                start_idx = (page_num - 1) * page_size
                end_idx = start_idx + page_size

                df = requests_to_df(requests[start_idx:end_idx])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"Показано: {start_idx + 1}-{min(end_idx, len(requests))} из {len(requests)}")
            else:
                st.info("История пуста")
        except Exception as e:
            handle_api_error(e)

    with hist_tabs[1]:
        st.markdown("### История транзакций")

        try:
            with st.spinner("Загрузка транзакций..."):
                transactions = api.get_balance_history()
            # Таблица с пагинацией
            if transactions:
                page_size = st.session_state.get("page_size", 10)
                total_pages = (len(transactions) - 1) // page_size + 1
                page_num = st.number_input("Страница", 1, total_pages, 1, key="history_trans_page")
                start_idx = (page_num - 1) * page_size
                end_idx = start_idx + page_size

                df = transactions_to_df(transactions[start_idx:end_idx])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"Показано: {start_idx + 1}-{min(end_idx, len(transactions))} из {len(transactions)}")
            else:
                st.info("История пуста")
        except Exception as e:
            handle_api_error(e)
