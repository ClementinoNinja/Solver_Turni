"""Regole condivise per le ore accreditate dai turni."""

from datetime import date
from decimal import Decimal
from functools import lru_cache

from src.models.shift import SHIFT_DEFINITIONS
from src.utils.holidays import get_italian_holidays


@lru_cache(maxsize=64)
def _holidays(year: int):
    return get_italian_holidays(year)


def credited_shift_hours(shift_code: str, work_date: date, shifts=None) -> Decimal:
    """Ore a credito: le assenze non maturano ore di domenica o nei festivi."""
    definitions = SHIFT_DEFINITIONS if shifts is None else shifts
    shift = definitions.get(shift_code)
    if shift is None:
        return Decimal("0")
    if shift.is_absence and (work_date.weekday() == 6 or work_date in _holidays(work_date.year)):
        return Decimal("0")
    return Decimal(str(shift.weight))


def hours_to_solver_units(hours: Decimal, scale: int = 100) -> int:
    """Converte ore decimali in unità intere del modello CP-SAT."""
    return int((hours * scale).to_integral_value())
