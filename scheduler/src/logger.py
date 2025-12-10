"""Logging configuration for scheduler"""

import logging

# Create logger
logger = logging.getLogger('scheduler')
logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(console_handler)

# Suppress SQLAlchemy and asyncio debug logs
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
