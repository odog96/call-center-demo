from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime

PORT = os.getenv('CDSW_APP_PORT', '8090')
CALL_LOG_FILE = 'call_log.json'
CUSTOMERS_FILE = 'customers.json'  # Add reference to customers file

app = Flask(__name__)

def load_customer_data():
    """Load customer data from JSON file"""
    try:
        with open(CUSTOMERS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: Could not load {CUSTOMERS_FILE}")
        return {}

def init_call_log():
    """Initialize the call log file if it doesn't exist"""
    if not os.path.exists(CALL_LOG_FILE):
        with open(CALL_LOG_FILE, 'w') as f:
            json.dump({"calls": []}, f)

def log_call(caller_name, account_id, summary, call_type, overall_sentiment,queue_time_seconds):
             
    """Log a call to the JSON file with enhanced fields"""
    try:
        with open(CALL_LOG_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"calls": []}
    
    # Load customer data to get profile type and churn risk
    customers = load_customer_data()
    customer_info = customers.get(account_id, {})
    
    call_record = {
        # Basic fields
        "caller_name": caller_name,
        "account_id": account_id,
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        
        # Call specific fields
        "call_type": call_type,
        "overall_sentiment": float(overall_sentiment),
       # "call_duration_minutes": int(call_duration_minutes),
        "queue_time_seconds": int(queue_time_seconds),
        
        # Customer profile fields
        "customer_profile_type": customer_info.get('profile_type', 'unknown'),
        "churn_risk": customer_info.get('churn_risk', 'unknown')
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
    """Handle the call logging POST request with enhanced fields"""
    print("Received call log request")  
    data = request.json
    print("Request data:", data)  # Add this
    
    # Validate call_type
    call_type = data.get('call_type')
    print('call type is : ',call_type)
    if call_type not in ['technical', 'promotional']:
        return jsonify({
            "status": "error",
            "message": "Invalid call_type. Must be 'technical' or 'promotional'"
        }), 400
    
    try:
        call_record = log_call(
            data.get('caller_name'),
            data.get('account_id'),
            data.get('summary'),
            call_type,
            data.get('overall_sentiment', 0.0),
           # data.get('call_duration_minutes', 0),
            data.get('queue_time_seconds', 0)
        )
        return jsonify({"status": "success", "record": call_record})
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    init_call_log()  # Initialize the log file when starting the app
    app.run(host='127.0.0.1', port=PORT)