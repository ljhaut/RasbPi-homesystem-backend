from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def get_today_and_tomorrow_dates():
    today = datetime.now(tz=ZoneInfo("Europe/Helsinki")).strftime("%Y%m%d")
    tomorrow = datetime.now(tz=ZoneInfo("Europe/Helsinki")) + timedelta(days=1)
    tomorrow = tomorrow.strftime("%Y%m%d")
    return today, tomorrow
