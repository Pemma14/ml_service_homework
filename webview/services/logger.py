import logging
import sys
from datetime import datetime
import streamlit as st

class CustomLogger:
    """Централизованный логгер для webview."""

    def __init__(self, name="webview", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if not self.logger.handlers:
            # Формат логов
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            # Вывод в консоль
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level, message, show_toast=False, **kwargs):
        """Внутренний метод для логирования."""
        msg = str(message)
        if kwargs:
            msg += f" | {kwargs}"

        self.logger.log(level, msg)

        if show_toast:
            if level >= logging.ERROR:
                st.toast(f"❌ {message}")
            elif level >= logging.WARNING:
                st.toast(f"⚠️ {message}")
            else:
                st.toast(f"ℹ️ {message}")

    def info(self, message, show_toast=False, **kwargs):
        self._log(logging.INFO, message, show_toast, **kwargs)

    def warning(self, message, show_toast=False, **kwargs):
        self._log(logging.WARNING, message, show_toast, **kwargs)

    def error(self, message, show_toast=False, **kwargs):
        self._log(logging.ERROR, message, show_toast, **kwargs)

    def debug(self, message, **kwargs):
        self._log(logging.DEBUG, message, False, **kwargs)

# Глобальный экземпляр логгера
logger = CustomLogger()

def get_logger(name="webview"):
    return CustomLogger(name)
