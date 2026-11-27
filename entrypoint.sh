#!/usr/bin/env bash

set -e

echo "Apply migrations"
uv run manage.py migrate
echo "Successfully applied migrations."
uv run manage.py collectstatic --noinput
uv run manage.py ensure_admin

exec "$@"
