#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Make migrations (optional, uncomment if needed)
# python manage.py makemigrations

# Apply migrations (optional, uncomment if needed)
# python manage.py migrate

echo "Build completed successfully!"
