"""
Sync danych z Garmin Connect.
Używa python-garminconnect (nieoficjalna biblioteka).
Loguje się jak aplikacja mobilna Garmin → pobiera dane → zapisuje do SQLite.
"""
import os
import json
import logging
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from vdot import calculate_vdot
from database import upsert_activity, log_sync_start, log_sync_finish

log = logging.getLogger(__name__)

TOKENSTORE = os.environ.get('GARMIN_TOKENSTORE', '/app/data/.garmin_tokens')


def get_garmin_client() -> Garmin:
    """
    Zaloguj się do Garmin Connect.
    Przy pierwszym logowaniu potrzebne GARMIN_EMAIL i GARMIN_PASSWORD.
    Potem używa zapisanych tokenów (~1 rok ważności).
    """
    os.makedirs(TOKENSTORE, exist_ok=True)
    token_file = os.path.join(TOKENSTORE, 'oauth1_token.json')

    # Próba logowania z zapisanych tokenów (tylko jeśli istnieją)
    if os.path.exists(token_file):
        try:
            garmin = Garmin()
            garmin.login(TOKENSTORE)
            log.info("Zalogowano z zapisanych tokenów.")
            return garmin
        except (GarminConnectAuthenticationError, GarminConnectConnectionError):
            log.warning("Tokeny wygasły, loguję z credentials...")

    # Logowanie z credentials
    email = os.environ.get('GARMIN_EMAIL')
    password = os.environ.get('GARMIN_PASSWORD')
    if not email or not password:
        raise ValueError(
            "Brak tokenów Garmin. Ustaw GARMIN_EMAIL i GARMIN_PASSWORD w .env"
        )

    log.info(f"Logowanie do Garmin jako {email}...")
    garmin = Garmin(email=email, password=password)
    garmin.login()
    # Zapisz tokeny na przyszłość
    garmin.garth.dump(TOKENSTORE)
    log.info("Zalogowano i zapisano tokeny.")
    return garmin


def sync_activities(count: int = 100) -> dict:
    """
    Pobierz ostatnie aktywności biegowe z Garmin Connect.
    Oblicz VDOT dla każdej, zapisz do bazy.
    """
    sync_id = log_sync_start()
    synced = 0

    try:
        garmin = get_garmin_client()

        # Pobierz aktywności biegowe
        activities = garmin.get_activities(0, count, activitytype="running")
        log.info(f"Pobrano {len(activities)} aktywności biegowych z Garmin.")

        for act in activities:
            distance_m = act.get('distance', 0) or 0
            duration_s = act.get('duration', 0) or 0

            # Oblicz VDOT (tylko dla biegów ≥1km i ≥5min)
            vdot = None
            if distance_m >= 1000 and duration_s >= 300:
                vdot = calculate_vdot(distance_m, duration_s)

            # Oblicz tempo
            pace = None
            if distance_m > 0 and duration_s > 0:
                pace = duration_s / (distance_m / 1000)

            data = {
                'garmin_id': str(act.get('activityId', '')),
                'source': 'garmin',
                'date': (act.get('startTimeLocal', '') or '')[:10],
                'name': act.get('activityName', 'Bieg'),
                'activity_type': act.get('activityType', {}).get('typeKey', 'running'),
                'distance_m': distance_m,
                'duration_s': duration_s,
                'moving_duration_s': act.get('movingDuration', 0),
                'pace_s_per_km': pace,
                'avg_hr': act.get('averageHR'),
                'max_hr': act.get('maxHR'),
                'avg_cadence': act.get('averageRunningCadenceInStepsPerMinute'),
                'avg_stride_length': act.get('avgStrideLength'),
                'elevation_gain': act.get('elevationGain'),
                'elevation_loss': act.get('elevationLoss'),
                'calories': act.get('calories'),
                'vo2max_garmin': act.get('vO2MaxValue'),
                'vdot': vdot,
                'training_effect': act.get('aerobicTrainingEffect'),
                'avg_temperature': act.get('avgTemperature'),
                'raw_json': json.dumps(act, default=str),
            }

            is_new = upsert_activity(data)
            if is_new:
                synced += 1

        log_sync_finish(sync_id, synced)
        return {
            'status': 'ok',
            'total_fetched': len(activities),
            'new_synced': synced,
            'sync_id': sync_id
        }

    except GarminConnectTooManyRequestsError:
        err = "Rate limit Garmin — spróbuj za 15 minut"
        log_sync_finish(sync_id, synced, err)
        return {'status': 'error', 'error': err}

    except GarminConnectAuthenticationError as e:
        err = f"Błąd autoryzacji Garmin: {e}"
        log_sync_finish(sync_id, synced, err)
        return {'status': 'error', 'error': err}

    except Exception as e:
        err = f"Błąd sync: {e}"
        log.exception(err)
        log_sync_finish(sync_id, synced, err)
        return {'status': 'error', 'error': err}


def get_garmin_vo2max() -> dict:
    """Pobierz aktualne VO2max z Garmin."""
    try:
        garmin = get_garmin_client()
        from datetime import date
        metrics = garmin.get_max_metrics(date.today().isoformat())
        generic = metrics.get('generic', {}) if metrics else {}
        return {
            'vo2max': generic.get('vo2MaxValue'),
            'fitness_age': generic.get('fitnessAge'),
        }
    except Exception as e:
        return {'error': str(e)}


def get_garmin_rhr() -> int | None:
    """Pobierz tętno spoczynkowe z Garmin."""
    try:
        garmin = get_garmin_client()
        from datetime import date
        hr_data = garmin.get_heart_rates(date.today().isoformat())
        return hr_data.get('restingHeartRate')
    except Exception:
        return None
