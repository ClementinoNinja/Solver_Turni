from datetime import date

from src.utils.holidays import calculate_easter, get_italian_holidays, get_monthly_target_hours


def test_easter_dates():
    assert calculate_easter(2025) == date(2025, 4, 20)
    assert calculate_easter(2026) == date(2026, 4, 5)


def test_holidays_include_easter_and_pasquetta():
    holidays = get_italian_holidays(2025)
    assert date(2025, 4, 20) in holidays
    assert date(2025, 4, 21) in holidays


def test_april_2025_target_hours():
    assert get_monthly_target_hours(2025, 4) == 144.0
