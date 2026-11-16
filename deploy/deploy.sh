#!/usr/bin/env bash
set -euo pipefail

cd /opt/ipsismanager
test -f .env
test -n "${IMAGE:?IMAGE is required}"
export IMAGE

docker compose -f compose.deploy.yml config --quiet
docker compose -f compose.deploy.yml pull web
docker compose -f compose.deploy.yml run --rm --no-deps web python -c \
  "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); from django.conf import settings; assert not settings.DEBUG, 'DJANGO_DEBUG must be false in production'"
docker compose -f compose.deploy.yml run --rm --no-deps web python manage.py migrate --noinput
docker compose -f compose.deploy.yml run --rm --no-deps web python manage.py collectstatic --noinput
docker compose -f compose.deploy.yml up -d --no-deps --wait --wait-timeout 90 web
