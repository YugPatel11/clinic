#!/usr/bin/env bash
# exit on error
set -o errexit

echo "--- Installing dependencies ---"
pip install -r requirements.txt

echo "--- Collecting static files ---"
python manage.py collectstatic --no-input

echo "--- Preparing database migrations ---"
python manage.py makemigrations

echo "--- Applying database migrations ---"
python manage.py migrate --noinput

echo "--- Creating Superuser (if not exists) ---"
# Set DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_USERNAME in Render env for this to work
python manage.py createsuperuser --noinput || echo "Superuser creation skipped or failed (User likely already exists)."

echo "--- Build complete! ---"