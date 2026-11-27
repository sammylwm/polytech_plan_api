FROM ghcr.io/astral-sh/uv:python3.13-alpine

LABEL authors="sammy"

WORKDIR /app

ENV UV_NO_DEV=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN apk add --no-cache --virtual .build-deps build-base linux-headers

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

RUN apk del .build-deps

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENTRYPOINT ["sh", "./entrypoint.sh"]

COPY polytech_api/ ./
COPY uwsgi.ini ./

EXPOSE 8000

CMD ["uwsgi", "--ini", "uwsgi.ini"]
