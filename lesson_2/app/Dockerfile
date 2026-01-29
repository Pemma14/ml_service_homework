FROM python:3.12-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

WORKDIR /app

# Копируем файл зависимостей
COPY pyproject.toml /app/

# Устанавливаем зависимости
RUN /uv/bin/uv pip install --system --no-cache -r pyproject.toml

EXPOSE 8000

COPY . /app/

CMD ["python", "main.py"]
