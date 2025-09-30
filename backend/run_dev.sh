#!/bin/bash
# BRANE Backend Development Startup Script

set -e

echo "🧠 BRANE Backend - Development Startup"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration before running!"
    exit 1
fi

# Check PostgreSQL connection
echo "🔍 Checking database connection..."
python3 -c "
import asyncio
from db.database import engine
from sqlalchemy import text

async def check_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
            print('✅ Database connection successful')
            return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        print('   Make sure PostgreSQL is running and credentials are correct')
        return False

if not asyncio.run(check_db()):
    exit(1)
" || exit 1

# Run migrations
echo "📊 Running database migrations..."
alembic upgrade head || echo "⚠️  Migrations failed, but continuing..."

# Create storage directories
echo "📁 Creating storage directories..."
mkdir -p storage/axon storage/uploads storage/models

# Start server
echo "🚀 Starting BRANE backend..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/api/docs"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
