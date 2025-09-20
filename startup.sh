#!/bin/bash
echo "🔧 Initializing database tables (if new database)..."
python init_db.py
echo "🚀 Starting Flask application normally..."
exec flask run --host=0.0.0.0 --port=5050