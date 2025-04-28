#!/bin/sh

# Apply database migrations
python manage.py migrate --settings=cuteblog.settings_prod

# Collect static files
python manage.py collectstatic --noinput --settings=cuteblog.settings_prod

# Start gunicorn
exec gunicorn --bind 0.0.0.0:8000 --workers=3 --timeout=120 cuteblog.wsgi:application
