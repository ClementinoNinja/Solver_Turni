import pytest
from datetime import date
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def test_soft_constraints_tripletta():
    # Scenario: 1 Dipendente, 5 Giorni. Team 1.
    # Tripletta ideale Team 1 (offset 0): 1 -> K -> N -> S -> R
    # Se imponiamo copertura 'N' al giorno 1 (che idealmente è '1'), il solver deve accettarlo ma pagando una penalità.
    # Ma se lasciamo libero, deve scegliere la sequenza ideale perché ha costo 0.
    
    emp = Employee(id="1", nome_cognome="A", ruolo="INF", team_id=1) # Team 1
    # Troviamo una data d tale che d.toordinal() % 5 == 0 -> Ideal '1'
    # 2024-01-01 toordinal -> 738886. 738886 % 5 = 1 -> Ideal 'K'
    # 738885 % 5 = 0. Quindi 2023-12-31 era Ideal '1'.
    # 2024-01-05 (giorno 5) -> 738890 % 5 = 0. Ideal '1'.
    
    start_date = date(2024, 1, 5) # Ideal sequence starts with '1'
    days = [start_date]
    
    solver = ShiftSolver([emp], days)
    
    # Add Hard Constraints (necessary for validity)
    solver.add_hard_constraints(min_coverage={'1': 0}) # No forced coverage
    
    # Add Soft Constraints
    solver.add_soft_constraints()
    
    solution = solver.solve()
    assert solution is not None
    
    # Verifica che abbia scelto '1' (Mattina) perché è l'ideale e non ci sono altri vincoli
    shift_code = solution[0]['shift_code']
    assert shift_code == '1'

def test_soft_constraints_penalty_override():
    # Se imponiamo una copertura che forza a violare la tripletta, deve farlo comunque.
    emp = Employee(id="1", nome_cognome="A", ruolo="INF", team_id=1) 
    start_date = date(2024, 1, 5) # Ideal '1'
    days = [start_date]
    
    solver = ShiftSolver([emp], days)
    
    # Forziamo a fare Notte 'N' invece di '1'
    solver.add_hard_constraints(min_coverage={'N': 1})
    
    solver.add_soft_constraints()
    
    solution = solver.solve()
    assert solution is not None
    
    shift_code = solution[0]['shift_code']
    assert shift_code == 'N' # Deve aver accettato la penalità per soddisfare il vincolo hard
