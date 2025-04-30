#!/bin/bash

echo "Installing dependencies..."
python3 -m pip install -r requirements-vercel.txt

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Creating staticfiles directory if it doesn't exist..."
mkdir -p staticfiles

echo "Copying static files to staticfiles directory..."
cp -r static/* staticfiles/ 2>/dev/null || :

echo "Build completed successfully!"
