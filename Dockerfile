FROM ghcr.io/astral-sh/uv:python3.13-alpine

LABEL authors="sammy"

WORKDIR /app

ENV UV_NO_DEV=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENTRYPOINT ["sh", "./entrypoint.sh"]

COPY polytech_api/ ./

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
