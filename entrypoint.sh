#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Configuring Site..."
python manage.py shell -c "
from django.contrib.sites.models import Site
Site.objects.update_or_create(id=1, defaults={'domain': 'mlt.com.br', 'name': 'Blood Lab'})
"

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 300 --max-requests 500 --max-requests-jitter 50 blood_exams.wsgi:application
