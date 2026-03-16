#!/usr/bin/env bash

# install dependencies
pip install -r backend/requirements.txt

# run migrations
python backend/config/manage.py migrate

# collect static files
python backend/config/manage.py collectstatic --noinput
