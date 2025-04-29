#!/bin/sh

# Apply database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start gunicorn bound to localhost on port 41657
exec gunicorn --bind 0.0.0.0:41657 --workers=3 --timeout=120 cuteblog.wsgi:application
