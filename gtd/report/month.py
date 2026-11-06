import datetime
from typing import Optional

REPORT_MONTH_FORMAT = "%Y-%m"
UNSPECIFIED = 0
FIRST_MONTH = 1
LAST_MONTH = 12


def resolve_report_month(
    year: int,
    month: int,
    today: datetime.date
) -> datetime.date:
    resolved_year = today.year if year == UNSPECIFIED else year
    resolved_month = today.month if month == UNSPECIFIED else month
    if not FIRST_MONTH <= resolved_month <= LAST_MONTH:
        raise ValueError(
            "Month must be between %d and %d, got %d"
            % (FIRST_MONTH, LAST_MONTH, resolved_month)
        )
    elif not datetime.MINYEAR <= resolved_year <= datetime.MAXYEAR:
        raise ValueError("Year out of range: %d" % resolved_year)
    else:
        return datetime.date(resolved_year, resolved_month, 1)


def format_report_month(month: datetime.date) -> str:
    return month.strftime(REPORT_MONTH_FORMAT)


def is_in_month(day: Optional[datetime.date], month: datetime.date) -> bool:
    if day is not None:
        return (day.year, day.month) == (month.year, month.month)
    else:
        return False
