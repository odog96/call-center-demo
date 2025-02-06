from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('call_center.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/api/metrics')
def get_metrics():
    conn = get_db_connection()
    try:
        metrics = conn.execute('SELECT * FROM metrics ORDER BY fiscal_period').fetchall()
        return jsonify([dict(row) for row in metrics])
    except Exception as e:
        print(f"Error in get_metrics: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/call_summary')
def get_call_summary():
    conn = get_db_connection()
    try:
        query = '''
            SELECT 
                churn_risk,
                AVG(queue_time_seconds) as avg_queue_time,
                COUNT(*) as call_count
            FROM calls
            GROUP BY churn_risk
            ORDER BY avg_queue_time DESC
        '''
        calls = conn.execute(query).fetchall()
        return jsonify([dict(row) for row in calls])
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(port=8100)
