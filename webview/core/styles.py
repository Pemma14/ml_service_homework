# Цветовая палитра в стиле modern dark theme
COLORS = {
    "primary": "#6366f1",  # Indigo
    "primary_dark": "#4f46e5",
    "secondary": "#8b5cf6",  # Purple
    "success": "#10b981",  # Green
    "warning": "#f59e0b",  # Amber
    "error": "#ef4444",  # Red
    "info": "#3b82f6",  # Blue
    "bg_dark": "#0f172a",  # Slate 900
    "bg_card": "#1e293b",  # Slate 800
    "bg_card_hover": "#334155",  # Slate 700
    "text_primary": "#f1f5f9",  # Slate 100
    "text_secondary": "#94a3b8",  # Slate 400
    "border": "#334155",  # Slate 700
}

# Основной CSS для всего приложения
CUSTOM_CSS = f"""
<style>
    /* === Основные стили === */
    .stApp {{
        background: linear-gradient(135deg, {COLORS['bg_dark']} 0%, #1a1f3a 100%);
        font-family: 'Inter', sans-serif;
    }}

    /* === Scrollbar === */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: {COLORS['bg_dark']};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {COLORS['border']};
        border-radius: 10px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['primary']};
    }}

    /* === Карточки === */
    .custom-card {{
        background: {COLORS['bg_card']};
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid {COLORS['border']};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
        min-height: 360px;
        height: 100%;
    }}

    .custom-card:hover {{
        background: {COLORS['bg_card_hover']};
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
    }}

    /* === Метрики === */
    [data-testid="stMetricValue"] {{
        font-size: 2rem;
        font-weight: 700;
        color: {COLORS['primary']};
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 0.875rem;
        color: {COLORS['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* === Кнопки === */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.4);
    }}

    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.6);
    }}

    /* Стили для обычных кнопок (secondary) */
    .stButton > button[kind="secondary"] {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        color: {COLORS['text_primary']};
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }}

    .stButton > button[kind="secondary"]:hover {{
        background: {COLORS['bg_card_hover']};
        border-color: {COLORS['primary']};
        color: {COLORS['primary']};
    }}

    /* === Унифицированные стили навигации и профиля в хедере === */
    /* Сама по себе .header-item - это маркер для колонки */
    .header-item {{
        display: inline-block;
        width: 0;
        height: 0;
        overflow: hidden;
    }}

    /* Находим колонку, в которой есть наш маркер, и заставляем её подстраиваться под контент */
    [data-testid="column"]:has(.header-item) {{
        width: auto !important;
        min-width: max-content !important;
        flex: 0 0 auto !important;
    }}

    /* Прижимаем последнюю колонку с маркером .header-item к правому краю */
    [data-testid="column"]:has(.header-item):last-child {{
    margin-left: auto !important;
    }}

    /* Стилизуем кнопки внутри такой колонки */
    [data-testid="column"]:has(.header-item) button,
    [data-testid="column"]:has(.header-item) button:focus,
    [data-testid="column"]:has(.header-item) button:active,
    [data-testid="column"]:has(.header-item) [data-testid="stPopover"] > button,
    [data-testid="column"]:has(.header-item) [data-testid="stPopover"] > button:focus,
    [data-testid="column"]:has(.header-item) [data-testid="stPopover"] > button:active {{
        border: 1px solid transparent !important;
        background: transparent !important;
        color: {COLORS['text_secondary']} !important;
        font-weight: 600 !important;
        padding: 0.5rem 0.8rem !important;
        border-radius: 4px !important;
        transition: all 0.2s ease !important;
        text-transform: none !important;
        height: 38px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        box-shadow: none !important;
        outline: none !important;
        width: auto !important;
        min-width: max-content !important;
    }}

    /* Принудительный запрет переноса для внутренних элементов кнопки */
    [data-testid="column"]:has(.header-item) button div,
    [data-testid="column"]:has(.header-item) button p,
    [data-testid="column"]:has(.header-item) [data-testid="stPopover"] button div,
    [data-testid="column"]:has(.header-item) [data-testid="stPopover"] button p {{
        white-space: nowrap !important;
        width: auto !important;
    }}

    [data-testid="column"]:has(.header-item) button:hover,
    [data-testid="column"]:has(.header-item) [data-testid="stPopover"] > button:hover {{
        color: {COLORS['text_primary']} !important;
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }}

    /* Активная вкладка (если есть) */
    [data-testid="column"]:has(.header-item-active) button {{
        background: rgba(255, 255, 255, 0.15) !important;
        color: {COLORS['text_primary']} !important;
        border: 1px solid transparent !important;
    }}

    /* Специальный сброс для контейнера поповера в хедере */
    [data-testid="column"]:has(.header-item) [data-testid="stPopover"] {{
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: auto !important;
    }}

    /* Убираем разделители в segmented control если они все еще где-то остались */
    [data-testid="stSegmentedControl"] div[data-testid="stMarkdownContainer"] {{
        display: none !important;
    }}

    /* Активная вкладка в хедере (имитация через primary) */
    /* Мы будем использовать специальный контейнер или просто полагаться на то что активная кнопка будет primary */

    /* === Таблицы === */
    .stDataFrame {{
        border-radius: 8px;
        overflow: hidden;
    }}

    /* === Сайдбар === */
    [data-testid="stSidebar"] {{
        background: {COLORS['bg_card']};
        border-right: 1px solid {COLORS['border']};
    }}

    /* Поднимаем содержимое сайдбара выше */
    [data-testid="stSidebarContent"] {{
        padding-top: 0.5rem !important; /* было 2rem */
    }}

    /* Убираем лишний верхний отступ у первого заголовка в сайдбаре */
    [data-testid="stSidebarContent"] h1:first-of-type,
    [data-testid="stSidebarContent"] h2:first-of-type,
    [data-testid="stSidebarContent"] h3:first-of-type {{
        margin-top: 0.25rem !important;
    }}

    /* === Табы === */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: {COLORS['bg_card']};
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        color: {COLORS['text_secondary']};
        border: none;
        font-weight: 500;
        transition: all 0.2s ease;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background-color: {COLORS['bg_card_hover']};
        color: {COLORS['text_primary']};
    }}

    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        color: white;
        border: none;
    }}

    /* === Заголовки === */
    h1, h2, h3 {{
        color: {COLORS['text_primary']};
        font-weight: 700;
        letter-spacing: -0.02em;
    }}

    h1 {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1.5rem;
    }}

    /* === Поля ввода === */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {{
        background-color: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_primary']} !important;
        transition: all 0.2s ease-in-out !important;
    }}

    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
        border-color: {COLORS['primary']} !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
        background-color: {COLORS['bg_card_hover']} !important;
    }}

    /* === Убираем кнопки +/- у number_input === */
    button[data-testid="stNumberInputStepUp"],
    button[data-testid="stNumberInputStepDown"] {{
        display: none !important;
    }}

    /* === Статус индикаторы === */
    .status-success {{
        color: {COLORS['success']};
        font-weight: 600;
    }}

    .status-warning {{
        color: {COLORS['warning']};
        font-weight: 600;
    }}

    .status-error {{
        color: {COLORS['error']};
        font-weight: 600;
    }}

    /* === Хедер === */
    [data-testid="stVerticalBlock"]:has(div#header-container) {{
        position: fixed !important;
        top: 0 rem !important; /* Еще выше к системной панели */
        left: 0 !important;
        right: 0 !important;
        z-index: 999990 !important;
        background-color: rgba(30, 41, 59, 0.8) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border-bottom: 1px solid #334155 !important;
        padding: 0.5rem 2rem !important;
        margin: 0 -5rem 1rem -5rem !important;
        border-radius: 0 !important;
    }}

    .header-logo {{
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.04em;
        line-height: 1.0;
        white-space: nowrap;
    }}

    .block-container {{
        padding-top: 3.2rem !important; /* Уменьшили отступ под новый верх хедера */
    }}

    /* === Алерты === */
    .stAlert {{
        border-radius: 8px;
        border-left: 4px solid;
    }}

    /* === Формы === */
    .stForm {{
        background: {COLORS['bg_card']};
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid {COLORS['border']};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
    }}

    .stForm:hover {{
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        transform: translateY(-2px);
    }}

    /* === Экспандеры === */
    .streamlit-expanderHeader {{
        background-color: {COLORS['bg_card']};
        border-radius: 8px;
        border: 1px solid {COLORS['border']};
        color: {COLORS['text_primary']};
        font-weight: 600;
    }}

    /* === Прогресс бары === */
    .stProgress > div > div > div {{
        background: linear-gradient(90deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
    }}

    /* === Поповеры === */
    [data-testid="stPopover"] {{
        background: rgba(30, 41, 59, 0.8) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4) !important;
    }}

    /* === Анимации === */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .fade-in {{
        animation: fadeIn 0.5s ease-out;
    }}

    /* === Glassmorphism === */
    .glass-card {{
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px;
    }}

    @keyframes skeletonLoading {{
        0% {{ background-position: 150% 50%; }}
        100% {{ background-position: -50% 50%; }}
    }}

    .skeleton {{
        background: linear-gradient(90deg,
            {COLORS['bg_card']} 25%,
            {COLORS['bg_card_hover']} 50%,
            {COLORS['bg_card']} 75%
        );
        background-size: 200% 100%;
        animation: skeletonLoading 1.5s infinite;
        border-radius: 8px;
        min-height: 20px;
        width: 100%;
        margin-bottom: 0.5rem;
    }}

    .skeleton-text {{ height: 1rem; width: 80%; }}
    .skeleton-title {{ height: 2rem; width: 40%; margin-bottom: 1rem; }}
    .skeleton-card {{ height: 150px; border-radius: 12px; }}

    /* === Кастомные классы для статус-меток === */
    .status-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
    }}

    .badge-success {{
        background-color: rgba(16, 185, 129, 0.2);
        color: {COLORS['success']};
        border: 1px solid {COLORS['success']};
    }}

    .badge-warning {{
        background-color: rgba(245, 158, 11, 0.2);
        color: {COLORS['warning']};
        border: 1px solid {COLORS['warning']};
    }}

    .badge-error {{
        background-color: rgba(239, 68, 68, 0.2);
        color: {COLORS['error']};
        border: 1px solid {COLORS['error']};
    }}

    .badge-info {{
        background-color: rgba(59, 130, 246, 0.2);
        color: {COLORS['info']};
        border: 1px solid {COLORS['info']};
    }}
</style>
"""


def apply_custom_styles():
    """Применяет кастомные стили к приложению."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_skeleton(type: str = "text", repeats: int = 1):
    """Отображает скелетон-загрузку."""
    import streamlit as st

    for _ in range(repeats):
        if type == "card":
            st.markdown('<div class="skeleton skeleton-card"></div>', unsafe_allow_html=True)
        elif type == "title":
            st.markdown('<div class="skeleton skeleton-title"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="skeleton skeleton-text"></div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str = None, icon: str = "📊"):
    """Создает красивую карточку метрики."""
    import streamlit as st

    delta_html = f'<div style="font-size: 0.875rem; color: {COLORS["text_secondary"]};">{delta}</div>' if delta else ""

    html = f"""<div class="custom-card fade-in">
<div style="display: flex; align-items: center; gap: 1rem;">
<div style="font-size: 2.5rem;">{icon}</div>
<div style="flex: 1;">
<div style="font-size: 0.875rem; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.05em;">{label}</div>
<div style="font-size: 2rem; font-weight: 700; color: {COLORS['primary']}; margin-top: 0.25rem;">{value}</div>
{delta_html}
</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)
