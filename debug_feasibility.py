from src.database.repository import EmployeeRepository

repo = EmployeeRepository()
emps = repo.get_all_employees()
print(f"Total Active Employees: {len(emps)}")
for e in emps:
    print(f"- {e.nome_cognome} (Team: {e.team_id}, NoNotte: {e.limitazione_notte})")

# Minimum reqs in code: 2 Morning + 2 Afternoon + 2 Night (default) = 6 people/day
print("\nRequirements Check:")
print(f"Required slots/day: 2 (M) + 2 (P) + 2 (N) = 6")
print(f"Available people: {len(emps)}")

if len(emps) < 6:
    print("!!! INFEASIBLE: Fewer employees than required slots!")
else:
    print("Feasibility check: OK (by numbers)")
