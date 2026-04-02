#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting the bot..."
python main.py
