from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime, timedelta, timezone
import threading
import queue
import time
import atexit

app = Flask(__name__)

# Configuration - MUST MATCH STM32
DB_PATH = '/home/cathlynramo/iot/activity_recognition.db'
PREDICTION_INTERVAL = 5
WINDOW_SIZE = 50  # Matches STM32

# Thread-safe components
sensor_queue = queue.Queue(maxsize=1000)
prediction_buffer = []
db_lock = threading.Lock()

# Activity mapping - matches STM32 output
ACTIVITY_MAP = {
    'walking': 'Walking',
    'running': 'Running',
    'idle': 'Idle',
    'calibrating': 'Calibrating'
}

# Thread management
_worker_thread = None
_thread_started = False
_thread_lock = threading.Lock()

# Database functions
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ax REAL NOT NULL,
            ay REAL NOT NULL,
            az REAL NOT NULL,
            magnitude REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity TEXT NOT NULL,
            confidence REAL,
            source TEXT DEFAULT 'device',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data(timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp DESC)')

    # Migrate existing database - add missing columns
    try:
        # Check if magnitude column exists
        cursor.execute("PRAGMA table_info(sensor_data)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'magnitude' not in columns:
            print("⚠ Adding 'magnitude' column to sensor_data table...")
            cursor.execute('ALTER TABLE sensor_data ADD COLUMN magnitude REAL')
            print("✅ Column added successfully")

        # Check if source column exists in predictions
        cursor.execute("PRAGMA table_info(predictions)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'source' not in columns:
            print("⚠ Adding 'source' column to predictions table...")
            cursor.execute("ALTER TABLE predictions ADD COLUMN source TEXT DEFAULT 'device'")
            print("✅ Column added successfully")

    except Exception as e:
        print(f"⚠ Migration warning: {e}")

    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/realtime', methods=['GET'])
def get_realtime_prediction():
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT activity, confidence, source, timestamp
                FROM predictions
                ORDER BY timestamp DESC
                LIMIT 1
            ''')

            row = cursor.fetchone()
            conn.close()

        if row:
            return jsonify({
                'status': 'success',
                'activity': row['activity'],
                'confidence': float(row['confidence']) if row['confidence'] else 0,
                'source': row['source'] if 'source' in row.keys() else 'unknown',
                'timestamp': row['timestamp']
            })
        else:
            return jsonify({
                'status': 'no_data',
                'activity': 'Waiting for data...',
                'confidence': 0,
                'source': 'none',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 100))

        start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT activity, confidence, timestamp
                FROM predictions
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (start_time, limit))

            rows = cursor.fetchall()

            cursor.execute('''
                SELECT activity, COUNT(*) as count
                FROM predictions
                WHERE timestamp >= ?
                GROUP BY activity
            ''', (start_time,))

            stats_rows = cursor.fetchall()
            conn.close()

        history = [{
            'activity': row['activity'],
            'confidence': float(row['confidence']) if row['confidence'] else 0,
            'timestamp': row['timestamp']
        } for row in rows]

        statistics = {row['activity']: row['count'] for row in stats_rows}

        return jsonify({
            'status': 'success',
            'total_records': len(history),
            'records': history,
            'statistics': statistics
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/database')
def database_view():
    """Database viewer page"""
    return render_template('database.html')

@app.route('/api/database/sensors', methods=['GET'])
def get_sensor_data():
    """Get sensor data in table format"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get total count
            cursor.execute('SELECT COUNT(*) as total FROM sensor_data')
            total = cursor.fetchone()['total']

            # Get paginated data
            cursor.execute('''
                SELECT id, ax, ay, az, timestamp
                FROM sensor_data
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))

            rows = cursor.fetchall()
            conn.close()

        data = [{
            'id': row['id'],
            'ax': round(row['ax'], 4),
            'ay': round(row['ay'], 4),
            'az': round(row['az'], 4),
            'timestamp': row['timestamp']
        } for row in rows]

        return jsonify({
            'status': 'success',
            'total': total,
            'limit': limit,
            'offset': offset,
            'data': data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/database/predictions', methods=['GET'])
def get_prediction_data():
    """Get prediction data in table format"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get total count
            cursor.execute('SELECT COUNT(*) as total FROM predictions')
            total = cursor.fetchone()['total']

            # Get paginated data
            cursor.execute('''
                SELECT id, activity, confidence, timestamp
                FROM predictions
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))

            rows = cursor.fetchall()
            conn.close()

        data = [{
            'id': row['id'],
            'activity': row['activity'],
            'confidence': round(row['confidence'], 3),
            'timestamp': row['timestamp']
        } for row in rows]

        return jsonify({
            'status': 'success',
            'total': total,
            'limit': limit,
            'offset': offset,
            'data': data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as total FROM predictions')
            total = cursor.fetchone()['total']

            cursor.execute('''
                SELECT
                    SUM(CASE WHEN activity = 'Walking' THEN 1 ELSE 0 END) as walking,
                    SUM(CASE WHEN activity = 'Running' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN activity = 'Idle' THEN 1 ELSE 0 END) as idle,
                    SUM(CASE WHEN activity = 'Calibrating' THEN 1 ELSE 0 END) as calibrating
                FROM predictions
            ''')

            counts = cursor.fetchone()
            conn.close()

        return jsonify({
            'status': 'success',
            'total_records': total,
            'walking_count': counts['walking'] or 0,
            'running_count': counts['running'] or 0,
            'idle_count': counts['idle'] or 0,
            'calibrating_count': counts['calibrating'] or 0
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/debug', methods=['GET'])
def debug():
    """Debug endpoint to check system status"""
    import threading as t

    # Get all threads
    all_threads = t.enumerate()
    thread_info = [{"name": th.name, "alive": th.is_alive(), "daemon": th.daemon} for th in all_threads]

    return jsonify({
        'status': 'ok',
        'worker_started': _thread_started,
        'queue_size': sensor_queue.qsize(),
        'buffer_size': len(prediction_buffer),
        'threads': thread_info,
        'thread_count': len(all_threads)
    })

@app.route('/api/upload', methods=['POST'])
def upload_sensor_data():
    """Receive sensor data with activity prediction from STM32"""
    try:
        data = request.get_json()

        print(f"📥 Received data: {data}")

        if not data or 'ax' not in data:
            print("❌ Invalid data format")
            return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400

        # Extract data
        ax = float(data['ax'])
        ay = float(data['ay'])
        az = float(data['az'])

        # Get activity from device
        activity_from_device = data.get('activity', 'unknown').lower().strip()

        # Calculate magnitude
        magnitude = (ax**2 + ay**2 + az**2)**0.5

        timestamp = datetime.now(timezone.utc).isoformat()

        print(f"📊 Parsed - ax={ax}, ay={ay}, az={az}, mag={magnitude:.3f}, activity={activity_from_device}")

        # Store sensor data and prediction
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert sensor data
            cursor.execute('''
                INSERT INTO sensor_data (ax, ay, az, magnitude, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (ax, ay, az, magnitude, timestamp))

            # Map activity to proper display format
            activity_label = ACTIVITY_MAP.get(activity_from_device, activity_from_device.capitalize())

            # Calculate confidence based on activity type (matching STM32 thresholds)
            if activity_from_device == 'running':
                confidence = 0.85
            elif activity_from_device == 'walking':
                confidence = 0.80
            elif activity_from_device == 'idle':
                confidence = 0.75
            elif activity_from_device == 'calibrating':
                confidence = 0.50
            else:
                confidence = 0.70

            # Store prediction (even if calibrating, to show status)
            cursor.execute('''
                INSERT INTO predictions (activity, confidence, source, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (activity_label, confidence, 'device', timestamp))

            conn.commit()
            conn.close()

        print(f"✅ STORED: {activity_label} (conf={confidence:.2f}, mag={magnitude:.3f}, source=device)")

        return jsonify({
            'status': 'success',
            'message': 'Data received',
            'activity_detected': activity_label,
            'magnitude': round(magnitude, 3)
        }), 200

    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Backup prediction worker (validates device predictions using same STM32 logic)
def prediction_worker():
    """Backup prediction system using same logic as STM32"""
    global prediction_buffer

    print("=" * 60)
    print("✓ BACKUP PREDICTION WORKER STARTED")
    print("=" * 60)

    last_prediction_time = 0

    while True:
        try:
            current_time = time.time()

            # Make backup predictions every 30 seconds (only if device hasn't sent data)
            if (current_time - last_prediction_time) >= 30:
                with db_lock:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    # Check if device sent data recently
                    cursor.execute('''
                        SELECT COUNT(*) as count
                        FROM predictions
                        WHERE source = 'device'
                        AND timestamp > datetime('now', '-30 seconds')
                    ''')

                    device_count = cursor.fetchone()['count']

                    if device_count == 0:
                        # Get recent sensor data for backup prediction
                        cursor.execute('''
                            SELECT ax, ay, az, magnitude
                            FROM sensor_data
                            ORDER BY id DESC
                            LIMIT ?
                        ''', (WINDOW_SIZE,))

                        rows = cursor.fetchall()

                        if len(rows) >= WINDOW_SIZE:
                            # Use same classification logic as STM32
                            magnitudes = [row['magnitude'] for row in rows]

                            # Calculate statistics
                            mean_mag = sum(magnitudes) / len(magnitudes)
                            variance = sum((m - mean_mag)**2 for m in magnitudes) / len(magnitudes)
                            max_mag = max(magnitudes)

                            # Same thresholds as STM32
                            RUNNING_THRESHOLD = 1.5
                            WALKING_THRESHOLD = 1.15

                            # Classification (matching STM32 exactly)
                            if variance > 0.15 and max_mag > RUNNING_THRESHOLD:
                                activity_label = 'Running'
                                confidence = 0.85
                            elif variance > 0.05 and max_mag > WALKING_THRESHOLD:
                                activity_label = 'Walking'
                                confidence = 0.80
                            else:
                                activity_label = 'Idle'
                                confidence = 0.75

                            cursor.execute('''
                                INSERT INTO predictions (activity, confidence, source, timestamp)
                                VALUES (?, ?, ?, ?)
                            ''', (activity_label, confidence, 'server_backup',
                                  datetime.now(timezone.utc).isoformat()))

                            conn.commit()
                            print(f"⚠ BACKUP PREDICTION: {activity_label} (var={variance:.3f}, max={max_mag:.3f})")

                    conn.close()
                    last_prediction_time = current_time

            time.sleep(10)

        except Exception as e:
            print(f"✗ Backup prediction worker error: {e}")
            time.sleep(10)

# Start worker thread
def start_worker():
    global _worker_thread, _thread_started

    with _thread_lock:
        if not _thread_started:
            _worker_thread = threading.Thread(target=prediction_worker, daemon=True, name="BackupPredictionWorker")
            _worker_thread.start()
            _thread_started = True
            print("✓ Backup prediction worker initialized")

# Hook to start thread on first request
@app.before_request
def before_request():
    if not _thread_started:
        start_worker()

# Initialize database
init_db()
print("=" * 60)
print("✓ Database initialized")
print("✓ Ready to receive data from STM32")
print("✓ WINDOW_SIZE = 50 (matches STM32)")
print("✓ Activity mapping: walking, running, idle, calibrating")
print("=" * 60)

if __name__ == '__main__':
    start_worker()
    app.run(debug=False, threaded=True)