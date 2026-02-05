FROM python:3.12-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /uv/bin/uv


WORKDIR /src
COPY app/pyproject.toml /src/
RUN /uv/bin/uv pip install --system --no-cache -r /src/pyproject.toml
EXPOSE 8000
COPY app /src/app
CMD ["python", "-m", "app.main"]
