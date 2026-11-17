
#!/usr/bin/env bash
set -euo pipefail

cd /opt/ipsismanager

test -f .env
test -n "${IMAGE:?IMAGE is required}"

# Conservar la imagen actual de Angular.
# Si todavía no existe el contenedor, usar una imagen temporal
# únicamente para permitir la validación de Docker Compose.
if docker container inspect ipsis-frontend >/dev/null 2>&1; then
    FRONT_IMAGE="$(docker inspect --format='{{.Config.Image}}' ipsis-frontend)"
else
    FRONT_IMAGE="nginx:alpine"
fi

test -n "$FRONT_IMAGE"

export IMAGE FRONT_IMAGE

docker compose -f compose.deploy.yml config --quiet
docker compose -f compose.deploy.yml pull web

docker compose -f compose.deploy.yml run --rm --no-deps web python -c \
  "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); from django.conf import settings; assert not settings.DEBUG, 'DJANGO_DEBUG must be false in production'"

docker compose -f compose.deploy.yml run --rm --no-deps web python manage.py migrate --noinput
docker compose -f compose.deploy.yml run --rm --no-deps web python manage.py collectstatic --noinput

docker compose -f compose.deploy.yml up -d --no-deps --wait --wait-timeout 90 web
