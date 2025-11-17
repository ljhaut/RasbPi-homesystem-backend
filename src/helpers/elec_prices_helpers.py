from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core.config import app_settings


def get_today_and_tomorrow_dates():
    today = datetime.now(tz=ZoneInfo("Europe/Helsinki")).strftime("%Y%m%d")
    tomorrow = datetime.now(tz=ZoneInfo("Europe/Helsinki")) + timedelta(days=1)
    tomorrow = tomorrow.strftime("%Y%m%d")
    return today, tomorrow


def position_to_timestamp(position: int, day: str) -> datetime:
    """Convert position to timestamp. Position 1 = 01:00, 2 = 01:15, etc.
    Positions 93-96 represent the first hour of the next day (00:00-00:45).

    Args:
        position (int): The position in the time series.
        day (str): The day in YYYYMMDD format.

    Returns:
        datetime: The corresponding timestamp.
    """
    helsinki_tz = ZoneInfo("Europe/Helsinki")
    target_date = datetime.strptime(day, "%Y%m%d").replace(tzinfo=helsinki_tz)

    # Each position represents a 15 minute block starting from 01:00.
    minutes_from_start = 60 + (position - 1) * 15
    day_offset, minutes_from_midnight = divmod(minutes_from_start, 24 * 60)

    timestamp = target_date + timedelta(days=day_offset, minutes=minutes_from_midnight)

    return timestamp


def calculate_c_per_kwh(price_e_per_mwh: float) -> float:
    """Convert price from EUR/MWh to c/kWh."""
    eur_per_kwh = price_e_per_mwh / 1000.0
    eur_per_kwh_vat = eur_per_kwh * (1 + app_settings.FINNISH_VAT_PERCENTAGE / 100)
    cents_per_kwh_vat = eur_per_kwh_vat * 100.0
    return cents_per_kwh_vat
