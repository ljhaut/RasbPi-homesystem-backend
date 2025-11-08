from datetime import datetime, timedelta


def get_today_and_tomorrow_dates():
    today = datetime.now().strftime("%Y%m%d")
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.strftime("%Y%m%d")
    return today, tomorrow
