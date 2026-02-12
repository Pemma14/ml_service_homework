import streamlit as st
import pandas as pd
from webview.core.styles import render_skeleton, metric_card
from webview.core.utils import calculate_statistics, requests_to_df
from webview.services.state import handle_api_error

def render_dashboard(api):
    # Получаем статистику
    try:
        requests = api.get_request_history()
        stats = calculate_statistics(requests)

        # Верхние карточки
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_card("Баланс", f"{st.session_state.get('balance', 0)} кр.", icon="💰")
        with m2:
            metric_card("Всего запросов", str(stats['total']), icon="📊")
        with m3:
            metric_card("Выполнено", str(stats['success']), icon="✅")
        with m4:
            metric_card("Потрачено", f"{stats['total_cost']} кр.", icon="💸")

        # График успешности
        if stats['total'] > 0:
            st.markdown("---")
            st.markdown("### 📈 Статистика выполнения")
            cc1, cc2 = st.columns(2)

            with cc1:
                st.metric(
                    "Процент успешных запросов",
                    f"{stats['success_rate']:.1f}%",
                    help="Доля успешно выполненных запросов"
                )

            with cc2:
                st.metric(
                    "Средняя стоимость запроса",
                    f"{stats['total_cost'] / stats['total']:.1f} кредитов" if stats['total'] > 0 else "0",
                    help="Средняя стоимость одного запроса"
                )

            # Небольшая визуализация распределения статусов
            chart_df = pd.DataFrame(
                {
                    "count": [stats["success"], stats["pending"], stats["failed"]]
                },
                index=["Успех", "В ожидании", "Ошибка"],
            )
            st.bar_chart(chart_df)

        # Последние запросы
        st.markdown("---")
        st.markdown("### 🕐 Последние запросы")
        if requests:
            recent = requests[:5]
            df = requests_to_df(recent)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Запросов пока нет")

    except Exception as e:
        handle_api_error(e)
