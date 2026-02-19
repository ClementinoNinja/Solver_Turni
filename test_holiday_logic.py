from src.utils.holidays import get_monthly_target_hours, calculate_easter
from datetime import date

# Test Easter 2025 (should be April 20)
e25 = calculate_easter(2025)
print(f"Easter 2025: {e25}") 

# Test Easter 2026 (should be April 5)
e26 = calculate_easter(2026)
print(f"Easter 2026: {e26}")

# Test Debit April 2025 (30 days)
# Sundays: 6, 13, 20, 27 (4 days)
# Holidays: 
#   20 (Easter - Sunday, matches sunday)
#   21 (Pasquetta - Monday)
#   25 (Liberazione - Friday)
# working days = 30 - 4 (Sun) - 2 (Mon 21, Fri 25) = 24?
# Wait, Easter is Sunday.
# 6,13,20,27 are Sundays.
# 21 is Mon (Pasquetta).
# 25 is Fri.
# Total off: 4 Sun + 1 Mon + 1 Fri = 6 days off.
# Working: 24. Target: 24*6 = 144.

target_apr_25 = get_monthly_target_hours(2025, 4)
print(f"Target April 2025: {target_apr_25} (Expected 144.0)")
