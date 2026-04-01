"""
Bieganie API — Flask backend.
- Serwuje HTML
- API dziennika treningowego (manual entries)
- API Garmin sync + analityka
- VDOT obliczenia
"""
import os
import json
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

import database as db
from vdot import calculate_vdot, training_paces, seconds_to_pace, format_duration

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(APP_DIR, 'data'))
UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)


# ── Static files ──

@app.route('/')
def index():
    # Serwuj z /data/bieganie jeśli tam jest, inaczej z katalogu aplikacji
    if os.path.exists(os.path.join(DATA_DIR, 'index.html')):
        return send_from_directory(DATA_DIR, 'index.html')
    return send_from_directory(APP_DIR, 'index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)


# ── Manual entries (legacy + nowe wpisy ręczne) ──

@app.route('/api/entries', methods=['GET'])
def get_entries():
    return jsonify(db.get_manual_entries())

@app.route('/api/entries', methods=['POST'])
def add_entry():
    date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    distance = request.form.get('distance', '')
    time_val = request.form.get('time', '')
    pace = request.form.get('pace', '')
    notes = request.form.get('notes', '')
    training_type = request.form.get('type', '')

    screenshot = None
    if 'screenshot' in request.files:
        file = request.files['screenshot']
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                filename = f"{uuid.uuid4().hex[:12]}{ext}"
                file.save(os.path.join(UPLOADS_DIR, filename))
                screenshot = filename

    entry = {
        'id': uuid.uuid4().hex[:8],
        'date': date,
        'distance': distance,
        'time': time_val,
        'pace': pace,
        'type': training_type,
        'notes': notes,
        'screenshot': screenshot,
        'created': datetime.now().isoformat()
    }

    db.save_manual_entry(entry)
    return jsonify(entry), 201

@app.route('/api/entries/<entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    success = db.delete_manual_entry(entry_id)
    if not success:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'ok': True})


# ── Garmin sync ──

@app.route('/api/garmin/sync', methods=['POST'])
def garmin_sync():
    """Synchronizuj aktywności z Garmin Connect."""
    try:
        from garmin_sync import sync_activities
        count = request.json.get('count', 100) if request.is_json else 100
        result = sync_activities(count=count)
        return jsonify(result)
    except ImportError:
        return jsonify({'status': 'error', 'error': 'garminconnect nie zainstalowany'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/garmin/status', methods=['GET'])
def garmin_status():
    """Status połączenia z Garmin + ostatni sync."""
    last_sync = db.get_last_sync()
    token_exists = os.path.exists(os.path.join(
        os.environ.get('GARMIN_TOKENSTORE', '/data/bieganie/.garmin_tokens'),
        'garmin_tokens.json'
    )) or os.path.exists(os.path.join(
        os.environ.get('GARMIN_TOKENSTORE', '/data/bieganie/.garmin_tokens'),
        'tokens'
    ))

    has_credentials = bool(
        os.environ.get('GARMIN_EMAIL') and os.environ.get('GARMIN_PASSWORD')
    )

    return jsonify({
        'connected': token_exists,
        'has_credentials': has_credentials,
        'last_sync': last_sync,
        'activity_count': db.get_activity_count()
    })

@app.route('/api/garmin/vo2max', methods=['GET'])
def garmin_vo2max():
    """Pobierz aktualne VO2max z Garmin."""
    try:
        from garmin_sync import get_garmin_vo2max
        return jsonify(get_garmin_vo2max())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Activities (z Garmin sync) ──

@app.route('/api/activities', methods=['GET'])
def get_activities():
    """Wszystkie aktywności z bazy (Garmin + manual)."""
    limit = request.args.get('limit', 200, type=int)
    offset = request.args.get('offset', 0, type=int)
    activities = db.get_activities(limit, offset)

    # Wzbogać o formatowane dane
    for a in activities:
        a['distance_km'] = round((a.get('distance_m') or 0) / 1000, 2)
        a['duration_fmt'] = format_duration(a.get('duration_s') or 0)
        a['pace_fmt'] = seconds_to_pace(a.get('duration_s') or 0, a.get('distance_m') or 0)

    return jsonify(activities)


# ── Analytics ──

@app.route('/api/analytics/summary', methods=['GET'])
def analytics_summary():
    """Statystyki zbiorcze."""
    stats = db.get_summary_stats()
    if stats.get('avg_pace_s'):
        stats['avg_pace_fmt'] = seconds_to_pace(stats['avg_pace_s'], 1000)
    return jsonify(stats)

@app.route('/api/analytics/vdot-history', methods=['GET'])
def vdot_history():
    """Historia VDOT do wykresu."""
    history = db.get_vdot_history()
    for h in history:
        h['distance_km'] = round((h.get('distance_m') or 0) / 1000, 2)
        h['duration_fmt'] = format_duration(h.get('duration_s') or 0)
    return jsonify(history)

@app.route('/api/analytics/weekly', methods=['GET'])
def weekly_stats():
    """Statystyki tygodniowe."""
    weeks = request.args.get('weeks', 12, type=int)
    stats = db.get_weekly_stats(weeks)
    for s in stats:
        if s.get('avg_pace_s'):
            s['avg_pace_fmt'] = seconds_to_pace(s['avg_pace_s'], 1000)
    return jsonify(stats)

@app.route('/api/analytics/hr-zones', methods=['GET'])
def hr_zones():
    """Rozkład stref tętna."""
    hrmax = request.args.get('hrmax', 191, type=int)
    return jsonify(db.get_hr_zone_distribution(hrmax))

@app.route('/api/analytics/training-paces', methods=['GET'])
def get_training_paces():
    """Tempa treningowe na podstawie aktualnego VDOT."""
    vdot = request.args.get('vdot', type=float)
    if not vdot:
        # Użyj najlepszego VDOT z ostatnich 6 tygodni
        history = db.get_vdot_history()
        if history:
            recent = [h for h in history[-20:] if h['vdot']]
            if recent:
                vdot = max(h['vdot'] for h in recent)

    if not vdot:
        vdot = 27.9  # domyślny

    paces = training_paces(vdot)
    paces['vdot'] = vdot
    return jsonify(paces)


# ── VDOT calculator ──

@app.route('/api/vdot/calculate', methods=['GET'])
def vdot_calculate():
    """Oblicz VDOT z dystansu i czasu."""
    distance_m = request.args.get('distance_m', type=float)
    duration_s = request.args.get('duration_s', type=float)
    if not distance_m or not duration_s:
        return jsonify({'error': 'Podaj distance_m i duration_s'}), 400

    vdot = calculate_vdot(distance_m, duration_s)
    paces = training_paces(vdot) if vdot else {}
    return jsonify({
        'vdot': vdot,
        'pace': seconds_to_pace(duration_s, distance_m),
        'training_paces': paces
    })


# ── Auto-sync cron (co 3h) ──

import threading
import time as _time

def auto_sync_loop():
    """Background thread — sync co 3 godziny."""
    INTERVAL = 3 * 3600  # 3h
    _time.sleep(60)  # czekaj minutę po starcie
    while True:
        try:
            if os.environ.get('GARMIN_EMAIL'):
                log.info("Auto-sync: rozpoczynam...")
                from garmin_sync import sync_activities
                result = sync_activities(count=50)
                log.info(f"Auto-sync: {result}")
            else:
                log.info("Auto-sync: brak GARMIN_EMAIL, pomijam")
        except Exception as e:
            log.error(f"Auto-sync error: {e}")
        _time.sleep(INTERVAL)

# Start background sync thread
sync_thread = threading.Thread(target=auto_sync_loop, daemon=True)
sync_thread.start()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
