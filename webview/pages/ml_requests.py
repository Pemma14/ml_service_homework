import streamlit as st
import json
import io
import csv
from datetime import datetime
from decimal import Decimal
from webview.core.config import EXPECTED_REQUEST_COST, ICONS, REQUIRED_ALIAS_ORDER, SYNONYMS_MAP
from webview.core.utils import (
    validate_item,
    parse_uploaded_file,
    show_prediction_result,
    parse_tsv,
    create_excel_template,
    prepare_results_df,
    create_excel_download,
    requests_to_df,
    status_label
)
from webview.services.api_client import UnauthorizedError
from webview.services.state import refresh_user_data, set_auth, handle_api_error
from webview.services.logger import logger

@st.dialog("Подтверждение отправки")
def confirm_ml_submission_dialog(api, to_send, send_mode, est_cost):
    st.write(f"Вы собираетесь отправить **{len(to_send)}** ML-запросов.")
    st.write(f"Общая стоимость составит **{est_cost}** кредитов.")

    with st.expander("Просмотр данных", expanded=True):
        if len(to_send) == 1:
            row = to_send[0]
            for k, v in row.items():
                label = k
                # Отображаем Да/Нет для бинарных полей, если это не возраст
                if k != "Возраст" and v in (0, 1):
                    val_text = "Да" if v == 1 else "Нет"
                else:
                    val_text = str(v)
                st.write(f"**{label.replace('*', r'\*')}:** {val_text}")
        else:
            st.dataframe(to_send, width='stretch')

    st.warning("Это действие приведет к списанию средств с вашего баланса.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Подтвердить и отправить", width='stretch', key="ml_confirm_btn_dialog"):
            st.session_state.ml_confirmed = True
            st.session_state.show_ml_confirm = False
            st.rerun()
    with col2:
        if st.button("❌ Отмена", width='stretch', key="ml_cancel_btn_dialog"):
            st.session_state.show_ml_confirm = False
            st.rerun()
    st.session_state.show_ml_confirm = False


def render_ml_requests(api):
    if 'file_uploader_key' not in st.session_state:
        st.session_state['file_uploader_key'] = 0

    # 0. Обработка подтвержденной отправки
    if st.session_state.get("ml_confirmed"):
        st.session_state.ml_confirmed = False
        st.session_state.show_ml_confirm = False  # Закрываем диалог
        to_send = st.session_state.get("ml_to_send")
        send_mode = st.session_state.get("ml_send_mode", "")
        if to_send:
            try:
                st.toast("🚀 Отправка запроса...")
                with st.spinner("Выполнение запросов..."):
                    if send_mode.startswith("⏱️"):
                        result = api.send_task(to_send)
                        st.session_state.last_bg_task_id = result.get("request_id")
                        st.success(f"✅ {len(to_send)} строк успешно отправлены в очередь на обработку!")
                    else:
                        result = api.predict(to_send)
                        st.success(f"⚡ Обработка {len(to_send)} строк завершена успешно!")

                st.session_state.last_result = result
                st.session_state.last_input = to_send
                refresh_user_data(api)
                st.rerun()
            except Exception as e:
                handle_api_error(e)

    st.markdown("### 🤖 Выполнить ML-предсказание")
    st.caption(f"{ICONS['info']} Стоимость одного запроса: {EXPECTED_REQUEST_COST} кредитов")

    mode = st.radio(
        "Источник данных",
        ["📝 Ручной ввод", "📁 Загрузить файл", "📋 Вставка из буфера"],
        horizontal=True,
        key="ml_input_mode"
    )

    # Синхронизируем с глобальной настройкой или используем умный дефолт
    # Если глобально стоит "В очередь", а режим "Ручной ввод", мы все равно ставим "Прямой ответ" как более логичный,
    # но даем возможность пользователю сменить это в сайдбаре.
    smart_default = "⚡ Прямой ответ" if mode == "📝 Ручной ввод" else "⏱️Фоновый режим"

    # Если пользователь зашел в раздел первый раз за сессию или сменил режим ввода,
    # мы можем предложить умный дефолт, если он не менял настройки в сайдбаре.
    if st.session_state.get("_last_mode") != mode:
        st.session_state.send_mode = smart_default
        st.session_state._last_mode = mode

    send_mode = st.session_state.send_mode

    batch = []

    # 1. Сбор данных в зависимости от режима
    if mode == "📝 Ручной ввод":
        pass # Будет обработано в форме
    elif mode == "📁 Загрузить файл":
        # Шаблоны файлов для загрузки
        with st.expander("Шаблоны файлов для загрузки"):
            # CSV шаблон
            csv_header = ";".join(REQUIRED_ALIAS_ORDER)
            csv_example_row = ";".join(["", "35", "1", "0", "0", "1", "0", "0"])
            csv_content = f"{csv_header}\n{csv_example_row}\n".encode("utf-8-sig")
            st.download_button(
                "⬇️ Скачать шаблон CSV",
                data=csv_content,
                file_name="ml_request_template.csv",
                mime="text/csv",
                width='stretch',
                key="download_csv_template"
            )
            # JSON шаблон
            json_obj = [{
                "№ Пациента": None,
                "Возраст": 35,
                "ВНН/ПП": 1,
                "Клозапин": 0,
                "CYP2C19 1/2": 0,
                "CYP2C19 1/17": 1,
                "CYP2C19 *17/*17": 0,
                "CYP2D6 1/3": 0,
            }]
            st.download_button(
                "⬇️ Скачать шаблон JSON",
                data=json.dumps(json_obj, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="ml_request_template.json",
                mime="application/json",
                width='stretch',
                key="download_json_template"
            )
            # Excel шаблон
            try:
                excel_content = create_excel_template()
                st.download_button(
                    "⬇️ Скачать шаблон Excel",
                    data=excel_content,
                    file_name="ml_request_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width='stretch',
                    key="download_excel_template"
                )
            except Exception as e:
                st.error(f"Не удалось создать Excel шаблон: {e}")

        file = st.file_uploader(
            "Загрузите JSON, CSV или Excel файл(ы)",
            type=["json", "csv", "xlsx", "xls"],
            help="Файлы должны содержать необходимые поля для предсказания",
            key=f"upload_file_{st.session_state['file_uploader_key']}",
            accept_multiple_files=True
        )
        c_up1, _ = st.columns([1,3])
        with c_up1:
            def clear_file():
                st.session_state['file_uploader_key'] += 1

        st.button("🧹 Очистить", key="clear_upload", on_click=clear_file)
        if file:
            try:
                batch = parse_uploaded_file(file)
                file_count = len(file) if isinstance(file, list) else 1
                st.success(f"{ICONS['success']} Загружено записей: {len(batch)} из {file_count} файл(ов)")
            except Exception as e:
                st.error(f"{ICONS['error']} Ошибка: {e}")
    elif mode == "📋 Вставка из буфера":
        paste_text = st.text_area(
            "Вставьте данные из Excel или Google Таблиц",
            height=150,
            placeholder="Скопируйте ячейки вместе с заголовками и вставьте сюда...",
            key="paste_text"
        )
        c_pt1, _ = st.columns([1,3])
        with c_pt1:
            def clear_paste():
                st.session_state.paste_text = ""

        st.button("🧹 Очистить", key="clear_paste", on_click=clear_paste)
        if paste_text:
            try:
                batch = parse_tsv(paste_text)
                if batch:
                    st.success(f"{ICONS['success']} Распознано записей: {len(batch)}")
            except Exception as e:
                st.error(f"{ICONS['error']} Ошибка парсинга: {e}")

    # 2. Интерфейс сопоставления колонок (для файлов и буфера)
    if batch and mode != "📝 Ручной ввод":
        st.markdown("---")
        st.markdown(f"#### {ICONS['settings']} Сопоставление колонок")
        st.caption("Если система неверно определила колонки в вашем файле, вы можете сопоставить их вручную.")

        all_keys = sorted(list(set(k for row in batch for k in row.keys())))
        col_mapping = {}
        cols = st.columns(3)

        for idx, target_col in enumerate(REQUIRED_ALIAS_ORDER):
            with cols[idx % 3]:
                # Умный дефолт: если название колонки совпадает с целевым
                default_index = 0
                if target_col in all_keys:
                    default_index = all_keys.index(target_col) + 1

                selected = st.selectbox(
                    f"Поле: {target_col}",
                    options=["-- Не выбрано --"] + all_keys,
                    index=default_index,
                    key=f"map_{target_col}"
                )
                if selected != "-- Не выбрано --":
                    col_mapping[selected] = target_col

        # Применяем маппинг
        if col_mapping:
            new_batch = []
            for row in batch:
                new_row = {}
                for k, v in row.items():
                    target = col_mapping.get(k, k)
                    new_row[target] = v
                new_batch.append(new_row)
            batch = new_batch

        with st.expander("Предпросмотр данных после сопоставления"):
            st.data_editor(batch, width='stretch', hide_index=True)

    # 3. Основной раздел ввода и отправки
    st.markdown("---")

    # Опции для ручного ввода (выносим выше, чтобы были доступны)
    BINARY_OPTIONS = {"Нет": 0, "Да": 1}
    CLOZAPINE_OPTIONS = {"Не принимал": 0, "Принимал": 1}

    with st.container(border=True):
        final_batch = []

        if mode == "📝 Ручной ввод":
            st.markdown(f"#### {ICONS['ml']} Ввод данных вручную")

            c1, c2 = st.columns(2)
            with c1:
                patient_id = st.text_input("№ Пациента", key="patient_input", placeholder="например, П-101", help="Необязательное поле")
                age_str = st.text_input("Возраст :red[*]", key="age_input", placeholder="например, 35")
                vnn_pp_label = st.selectbox("ВНН/ПП", options=["-- Не выбрано --"] + list(BINARY_OPTIONS.keys()), key="vnn_pp_label", help="Врождённые аномалии нервной системы или злоупотребление психоактивными веществами")
                clozapine_label = st.selectbox("Клозапин", options=["-- Не выбрано --"] + list(CLOZAPINE_OPTIONS.keys()), key="clozapine_label")

            with c2:
                cyp2c19_1_2_label = st.selectbox("CYP2C19 1/2", options=["-- Не выбрано --"] + list(BINARY_OPTIONS.keys()), key="cyp2c19_1_2_label")
                cyp2c19_1_17_label = st.selectbox("CYP2C19 1/17", options=["-- Не выбрано --"] + list(BINARY_OPTIONS.keys()), key="cyp2c19_1_17_label")
                cyp2c19_17_17_label = st.selectbox("CYP2C19 *17/*17", options=["-- Не выбрано --"] + list(BINARY_OPTIONS.keys()), key="cyp2c19_17_17_label")
                cyp2d6_1_3_label = st.selectbox("CYP2D6 1/3", options=["-- Не выбрано --"] + list(BINARY_OPTIONS.keys()), key="cyp2d6_1_3_label")

            # Валидация
            filled = True

            age_val = None
            if age_str and age_str.strip():
                try:
                    age_val = int(age_str.strip())
                    if not (0 <= age_val <= 120):
                        st.error("Возраст должен быть в диапазоне 0..120")
                        filled = False
                except Exception:
                    st.error("Возраст должен быть целым числом")
                    filled = False
            else:
                filled = False

            if filled:
                # Формируем запись, пропуская невыбранные поля (они будут заполнены значениями 'Нет' ниже)
                row = {"№ Пациента": patient_id.strip() if patient_id else None, "Возраст": age_val}
                if vnn_pp_label != "-- Не выбрано --": row["ВНН/ПП"] = BINARY_OPTIONS[vnn_pp_label]
                if clozapine_label != "-- Не выбрано --": row["Клозапин"] = CLOZAPINE_OPTIONS[clozapine_label]
                if cyp2c19_1_2_label != "-- Не выбрано --": row["CYP2C19 1/2"] = BINARY_OPTIONS[cyp2c19_1_2_label]
                if cyp2c19_1_17_label != "-- Не выбрано --": row["CYP2C19 1/17"] = BINARY_OPTIONS[cyp2c19_1_17_label]
                if cyp2c19_17_17_label != "-- Не выбрано --": row["CYP2C19 *17/*17"] = BINARY_OPTIONS[cyp2c19_17_17_label]
                if cyp2d6_1_3_label != "-- Не выбрано --": row["CYP2D6 1/3"] = BINARY_OPTIONS[cyp2d6_1_3_label]
                final_batch = [row]
        else:
            final_batch = batch

        # Валидация и сбор предупреждений
        valid_rows, invalid_rows, all_warnings = [], [], set()
        if final_batch:
            for idx, row in enumerate(final_batch, 1):
                is_valid, errors, normalized, warnings = validate_item(row)
                if is_valid:
                    valid_rows.append(normalized)
                    all_warnings.update(warnings)
                else:
                    invalid_rows.append({"row": idx, "errors": errors})

        # Предупреждения и выбор
        confirmed_defaults = True
        if all_warnings:
            st.warning(f"{ICONS['warning']} В данных отсутствуют некоторые параметры: {', '.join(sorted(all_warnings))}. Для них будет автоматически подставлено значение 'Нет' (0). Это может повлиять на точность предсказания.")
            confirmed_defaults = st.checkbox("Я согласен использовать значения по умолчанию ('Нет')", value=False, key="confirm_def")

        only_valid = True
        if invalid_rows:
            only_valid = st.checkbox(f"⚠️ Отправить только корректные записи (пропустить {len(invalid_rows)} шт.)", value=True, key="only_v")

        to_send = valid_rows if only_valid else final_batch
        est_cost = Decimal(str(len(to_send))) * EXPECTED_REQUEST_COST if to_send else Decimal("0")

        enough_balance = True
        if st.session_state.balance is not None:
            enough_balance = st.session_state.balance >= est_cost
            if to_send:
                st.info(f"{ICONS['info']} Оценочная стоимость: **{est_cost}** кредитов")
            if not enough_balance:
                st.error(f"{ICONS['error']} Недостаточно средств!")

        if invalid_rows:
            with st.expander(f"Проблемные записи ({len(invalid_rows)})"):
                for item in invalid_rows: st.error(f"Строка {item['row']}: {item['errors']}")

        # Кнопки управления
        col_send, col_clear = st.columns([3, 1])

        # Кнопка отправки
        btn_label = "🚀 Отправить запрос"
        if not to_send:
            btn_help = "Нет данных для отправки"
        elif not enough_balance:
            btn_help = "Недостаточно средств на балансе"
        elif not confirmed_defaults:
            btn_help = "Необходимо подтвердить использование значений по умолчанию"
        else:
            btn_help = f"Отправить {len(to_send)} записей на обработку"

        submitted = col_send.button(
            btn_label,
            width='stretch',
            type="primary",
            disabled=not to_send or not enough_balance or not confirmed_defaults,
            help=btn_help
        )

    def clear_all_inputs():
        st.session_state['patient_input'] = ''
        st.session_state['age_input'] = ''
        for _k in ['vnn_pp_label','clozapine_label','cyp2c19_1_2_label','cyp2c19_1_17_label','cyp2c19_17_17_label','cyp2d6_1_3_label']:
            st.session_state[_k] = '-- Не выбрано --'
        st.session_state['file_uploader_key'] += 1
        st.session_state['paste_text'] = ''
        try:
            for _col in REQUIRED_ALIAS_ORDER: st.session_state[f'map_{_col}'] = '-- Не выбрано --'
        except Exception: pass

    if col_clear.button("🧹 Очистить всё", width='stretch', help="Сбросить все поля и файлы", on_click=clear_all_inputs):
        st.rerun()

    # 4. Обработка отправки
    if submitted and to_send:
        if st.session_state.use_confirmations:
            st.session_state.show_ml_confirm = True
            st.session_state.ml_to_send = to_send
            st.session_state.ml_send_mode = send_mode
            st.session_state.ml_est_cost = est_cost
            st.rerun()
        else:
            # Прямая отправка без диалога
            try:
                with st.spinner("Выполнение запросов..."):
                    if send_mode.startswith("⏱️"):
                        result = api.send_task(to_send)
                        st.session_state.last_bg_task_id = result.get("request_id")
                        st.success(f"✅ {len(to_send)} строк успешно отправлены в очередь на обработку!")
                    else:
                        result = api.predict(to_send)
                        st.success(f"⚡ Обработка {len(to_send)} строк завершена успешно!")

                    st.session_state.last_result = result
                    st.session_state.last_input = to_send
                    refresh_user_data(api)
                    st.rerun()
            except Exception as e:
                handle_api_error(e)

    # 5. Экспорт результатов
    if st.session_state.get("last_result") is not None:
        st.markdown("---")
        show_prediction_result(st.session_state.last_result)

        st.markdown(f"### 💾 Экспорт последних результатов")

        res = st.session_state.last_result
        last_input = st.session_state.get("last_input", [])

        # Формируем таблицу
        pred = res.get("prediction") if isinstance(res, dict) else res
        results_df = prepare_results_df(last_input, pred)

        if not results_df.empty:
            # Таблица удалена по просьбе пользователя

            col_ex1, col_ex2, col_ex3 = st.columns(3)

            with col_ex1:
                st.download_button(
                    "📊 Скачать CSV",
                    data=results_df.to_csv(index=False, sep=';').encode("utf-8-sig"),
                    file_name=f"ml_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width='stretch',
                    key="download_full_csv"
                )

            with col_ex2:
                try:
                    excel_data = create_excel_download(results_df, sheet_name="ML Results")
                    st.download_button(
                        "📗 Скачать Excel",
                        data=excel_data,
                        file_name=f"ml_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width='stretch',
                        key="download_full_excel"
                    )
                except Exception as e:
                    st.error(f"Ошибка Excel: {e}")

            with col_ex3:
                st.download_button(
                    "📦 Скачать JSON",
                    data=json.dumps(res, ensure_ascii=False, indent=2).encode("utf-8"),
                    file_name=f"ml_raw_res_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    width='stretch',
                    key="download_raw_json"
                )
        else:
            st.info("Нет данных для отображения в таблице")

    # Показываем диалог подтверждения в конце, если флаг установлен
    # НО: не показываем, если уже подтверждено (избегаем повторного открытия)
    if st.session_state.get("show_ml_confirm") and not st.session_state.get("ml_confirmed"):
        confirm_ml_submission_dialog(
            api,
            st.session_state.ml_to_send,
            st.session_state.ml_send_mode,
            st.session_state.ml_est_cost
        )

    # 6. Мониторинг
    render_task_monitoring(api)


def render_task_monitoring(api):
    if "last_bg_task_id" not in st.session_state:
        return

    rid = st.session_state.last_bg_task_id

    # Контейнер для мониторинга
    monitor_placeholder = st.empty()

    with monitor_placeholder.container(border=True):
        st.markdown(f"#### {ICONS['history']} Мониторинг задачи")

        try:
            details = api.get_request_details(rid)
            status = str(details.get("status", "")).lower()

            if status in ("success", "fail"):
                # Задача завершена
                st.session_state.last_result = details
                # Очищаем ID фоновой задачи, так как она готова
                del st.session_state.last_bg_task_id

                if status == "success":
                    st.success("✅ Задача успешно выполнена!")
                else:
                    st.error("❌ Ошибка при выполнении задачи.")

                # Показываем результат
                show_prediction_result(details)

                # Обновляем данные пользователя (баланс)
                refresh_user_data(api)

                # Кнопка для скрытия блока мониторинга
                if st.button("Ок", width='stretch'):
                    st.rerun()
            else:
                # Задача в процессе
                st.info(f"Статус задачи: {status_label(status)}")
                st.markdown("""
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div class="stSpinner"></div>
                        <span>Ожидание завершения обработки... Статус обновится автоматически.</span>
                    </div>
                """, unsafe_allow_html=True)

                # Кнопка для принудительного обновления
                if st.button("🔄 Обновить сейчас", key="manual_refresh_task"):
                    st.rerun()

                # Автоматическое обновление через 3 секунды
                import time
                time.sleep(3)
                st.rerun()

        except Exception as e:
            st.error(f"Не удалось получить статус: {e}")
            if st.button("Попробовать снова"):
                st.rerun()


