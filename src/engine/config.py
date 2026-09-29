"""Configurazione validata dei vincoli e degli obiettivi del solver."""

from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True)
class SolverConfig:
    # Valori iniziali conservati dalle regole già presenti nell'applicazione.
    shift_capacity: int = 5
    morning_coverage_options: tuple = ((2, 2), (3, 1))
    evening_coverage_options: tuple = ((2, 2), (3, 1))
    night_min_inf: int = 2
    night_min_oss: int = 1
    cycle_anchor: date = date(2026, 1, 5)
    cycle_transition_penalty: int = 1500
    night_balance_penalty: int = 20
    max_consecutive_nights: int = 2
    preference_penalty: int = 100
    hours_deviation_penalty: int = 5
    daily_target_hours: float = 6.0
    max_time_seconds: int = 60

    def __post_init__(self):
        if self.shift_capacity < 1:
            raise ValueError("La capacità massima del turno deve essere positiva.")
        if self.night_min_inf < 0 or self.night_min_oss < 0:
            raise ValueError("I minimi di copertura notturna non possono essere negativi.")
        if self.max_time_seconds < 1:
            raise ValueError("Il limite di calcolo deve essere almeno un secondo.")
        if not 0 < self.daily_target_hours <= 24:
            raise ValueError("Le ore teoriche per giorno lavorativo devono essere tra 0 e 24.")
        if (self.cycle_transition_penalty < 0 or self.night_balance_penalty < 0
                or self.preference_penalty < 0):
            raise ValueError("Le penalità non possono essere negative.")
        if self.max_consecutive_nights < 1:
            raise ValueError("max_consecutive_nights deve essere almeno 1.")
        for options in (self.morning_coverage_options, self.evening_coverage_options):
            if (len(options) != 2 or any(len(option) != 2 for option in options)
                    or any(inf < 0 or oss < 0 or inf + oss == 0 for inf, oss in options)):
                raise ValueError("Ogni alternativa di copertura deve richiedere almeno una persona.")

    @property
    def daytime_coverage(self):
        return {"1": self.morning_coverage_options, "K": self.evening_coverage_options}

    def to_dict(self):
        values = asdict(self)
        values["cycle_anchor"] = self.cycle_anchor.isoformat()
        return values

    @classmethod
    def from_dict(cls, values):
        allowed = set(cls.__dataclass_fields__)
        normalized = {key: value for key, value in values.items() if key in allowed}
        if "cycle_anchor" in normalized and isinstance(normalized["cycle_anchor"], str):
            normalized["cycle_anchor"] = date.fromisoformat(normalized["cycle_anchor"])
        for key in ("morning_coverage_options", "evening_coverage_options"):
            if key in normalized:
                normalized[key] = tuple(tuple(option) for option in normalized[key])
        return cls(**normalized)


DEFAULT_SOLVER_CONFIG = SolverConfig()
