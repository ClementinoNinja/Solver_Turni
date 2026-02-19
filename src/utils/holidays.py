from datetime import date, timedelta
import calendar

def calculate_easter(year):
    """
    Calcola la domenica di Pasqua usando l'algoritmo standard (Meeus/Jones/Butcher).
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)

def get_italian_holidays(year):
    """
    Restituisce un set di date festive italiane per l'anno specificato.
    """
    holidays = {
        date(year, 1, 1),   # Capodanno
        date(year, 1, 6),   # Epifania
        date(year, 4, 25),  # Liberazione
        date(year, 5, 1),   # Festa Lavoratori
        date(year, 6, 2),   # Repubblica
        date(year, 8, 15),  # Ferragosto
        date(year, 11, 1),  # Ognissanti
        date(year, 12, 8),  # Immacolata
        date(year, 12, 25), # Natale
        date(year, 12, 26), # Santo Stefano
    }
    
    # Pasqua e Pasquetta
    easter = calculate_easter(year)
    pasquetta = easter + timedelta(days=1)
    
    # Nota: Pasqua è sempre Domenica, quindi ai fini del "Debito" conta già come festivo.
    # Pasquetta è Lunedì, quindi è importante aggiungerla.
    holidays.add(easter)
    holidays.add(pasquetta)
    
    return holidays

def get_monthly_target_hours(year, month, daily_target=6.0):
    """
    Calcola il debito orario del mese:
    (Giorni Totali - Domeniche - Festivi Infrasettimanali) * daily_target
    """
    idx_last_day = calendar.monthrange(year, month)[1]
    holidays = get_italian_holidays(year)
    
    working_days = 0
    for day_n in range(1, idx_last_day + 1):
        curr_date = date(year, month, day_n)
        
        is_sunday = (curr_date.weekday() == 6)
        is_holiday = (curr_date in holidays)
        
        # Se non è domenica e non è festivo -> Lavorativo
        if not is_sunday and not is_holiday:
            working_days += 1
            
    return float(working_days) * daily_target
