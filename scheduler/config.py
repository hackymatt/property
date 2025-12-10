"""Configuration for scheduler"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'property')

# Check if using Postgres or SQLite
if os.getenv('DATABASE') == 'postgres':
    DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
else:
    # SQLite for development
    DATABASE_URL = 'sqlite+aiosqlite:///db.sqlite3'

# Scheduler settings
CHECK_INTERVAL = 1  # Check database every N seconds
