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

    def calculate_target_hours(self, working_days_in_month: int) -> float:
         return working_days_in_month * 6.0
