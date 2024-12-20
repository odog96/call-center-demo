from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PORT = os.getenv('CDSW_APP_PORT', '8090')

app = Flask(__name__)

CALL_LOG_FILE = 'call_log.json'

def init_call_log():
    if not os.path.exists(CALL_LOG_FILE):
        with open(CALL_LOG_FILE, 'w') as f:
            json.dump({"calls": []}, f)

def log_call(caller_name, account_id, summary):
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

def send_call_summary_email(email, summary):
    # This is a mock email function
    # In production, you would configure real SMTP settings
    print(f"[MOCK EMAIL] To: {email}")
    print(f"[MOCK EMAIL] Subject: Your Call Summary")
    print(f"[MOCK EMAIL] Body: {summary}")
    return True

@app.route("/")
def main():
    return render_template('sko_demo_frontend.html')

@app.route("/log_call", methods=['POST'])
def handle_call_log():
    data = request.json
    call_record = log_call(
        data.get('caller_name'),
        data.get('account_id'),
        data.get('summary')
    )
    
    # Send email if email address is provided
    if data.get('email'):
        send_call_summary_email(data['email'], data['summary'])
    
    return jsonify({"status": "success", "record": call_record})

if __name__ == '__main__':
    init_call_log()
    app.run(host='127.0.0.1', port=PORT)