#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py ensure_superuser
python manage.py seed_demo_data

# --timeout: check-model may run a GLB download (up to 60s) plus a
# synchronous Blender GLB->USDZ conversion (up to 90s export + 60s texture
# fix - see utils/usdz_convert.py) in the same request. gunicorn's 30s
# default would SIGKILL the worker mid-conversion well before our own
# per-step timeouts get a chance to fail cleanly and record a proper
# usdz_json error - 240s gives real headroom above that worst case.
exec gunicorn Platform3d.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-3}" --timeout 240
