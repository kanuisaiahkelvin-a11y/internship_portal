#!/usr/bin/env bash
# Build script for Render / Railway / Heroku-style deployments.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py bootstrap
