from dataclasses import dataclass
from enum import Enum

class ShiftType(Enum):
    MATTINA = '1'
    POMERIGGIO = 'K'
    NOTTE = 'N'
    SMONTO = 'S'
    RIPOSO = 'R'
    FERIE = 'F'
    MALATTIA = 'M'
    LEGGE_104 = '104'
    PERMESSO = 'P'

@dataclass(frozen=True)
class Shift:
    code: str
    weight: float
    is_absence: bool
    description: str

# Dizionario dei turni standard
SHIFT_DEFINITIONS = {
    '1': Shift('1', 7.0, False, 'Mattina'),
    'K': Shift('K', 7.0, False, 'Pomeriggio'),
    'N': Shift('N', 10.0, False, 'Notte'),
    'S': Shift('S', 0.0, False, 'Smonto'),
    'R': Shift('R', 0.0, False, 'Riposo'),
    'F': Shift('F', 6.0, True, 'Ferie'),
    'M': Shift('M', 6.0, True, 'Malattia'),
    '104': Shift('104', 6.0, True, 'Legge 104'),
    'P': Shift('P', 6.0, True, 'Permesso'),
}
