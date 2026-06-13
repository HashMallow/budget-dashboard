"""Jalali (Persian / Solar Hijri) calendar helpers.

The marketing data is organized around the Persian fiscal calendar (year 1405,
months Farvardin..Esfand). Invoice dates are stored as Gregorian ``date`` values,
so dashboards must convert to the Jalali month/year for any per-month or per-year
reporting. Grouping by the Gregorian month is wrong: e.g. Farvardin/Ordibehesht
spend lands in Gregorian March-May, which previously made the Persian month labels
line up with the wrong (often empty) buckets.
"""

from __future__ import annotations

import re
from datetime import date

# Jalali month names in Persian, with a Latin transliteration for English UIs.
JALALI_MONTHS: list[tuple[int, str, str]] = [
    (1, "فروردین", "Farvardin"),
    (2, "اردیبهشت", "Ordibehesht"),
    (3, "خرداد", "Khordad"),
    (4, "تیر", "Tir"),
    (5, "مرداد", "Mordad"),
    (6, "شهریور", "Shahrivar"),
    (7, "مهر", "Mehr"),
    (8, "آبان", "Aban"),
    (9, "آذر", "Azar"),
    (10, "دی", "Dey"),
    (11, "بهمن", "Bahman"),
    (12, "اسفند", "Esfand"),
]

_DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_J_DAYS_IN_MONTH = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
_G_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def normalize_digits(value: object) -> str:
    """Return text with Persian/Arabic digits converted to ASCII digits."""
    return str(value or "").translate(_DIGIT_TRANSLATION).strip()


def _is_gregorian_leap(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def gregorian_to_jalali(g_year: int, g_month: int, g_day: int) -> tuple[int, int, int]:
    """Convert a Gregorian (year, month, day) to a Jalali (year, month, day)."""
    gy = g_year - 1600
    gm = g_month - 1
    gd = g_day - 1

    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for i in range(gm):
        g_day_no += _G_DAYS_IN_MONTH[i]
    if gm > 1 and _is_gregorian_leap(g_year):
        g_day_no += 1
    g_day_no += gd

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    for i in range(11):
        if j_day_no < _J_DAYS_IN_MONTH[i]:
            return jy, i + 1, j_day_no + 1
        j_day_no -= _J_DAYS_IN_MONTH[i]
    return jy, 12, j_day_no + 1


def jalali_to_gregorian(j_year: int, j_month: int, j_day: int) -> date:
    """Convert a Jalali (year, month, day) to a Gregorian ``date``."""
    if not 1 <= j_month <= 12:
        raise ValueError("Invalid Jalali month")
    max_day = 31 if j_month <= 6 else 30
    if j_month == 12:
        max_day = 30
    if not 1 <= j_day <= max_day:
        raise ValueError("Invalid Jalali day")

    jy = j_year + 1595
    days = (
        -355668
        + (365 * jy)
        + ((jy // 33) * 8)
        + (((jy % 33) + 3) // 4)
        + j_day
        + ((j_month - 1) * 31 if j_month < 7 else ((j_month - 7) * 30) + 186)
    )

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1

    month_lengths = [31, 29 if _is_gregorian_leap(gy) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gregorian_month = 1
    for month_length in month_lengths:
        if gd <= month_length:
            return date(gy, gregorian_month, gd)
        gd -= month_length
        gregorian_month += 1
    raise ValueError("Could not convert Jalali date")


def parse_jalali_date_text(value: object) -> date | None:
    """Parse Jalali text like 1405/01/10 or ۱۴۰۵-۰۱-۱۰ into a Gregorian date."""
    text = normalize_digits(value)
    match = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if not match:
        match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", text)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    if not 1200 <= year <= 1600:
        return None
    try:
        return jalali_to_gregorian(year, month, day)
    except ValueError:
        return None


def format_jalali_date(value: date | None) -> str:
    if value is None:
        return ""
    year, month, day = gregorian_to_jalali(value.year, value.month, value.day)
    return f"{year:04d}/{month:02d}/{day:02d}"


def jalali_year_of(value: date) -> int:
    return gregorian_to_jalali(value.year, value.month, value.day)[0]


def jalali_month_of(value: date) -> int:
    return gregorian_to_jalali(value.year, value.month, value.day)[1]


def jalali_year_bounds(j_year: int) -> tuple[date, date]:
    """Return the [start, end] Gregorian dates that fall inside a Jalali year.

    Useful for filtering ``invoice_date`` by a Jalali year directly in the database
    via ``invoice_date__range`` without per-row conversion.
    """
    from datetime import timedelta

    start = jalali_to_gregorian(j_year, 1, 1)
    end = jalali_to_gregorian(j_year + 1, 1, 1) - timedelta(days=1)
    return start, end
