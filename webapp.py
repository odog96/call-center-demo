from flask import Flask, render_template, request, jsonify  # Add request and jsonify
import os
import json
from datetime import datetime

PORT = os.getenv('CDSW_APP_PORT', '8090')
CALL_LOG_FILE = 'call_log.json'  # Define the log file path

app = Flask(__name__)

def init_call_log():
    """Initialize the call log file if it doesn't exist"""
    if not os.path.exists(CALL_LOG_FILE):
        with open(CALL_LOG_FILE, 'w') as f:
            json.dump({"calls": []}, f)

def log_call(caller_name, account_id, summary):
    """Log a call to the JSON file"""
    try:
        with open(CALL_LOG_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"calls": []}
    
    call_record = {
        "caller_name": caller_name,
        "account_id": account_id,
        "timestamp": datetime.now().isoformat(),
        "summary": summary
    }
    
    data["calls"].append(call_record)
    
    with open(CALL_LOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    return call_record

@app.route("/")
def main():
    return render_template('sko_demo_frontend.html')

@app.route("/log_call", methods=['POST'])
def handle_call_log():
    """Handle the call logging POST request"""
    data = request.json
    call_record = log_call(
        data.get('caller_name'),
        data.get('account_id'),
        data.get('summary')
    )
    return jsonify({"status": "success", "record": call_record})

if __name__ == '__main__':
    init_call_log()  # Initialize the log file when starting the app
    app.run(host='127.0.0.1', port=PORT)