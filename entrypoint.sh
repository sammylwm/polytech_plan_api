#!/usr/bin/env bash

set -e

echo "Apply migrations"
uv run manage.py migrate
echo "Successfully applied migrations."

exec "$@"
