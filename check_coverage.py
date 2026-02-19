from src.database.repository import EmployeeRepository
from collections import defaultdict
from datetime import date, timedelta
import calendar

# Config
YEAR = 2026
MONTH = 2
MIN_REQ = {'1': 2, 'K': 2, 'N': 2}

repo = EmployeeRepository()

# Get date range
num_days = calendar.monthrange(YEAR, MONTH)[1]
start = date(YEAR, MONTH, 1).strftime("%Y-%m-%d")
end = date(YEAR, MONTH, num_days).strftime("%Y-%m-%d")

print(f"Checking Coverage for {start} to {end}...")

roster = repo.get_roster_by_month(start, end)

# Organize by Day -> Shift -> Count
coverage = defaultdict(lambda: defaultdict(int))

for entry in roster:
    d = entry['data']
    s = entry['shift_code']
    coverage[d][s] += 1

# Check faults
faults = 0
for day_int in range(1, num_days+1):
    d_obj = date(YEAR, MONTH, day_int)
    d_str = d_obj.strftime("%Y-%m-%d")
    
    day_counts = coverage[d_str]
    
    print(f"\n[{d_str}]")
    for shift_code, min_needed in MIN_REQ.items():
        actual = day_counts[shift_code]
        status = "OK" if actual >= min_needed else "FAIL"
        if status == "FAIL":
            faults += 1
        print(f"  Shift {shift_code}: {actual} / {min_needed} -> {status}")

if faults == 0:
    print("\nSUCCESS: All coverage constraints met in DB.")
else:
    print(f"\nFAILURE: Found {faults} coverage violations in DB.")
