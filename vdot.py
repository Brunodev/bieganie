"""
Obliczanie VDOT ze wzoru Danielsa-Gilberta.
Generowanie temp treningowych na podstawie VDOT.
"""
import math


def calculate_vdot(distance_m: float, duration_s: float) -> float | None:
    """
    Oblicz VDOT z dystansu (metry) i czasu (sekundy).
    Wzór Danielsa-Gilberta:
      VO2(v) = -4.60 + 0.182258*v + 0.000104*v^2
      %max(t) = 0.8 + 0.1894393*e^(-0.012778*t) + 0.2989558*e^(-0.1932605*t)
      VDOT = VO2 / %max
    """
    if distance_m <= 0 or duration_s <= 0:
        return None

    t = duration_s / 60.0       # minuty
    v = distance_m / t           # m/min

    vo2 = -4.60 + 0.182258 * v + 0.000104 * v ** 2
    pct = (
        0.8
        + 0.1894393 * math.exp(-0.012778 * t)
        + 0.2989558 * math.exp(-0.1932605 * t)
    )

    vdot = vo2 / pct
    if vdot < 15 or vdot > 90:
        return None

    return round(vdot, 1)


def training_paces(vdot: float) -> dict:
    """
    Generuj tempa treningowe (min/km) na podstawie VDOT.
    Przybliżenie na bazie tabel Danielsa.
    """
    if not vdot or vdot < 15:
        return {}

    # Przybliżone tempo na km na podstawie % VO2max i odwrócenia wzoru
    def pace_for_pct(pct_vo2max):
        """Zwraca tempo w sek/km dla danego % VO2max."""
        target_vo2 = vdot * pct_vo2max
        # Odwróć VO2(v) = -4.60 + 0.182258*v + 0.000104*v^2
        # 0.000104*v^2 + 0.182258*v + (-4.60 - target_vo2) = 0
        a = 0.000104
        b = 0.182258
        c = -4.60 - target_vo2
        disc = b * b - 4 * a * c
        if disc < 0:
            return None
        v = (-b + math.sqrt(disc)) / (2 * a)  # m/min
        if v <= 0:
            return None
        return 1000 / v * 60  # sek/km

    def fmt(secs):
        if secs is None:
            return None
        m = int(secs // 60)
        s = int(secs % 60)
        return f"{m}:{s:02d}"

    easy_slow = pace_for_pct(0.60)
    easy_fast = pace_for_pct(0.74)
    marathon = pace_for_pct(0.80)
    threshold = pace_for_pct(0.86)
    interval = pace_for_pct(0.98)
    rep = pace_for_pct(1.05)

    return {
        'easy': f"{fmt(easy_fast)} – {fmt(easy_slow)}",
        'easy_fast': fmt(easy_fast),
        'easy_slow': fmt(easy_slow),
        'marathon': fmt(marathon),
        'threshold': fmt(threshold),
        'interval': fmt(interval),
        'repetition': fmt(rep),
    }


def seconds_to_pace(duration_s: float, distance_m: float) -> str:
    """Konwertuj na tempo min:ss/km."""
    if distance_m <= 0 or duration_s <= 0:
        return ""
    pace_s = duration_s / (distance_m / 1000)
    return f"{int(pace_s // 60)}:{int(pace_s % 60):02d}"


def format_duration(seconds: float) -> str:
    """Formatuj sekundy na h:mm:ss lub mm:ss."""
    if seconds <= 0:
        return "0:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
