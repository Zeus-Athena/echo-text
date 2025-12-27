#!/bin/bash

# Run database migrations (auto-apply schema changes)
echo "Running database migrations..."
cd /app && alembic upgrade head || echo "Warning: alembic migration failed, but continuing..."

# Run the initialization script (don't fail if it doesn't work)
echo "Running database initialization..."
cd /app && PYTHONPATH=/app python3 scripts/init_admin.py || echo "Warning: init_admin.py failed, but continuing..."

# Start the application
echo "Starting application..."
exec "$@"
