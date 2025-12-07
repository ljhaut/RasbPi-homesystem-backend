from datetime import datetime
from zoneinfo import ZoneInfo

from core.logging_config import setup_logger

logger = setup_logger()


def get_current_point_index() -> int:
    """Get the current quarter-hour index (1-96)"""
    now = datetime.now(tz=ZoneInfo("Europe/Helsinki"))
    logger.debug(f"Current time: {now}")
    return now.hour * 4 + (now.minute // 15) + 1


def get_current_quarter_timestamp() -> datetime:
    """Get the timestamp of the current quarter-hour"""
    now = datetime.now(tz=ZoneInfo("Europe/Helsinki"))
    quarter_hour = (now.minute // 15) * 15
    quarter_timestamp = now.replace(minute=quarter_hour, second=0, microsecond=0)
    return quarter_timestamp
