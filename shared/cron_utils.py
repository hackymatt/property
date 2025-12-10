"""Cron expression utilities for calculating next run times"""

from datetime import datetime, timezone
from croniter import croniter


def calculate_next_run(cron_expression: str) -> datetime:
    """
    Calculate next run time using croniter.

    Args:
        cron_expression: Cron expression string (e.g., '0 */6 * * *')

    Returns:
        datetime: Next run time as naive datetime in UTC, or None if invalid expression

    Example:
        >>> next_run = calculate_next_run('0 * * * *')  # Every hour
        >>> isinstance(next_run, datetime)
        True
    """
    try:
        # Use naive datetime since database column is TIMESTAMP WITHOUT TIME ZONE
        cron = croniter(
            cron_expression, datetime.now(timezone.utc).replace(tzinfo=None)
        )
        next_time = cron.get_next(datetime)
        return next_time
    except (ValueError, AttributeError) as e:
        # Log at import site - this module doesn't have logger dependency
        print(f"Invalid cron expression '{cron_expression}': {e}")
        return None


def is_valid_cron(cron_expression: str) -> bool:
    """
    Validate if a cron expression is valid.

    Args:
        cron_expression: Cron expression string to validate

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> is_valid_cron('0 * * * *')
        True
        >>> is_valid_cron('invalid')
        False
    """
    try:
        croniter(cron_expression, datetime.now(timezone.utc).replace(tzinfo=None))
        return True
    except (ValueError, AttributeError):
        return False
