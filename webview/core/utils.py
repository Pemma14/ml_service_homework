import json
import csv
import io
import re
from typing import Dict, Any, List, Tuple
import pandas as pd
import streamlit as st
from webview.core.config import ALIAS_MAP, REQUIRED_ALIAS_ORDER, STATUS_MAP, SYNONYMS_MAP, MAX_AGE, MIN_AGE


def is_valid_url(url: str) -> bool:
    """Валидирует URL-адрес."""
    if not url or not isinstance(url, str):
        return False
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


@st.cache_data
def to_alias_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразует ключи в русские алиасы, используя умный поиск (синонимы)."""
    out = {}

    # Сначала подготовим карту: очищенный ключ в нижнем регистре -> канонический алиас
    # Это можно было бы кэшировать отдельно, но для простоты сделаем тут
    key_to_canonical = {}
    for canonical, synonyms in SYNONYMS_MAP.items():
        for syn in synonyms:
            key_to_canonical[syn.lower().strip()] = canonical
        # Сам канонический вариант тоже добавим на всякий случай
        key_to_canonical[canonical.lower().strip()] = canonical

    for k, v in row.items():
        # Очищаем входящий ключ
        clean_k = str(k).lower().strip()

        # 1. Прямое совпадение с каноническим алиасом (уже есть в key_to_canonical)
        # 2. Поиск через синонимы
        canonical = key_to_canonical.get(clean_k)
        if canonical:
            out[canonical] = v
        else:
            # 3. Старый механизм через ALIAS_MAP
            alias = ALIAS_MAP.get(k)
            if alias:
                out[alias] = v
            else:
                # Сохраняем как есть, если не нашли совпадений
                out[k] = v
    return out


@st.cache_data
def coerce_number(val) -> Tuple[bool, float | int | None]:
    """Преобразует значение в число, поддерживая текстовые статусы."""
    if val is None:
        return False, None

    if isinstance(val, (int, float)):
        return True, val

    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return False, None

        # Положительные статусы
        if s in ("есть", "выявлен", "да", "присутствует", "принимает", "1", "1.0", "true", "yes"):
            return True, 1
        # Отрицательные статусы
        if s in ("нет", "не выявлен", "отсутствует", "не принимает", "0", "0.0", "false", "no"):
            return True, 0

        try:
            if "." in s or "," in s:
                return True, float(s.replace(",", "."))
            return True, int(s)
        except Exception:
            return False, None

    return False, None


@st.cache_data
def validate_item(item: Dict[str, Any]) -> Tuple[bool, Dict[str, str], Dict[str, Any], List[str]]:
    """
    Валидирует один объект данных для ML-запроса.
    Возвращает (is_valid, errors_by_field, normalized_item, warnings).
    """
    errs: Dict[str, str] = {}
    warnings: List[str] = []
    norm = to_alias_keys(item)

    # № Пациента
    p_id = norm.get("№ Пациента")
    if p_id is not None and str(p_id).strip():
        norm["№ Пациента"] = str(p_id)
    else:
        norm["№ Пациента"] = None

    # Возраст: MIN_AGE..MAX_AGE
    ok, num = coerce_number(norm.get("Возраст"))
    if not ok or num is None:
        errs["Возраст"] = "Число обязательно"
    else:
        try:
            num_f = float(num)
            if not (MIN_AGE <= num_f <= MAX_AGE):
                errs["Возраст"] = f"Значение должно быть в диапазоне {MIN_AGE}..{MAX_AGE}"
            norm["Возраст"] = num_f
        except Exception:
            errs["Возраст"] = "Некорректный формат"

    # Бинарные признаки
    binary_cols = [
        "ВНН/ПП",
        "Клозапин",
        "CYP2C19 1/2",
        "CYP2C19 1/17",
        "CYP2C19 *17/*17",
        "CYP2D6 1/3",
    ]

    for key in binary_cols:
        val = norm.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            norm[key] = 0
            warnings.append(key)
            continue

        ok, num = coerce_number(val)
        if not ok or num is None:
            errs[key] = "Допустимы 0/1 или статусы (Да/Нет)"
        else:
            try:
                iv = int(num)
                if iv not in (0, 1):
                    errs[key] = "Допустимы только 0 или 1"
                norm[key] = iv
            except Exception:
                errs[key] = "Некорректный формат"

    # Проверка обязательных колонок из REQUIRED_ALIAS_ORDER
    for col in REQUIRED_ALIAS_ORDER:
        if col not in norm:
            norm[col] = 0
            if col == "Возраст":
                errs["Возраст"] = "Поле отсутствует"
            else:
                warnings.append(col)

    return len(errs) == 0, errs, norm, list(set(warnings))


def parse_uploaded_file(file_or_list) -> List[Dict[str, Any]]:
    """Парсит загруженный файл или список файлов (JSON, CSV или Excel)."""
    if isinstance(file_or_list, list):
        all_data = []
        for f in file_or_list:
            all_data.extend(parse_uploaded_file(f))
        return all_data

    file = file_or_list
    name = (file.name or "").lower()
    content = file.read()
    file.seek(0)

    if name.endswith(".json"):
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise ValueError("Ожидался список объектов JSON")
        return data

    if name.endswith(".csv"):
        text = content.decode("utf-8")
        f = io.StringIO(text)
        reader = csv.DictReader(f)
        return list(reader)

    if name.endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(file)
            # Заменяем NaN на None для корректной работы JSON API
            return df.where(pd.notnull(df), None).to_dict(orient="records")
        except ImportError:
            raise ImportError("Для работы с Excel установите библиотеку openpyxl: pip install openpyxl")
        except Exception as e:
            raise ValueError(f"Ошибка при чтении Excel: {e}")

    # Попытка авто-определения JSON
    try:
        data = json.loads(content.decode("utf-8"))
        return data if isinstance(data, list) else [data]
    except Exception:
        raise ValueError("Поддерживаются файлы CSV, JSON или Excel")


def parse_tsv(text: str) -> List[Dict[str, Any]]:
    """Парсит текст в формате TSV (обычно при вставке из Excel)."""
    if not text or not text.strip():
        return []

    f = io.StringIO(text.strip())
    # Excel при копировании использует табуляцию как разделитель
    reader = csv.DictReader(f, delimiter='\t')
    return list(reader)


def create_excel_template() -> bytes:
    """Создает байты пустого Excel-файла с заголовками."""
    df = pd.DataFrame(columns=REQUIRED_ALIAS_ORDER)
    # Добавим одну строку-пример
    example_row = {
        "№ Пациента": "П-101",
        "Возраст": 35,
        "ВНН/ПП": 1,
        "Клозапин": 0,
        "CYP2C19 1/2": 0,
        "CYP2C19 1/17": 1,
        "CYP2C19 *17/*17": 0,
        "CYP2D6 1/3": 0,
    }
    df = pd.concat([df, pd.DataFrame([example_row])], ignore_index=True)
    return create_excel_download(df, sheet_name='Template')


def create_excel_download(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    """Создает байты Excel-файла из DataFrame."""
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        return output.getvalue()
    except ImportError:
        raise ImportError("Для работы с Excel установите библиотеку openpyxl: pip install openpyxl")
    except Exception as e:
        raise ValueError(f"Ошибка при создании Excel: {e}")


def prepare_results_df(input_data: List[Dict[str, Any]], prediction: Any, status: str = None) -> pd.DataFrame:
    """Объединяет входные данные и предсказания в один DataFrame."""
    if not input_data:
        return pd.DataFrame()

    df = pd.DataFrame(input_data)

    # Пытаемся сопоставить предсказания строкам
    if prediction is not None:
        if isinstance(prediction, list):
            if len(prediction) == len(df):
                df["Результат"] = prediction
            else:
                # Если список, но длина не совпадает, превращаем в строку
                df["Результат"] = str(prediction)
        else:
            # Одиночное предсказание для всех строк
            df["Результат"] = prediction

    # Упорядочиваем колонки: №пациента первым, Результат последним
    cols = [c for c in REQUIRED_ALIAS_ORDER if c in df.columns]
    cols += [c for c in df.columns if c not in cols and c != "Результат"]
    if "Результат" in df.columns:
        cols.append("Результат")

    return df[cols]


@st.cache_data
def status_label(status: str) -> str:
    """Возвращает красивую метку для статуса."""
    s_l = (status or "").lower()
    status_info = STATUS_MAP.get(s_l, {"label": status, "icon": "⬜"})
    return f"{status_info['icon']} {status_info['label']}"


def show_prediction_result(res: Any) -> None:
    """Отображает результат предсказания."""
    with st.container(border=True):
        st.markdown("#### 🎯 Результат предсказания")
        if isinstance(res, dict):
            pred = res.get("prediction")
            if pred is not None:
                if isinstance(pred, list):
                    st.markdown("**Предсказания:**")
                    for i, v in enumerate(pred, 1):
                        st.write(f"• Объект {i}: `{v}`")
                else:
                    st.write(pred)

            # Служебная информация (ID запроса и примечание удалены по просьбе пользователя)
            meta_lines = []
            if "status" in res:
                meta_lines.append(f"**Статус:** {status_label(str(res['status']))}")
            if "message" in res:
                meta_lines.append(f"**Сообщение:** {res['message']}")
            if "cost" in res:
                meta_lines.append(f"**Стоимость:** {res['cost']} кредитов")
            if meta_lines:
                st.markdown("---")
                for line in meta_lines:
                    st.markdown(line)
        elif isinstance(res, list):
            st.markdown("**Предсказания:**")
            for i, v in enumerate(res, 1):
                st.write(f"• Объект {i}: `{v}`")
        else:
            st.info(res)


@st.cache_data(show_spinner=False)
def requests_to_df(items: List[dict]) -> pd.DataFrame:
    """Преобразует список запросов в DataFrame для отображения."""
    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)

    # Извлечём название модели
    if "ml_model" in df.columns:
        df["model_name"] = df["ml_model"].apply(
            lambda x: (x or {}).get("name") if isinstance(x, dict) else None
        )

    # Читаемая дата
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

    # Красивый статус
    if "status" in df.columns:
        df["status_label"] = df["status"].apply(lambda s: status_label(str(s)))

    # Выбираем нужные колонки
    cols = [c for c in [
        "id", "created_at", "status_label", "cost", "model_name", "prediction"
    ] if c in df.columns]

    return df[cols].rename(columns={
        "id": "ID",
        "created_at": "Дата",
        "status_label": "Статус",
        "cost": "Списание",
        "model_name": "Модель",
        "prediction": "Предсказание",
    })


@st.cache_data(show_spinner=False)
def transactions_to_df(items: List[dict]) -> pd.DataFrame:
    """Преобразует список транзакций в DataFrame."""
    if not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)


    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

    if "status" in df.columns:
        df["status_label"] = df["status"].apply(lambda s: status_label(str(s)))

    # Определяем колонки
    guess_type = "type" if "type" in df.columns else ("operation_type" if "operation_type" in df.columns else None)
    guess_amount = "amount" if "amount" in df.columns else ("value" if "value" in df.columns else None)

    cols = [c for c in [
        "id", "created_at", "status_label", guess_type, guess_amount
    ] if c and c in df.columns]

    rename = {
        "id": "ID",
        "created_at": "Дата",
        "status_label": "Статус",
    }
    if guess_type:
        rename[guess_type] = "Тип"
    if guess_amount:
        rename[guess_amount] = "Сумма"

    return df[cols].rename(columns=rename)


@st.cache_data(show_spinner=False)
def calculate_statistics(requests: List[dict]) -> Dict[str, Any]:
    """Вычисляет статистику по запросам."""
    if not requests:
        return {
            "total": 0,
            "success": 0,
            "pending": 0,
            "failed": 0,
            "total_cost": 0
        }

    total = len(requests)
    success = sum(1 for x in requests if str(x.get("status", "")).lower() in ("success", "completed", "done"))
    pending = sum(1 for x in requests if str(x.get("status", "")).lower() in ("pending", "processing", "in_progress"))
    failed = sum(1 for x in requests if str(x.get("status", "")).lower() in ("fail", "error", "failed"))
    total_cost = sum(float(x.get("cost", 0)) for x in requests if x.get("cost"))

    return {
        "total": total,
        "success": success,
        "pending": pending,
        "failed": failed,
        "total_cost": total_cost,
        "success_rate": (success / total * 100) if total > 0 else 0
    }
