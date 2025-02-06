import sqlite3
import time
import random
from datetime import datetime
import json

def load_customers():
    with open('customers.json', 'r') as f:
        return json.load(f)

def generate_call_record():
    """Generate a single call record"""
    customers = load_customers()
    customer = random.choice(list(customers.values()))
    
    call = {
        "caller_name": customer['name'],
        "account_id": random.choice(list(customers.keys())),
        "timestamp": datetime.now().isoformat(),
        "summary": generate_summary(),  # reuse your existing function
        "call_type": random.choice(['technical', 'promotional']),
        "customer_profile_type": customer['profile_type'],
        "churn_risk": customer['churn_risk'],
        "overall_sentiment": round(random.uniform(0.1, 0.9), 2),
        "queue_time_seconds": random.randint(0, 300)
    }
    return call

def insert_call(conn, call):
    """Insert a single call record"""
    sql = '''INSERT INTO calls(
                caller_name, account_id, timestamp, summary, 
                call_type, customer_profile_type, churn_risk, 
                overall_sentiment, queue_time_seconds
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    
    values = (
        call['caller_name'],
        call['account_id'],
        call['timestamp'],
        call['summary'],
        call['call_type'],
        call['customer_profile_type'],
        call['churn_risk'],
        call['overall_sentiment'],
        call['queue_time_seconds']
    )
    
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()

def simulate_live_calls(interval=1.0):
    """
    Simulate live calls with specified interval (in seconds)
    """
    conn = sqlite3.connect('call_center.db')
    
    print("Starting live call simulation...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            call = generate_call_record()
            insert_call(conn, call)
            print(f"Inserted call from {call['caller_name']} at {call['timestamp']}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping simulation...")
    finally:
        conn.close()

if __name__ == "__main__":
    simulate_live_calls()