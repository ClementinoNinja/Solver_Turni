from src.database.repository import EmployeeRepository

repo = EmployeeRepository()
# Get all requests for a broad range to see what's there
reqs = repo.get_requests("2026-01-01", "2026-12-31")

print(f"Found {len(reqs)} requests:")
for r in reqs:
    print(f"ID: {r['id']}, Emp: {r['employee_id']}, Type: '{r['tipo_richiesta']}', Start: {r['data_inizio']}")
