import locale
from datetime import datetime
from enum import Enum

import pytz


locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


class DateFormat(str, Enum):
    FORMAT_FULL = "%d.%m.%Y, %H:%M:%S"
    FORMAT_SHORT_DATE = "%d.%m.%Y"
    FORMAT_SHORT_TIME = "%H:%M"
    FORMAT_SHORT_TIME_SECOND = "%H:%M:%S"
    FORMAT_DAY_MONTH_YEAR = "%d %B %Y"
    FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE = "%d.%m.%Y %H:%M"


def get_date_str(timestamp: int, time_format: DateFormat = DateFormat.FORMAT_FULL) -> str:
    date_time_utc = datetime.fromtimestamp(timestamp)
    moscow_tz = pytz.timezone('Europe/Moscow')
    date_time_msk = date_time_utc.astimezone(moscow_tz)
    return date_time_msk.strftime(time_format)
