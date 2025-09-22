#!/bin/bash
echo "🔧 Waiting for database to be ready..."

# Wait for database to be available
while true; do
  if python -c "import psycopg2; psycopg2.connect('postgresql://ddtimer:ddtimerpassword@db:5432/ddtimerdb').close()" 2>/dev/null; then
    break
  fi
  echo "⏳ Waiting for database..."
  sleep 2
done

echo "✅ Database is ready!"
echo "🔧 Initializing database tables (if new database)..."
python init_db.py
echo "🚀 Starting Flask application normally..."
exec flask run --host=0.0.0.0 --port=5050