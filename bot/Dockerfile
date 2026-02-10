FROM python:3.12-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /uv/bin/uv

WORKDIR /src

# Копируем файл зависимостей
COPY bot/pyproject.toml /src/

# Устанавливаем зависимости
RUN /uv/bin/uv pip install --system --no-cache -r /src/pyproject.toml

# Копируем код бота
COPY bot /src/bot

# Команда запуска
CMD ["python", "-m", "bot.main"]
