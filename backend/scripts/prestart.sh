#!/bin/bash

# Let the DB start
python3 /app/app/backend_pre_start.py

# Run database migrations (auto-apply schema changes)
echo "Running database migrations..."
cd /app && alembic upgrade head

# Run the initialization script
echo "Running database initialization..."
cd /app && PYTHONPATH=/app python3 scripts/init_admin.py

# Start the application
echo "Starting application..."
exec "$@"
