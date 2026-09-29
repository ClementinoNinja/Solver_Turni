"""Validazione condivisa delle bozze generate e delle modifiche manuali."""

from collections import defaultdict
from datetime import date

from src.engine.config import DEFAULT_SOLVER_CONFIG


def _shift_history(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def validate_roster(entries, employees, days, requests=(), previous_shifts=None,
                    next_shifts=None, config=DEFAULT_SOLVER_CONFIG,
                    additional_coverage_entries=(), additional_employee_roles=None):
    employees_by_id = {employee.id: employee for employee in employees}
    dates = {day.isoformat() for day in days}
    schedule = {}
    errors = []

    for entry in entries:
        employee_id = entry.get("employee_id")
        day = str(entry.get("data", ""))[:10]
        code = entry.get("shift_code")
        if employee_id not in employees_by_id or day not in dates:
            errors.append(f"Assegnazione fuori periodo o dipendente sconosciuto: {employee_id}, {day}.")
            continue
        key = (employee_id, day)
        if key in schedule:
            errors.append(f"Più turni assegnati a {employee_id} il {day}.")
        if code not in {"1", "K", "N", "S", "R", "F", "M", "104", "P"}:
            errors.append(f"Codice turno non valido per {employee_id} il {day}: {code!r}.")
        schedule[key] = code

    for employee in employees:
        for day in dates:
            if (employee.id, day) not in schedule:
                errors.append(f"Manca un turno per {employee.nome_cognome} il {day}.")

    absences = {
        "FERIE": "F", "MALATTIA": "M", "104": "104", "PERMESSO": "P",
    }
    preferences = {
        "MATTINA (PREF)": "1", "POMERIGGIO (PREF)": "K", "NOTTE (PREF)": "N",
    }
    requested_absences = set()
    approved = {"APPROVED", "APPROVATO"}
    for request in requests:
        if str(request.get("stato", "")).strip().upper() not in approved:
            continue
        employee_id = request.get("employee_id")
        if employee_id not in employees_by_id:
            continue
        request_type = str(request.get("tipo_richiesta", request.get("tipo", ""))).strip().upper()
        if request_type not in absences and request_type not in preferences:
            errors.append(f"Tipo richiesta sconosciuto: {request_type!r}.")
            continue
        try:
            start = date.fromisoformat(str(request["data_inizio"])[:10])
            end = date.fromisoformat(str(request["data_fine"])[:10])
        except (KeyError, TypeError, ValueError):
            errors.append(f"Date non valide nella richiesta di {employee_id}.")
            continue
        if end < start:
            errors.append(f"Intervallo invertito nella richiesta di {employee_id}.")
            continue
        code = absences.get(request_type)
        for day in days:
            day_key = day.isoformat()
            if start <= day <= end and code:
                key = (employee_id, day_key)
                old = next((item[2] for item in requested_absences if item[:2] == key), None)
                if old is not None and old != code:
                    errors.append(f"Richieste di assenza incompatibili per {employee_id} il {day_key}.")
                requested_absences.add((employee_id, day_key, code))
                if schedule.get(key) != code:
                    errors.append(f"Assenza approvata non rispettata per {employee_id} il {day_key}.")

    for employee in employees:
        for day in days:
            day_key = day.isoformat()
            code = schedule.get((employee.id, day_key))
            if code in {"F", "M", "104", "P"} and (employee.id, day_key, code) not in requested_absences:
                errors.append(f"Assenza senza richiesta approvata per {employee.id} il {day_key}.")
            if code == "N" and employee.limitazione_notte:
                errors.append(f"Turno notturno non consentito per {employee.nome_cognome} il {day_key}.")

    previous_shifts = previous_shifts or {}
    next_shifts = next_shifts or {}
    additional_employee_roles = additional_employee_roles or {}
    for employee in employees:
        employee_days = sorted(days)
        previous_history = _shift_history(previous_shifts.get(employee.id))
        next_history = _shift_history(next_shifts.get(employee.id))
        for index, day in enumerate(employee_days):
            code = schedule.get((employee.id, day.isoformat()))
            yesterday = employee_days[index - 1].isoformat() if index else None
            yesterday_code = schedule.get((employee.id, yesterday)) if yesterday else (
                previous_history[-1] if previous_history else None
            )
            if code == "S" and yesterday_code != "N":
                errors.append(f"Smonto senza notte precedente per {employee.id} il {day.isoformat()}.")
            if yesterday_code == "N" and code == "1":
                errors.append(f"Mattina dopo notte per {employee.id} il {day.isoformat()}.")
        last_code = schedule.get((employee.id, employee_days[-1].isoformat())) if employee_days else None
        if last_code == "N" and next_history and next_history[0] == "1":
            errors.append(f"Notte seguita da mattina nel periodo successivo per {employee.id}.")
        first_code = schedule.get((employee.id, employee_days[0].isoformat())) if employee_days else None
        if previous_history and previous_history[-1] == "N" and first_code == "1":
            errors.append(f"Mattina dopo notte nel periodo precedente per {employee.id}.")

        night_run = 0
        for code in reversed(previous_history):
            if code != "N":
                break
            night_run += 1
        for day in employee_days:
            if schedule.get((employee.id, day.isoformat())) == "N":
                night_run += 1
                if night_run > config.max_consecutive_nights:
                    errors.append(
                        f"Piu di {config.max_consecutive_nights} notti consecutive per "
                        f"{employee.id} il {day.isoformat()}."
                    )
            else:
                night_run = 0
        for index, code in enumerate(next_history):
            if code != "N":
                break
            night_run += 1
            if night_run > config.max_consecutive_nights:
                errors.append(
                    f"Piu di {config.max_consecutive_nights} notti consecutive nel periodo successivo "
                    f"per {employee.id}."
                )
                break

    for day in days:
        counts = defaultdict(lambda: [0, 0])
        for employee in employees:
            code = schedule.get((employee.id, day.isoformat()))
            if code in {"1", "K", "N"}:
                counts[code][0 if employee.ruolo == "INF" else 1] += 1
        for entry in additional_coverage_entries:
            if str(entry.get("data", ""))[:10] != day.isoformat():
                continue
            code = entry.get("shift_code")
            role = additional_employee_roles.get(entry.get("employee_id"))
            if code in {"1", "K", "N"} and role in {"INF", "OSS"}:
                counts[code][0 if role == "INF" else 1] += 1
        for code, alternatives in config.daytime_coverage.items():
            if not any(counts[code][0] >= inf and counts[code][1] >= oss for inf, oss in alternatives):
                errors.append(f"Copertura insufficiente per il turno {code} il {day.isoformat()}.")
        if counts["N"][0] < config.night_min_inf or counts["N"][1] < config.night_min_oss:
            errors.append(f"Copertura notturna insufficiente il {day.isoformat()}.")
        for code in ("1", "K", "N"):
            if sum(counts[code]) > config.shift_capacity:
                errors.append(f"Capacità superata per il turno {code} il {day.isoformat()}.")

    return list(dict.fromkeys(errors))
