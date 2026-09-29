from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Employee:
    id: str = field(default="")
    matricola: str = field(default="")
    nome_cognome: str = field(default="")
    ruolo: str = field(default="INF")  # INF, OSS
    team_id: Optional[int] = None
    limitazione_notte: bool = False
    attivo: bool = True
    contract_percentage: float = 100.0

    def __post_init__(self):
        if not 0 < self.contract_percentage <= 100:
            raise ValueError("La percentuale part-time deve essere maggiore di 0 e non superare il 100%.")
        if self.ruolo not in {"INF", "OSS"}:
            raise ValueError(f"Ruolo non valido: {self.ruolo!r}.")

    @property
    def target_hours_mensile_base(self) -> float:
        """
        Calcola il target orario mensile base.
        Questo metodo richiederebbe i giorni lavorativi effettivi nel mese.
        Per ora restituisce un valore indicativo o base.
        La logica business completa deve essere nel Service Layer o calcolata dinamicamente.
        """
        # TODO: Implementare calcolo preciso basato su calendario
        return 0.0

    def calculate_target_hours(self, working_days_in_month: int, daily_target_hours: float = 6.0) -> float:
        if daily_target_hours < 0:
            raise ValueError("Le ore teoriche giornaliere non possono essere negative.")
        return working_days_in_month * daily_target_hours * self.contract_percentage / 100.0
