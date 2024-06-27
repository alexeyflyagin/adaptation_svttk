import locale
from datetime import datetime
from enum import Enum

import pytz


locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

moscow_tz = pytz.timezone('Europe/Moscow')


class DateFormat(str, Enum):
    FORMAT_FULL = "%d.%m.%Y, %H:%M:%S"
    FORMAT_FULL_2 = "%d.%m.%Y_%H-%M-%S"
    FORMAT_SHORT_DATE = "%d.%m.%Y"
    FORMAT_SHORT_TIME = "%H:%M"
    FORMAT_SHORT_TIME_SECOND = "%H:%M:%S"
    FORMAT_DAY_MONTH_YEAR = "%d %B %Y"
    FORMAT_DAY_MONTH_YEAR_HOUR_MINUTE = "%d.%m.%Y %H:%M"


def get_msk_datetime(it: datetime) -> datetime:
    return it.astimezone(moscow_tz)


def get_date_str(timestamp: int, time_format: DateFormat = DateFormat.FORMAT_FULL) -> str:
    date_time_utc = datetime.fromtimestamp(timestamp)
    date_time_msk = get_msk_datetime(date_time_utc)
    return date_time_msk.strftime(time_format)
