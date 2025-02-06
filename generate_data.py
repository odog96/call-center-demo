import json
from datetime import datetime, timedelta
import random
import sqlite3
from sqlite3 import Error
import argparse

def create_connection():
    """Create a database connection to the SQLite database"""
    try:
        conn = sqlite3.connect('call_center.db')
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def load_customers():
    with open('customers.json', 'r') as f:
        return json.load(f)

def generate_timestamps(num_records, start_date=None, end_date=None):
    """
    Generate timestamps either for a specific date range or based on number of records
    Ensures temporal coherence by not generating timestamps after current time
    """
    timestamps = []
    current_time = datetime.now()
    
    if start_date and end_date:
        # Calculate records per day to spread across date range
        days_diff = (end_date - start_date).days
        records_per_day = max(1, num_records // days_diff if days_diff > 0 else num_records)
        
        current_date = start_date
        
        while current_date < end_date and len(timestamps) < num_records:
            is_today = current_date.date() == current_time.date()
            
            # For past days, use full business hours
            if not is_today:
                for _ in range(records_per_day):
                    if len(timestamps) >= num_records:
                        break
                    hour = random.randint(9, 16)
                    minute = random.randint(0, 59)
                    call_time = current_date.replace(hour=hour, minute=minute)
                    timestamps.append(call_time)
            
            # For today, only generate timestamps before current time
            elif current_time.hour >= 9:  # Only if current time is during/after business hours
                # Calculate how many hours of the day have passed since 9 AM
                hours_passed = current_time.hour - 9
                if hours_passed > 0:
                    # Distribute records across the passed hours
                    records_for_today = min(records_per_day, num_records - len(timestamps))
                    records_per_hour = max(1, records_for_today // hours_passed)
                    
                    for hour in range(9, current_time.hour):
                        for _ in range(records_per_hour):
                            if len(timestamps) >= num_records:
                                break
                            minute = random.randint(0, 59)
                            call_time = current_date.replace(hour=hour, minute=minute)
                            timestamps.append(call_time)
                    
                    # Handle current hour - only use minutes up to current minute
                    if current_time.minute > 0:  # Only if some minutes have passed in current hour
                        remaining_records = min(records_per_hour, num_records - len(timestamps))
                        for _ in range(remaining_records):
                            minute = random.randint(0, current_time.minute - 1)  # -1 to ensure we're strictly before current time
                            call_time = current_date.replace(hour=current_time.hour, minute=minute)
                            timestamps.append(call_time)
            
            current_date += timedelta(days=1)
    else:
        # Original logic for generating timestamps without date range
        num_days = max(30, int(num_records / 2.5))
        
        for i in range(num_days):
            current_date = current_time - timedelta(days=i)
            is_today = i == 0
            
            if not is_today:
                calls_per_day = random.randint(2, 3)
                for _ in range(calls_per_day):
                    if len(timestamps) >= num_records:
                        break
                    hour = random.randint(9, 16)
                    minute = random.randint(0, 59)
                    call_time = current_date.replace(hour=hour, minute=minute)
                    timestamps.append(call_time)
            else:
                # Same logic as above for today's timestamps
                if current_time.hour >= 9:
                    hours_passed = current_time.hour - 9
                    if hours_passed > 0:
                        calls_today = min(3, num_records - len(timestamps))
                        calls_per_hour = max(1, calls_today // hours_passed)
                        
                        for hour in range(9, current_time.hour):
                            for _ in range(calls_per_hour):
                                if len(timestamps) >= num_records:
                                    break
                                minute = random.randint(0, 59)
                                call_time = current_date.replace(hour=hour, minute=minute)
                                timestamps.append(call_time)
                        
                        if current_time.minute > 0:
                            remaining_calls = min(calls_per_hour, num_records - len(timestamps))
                            for _ in range(remaining_calls):
                                minute = random.randint(0, current_time.minute - 1)
                                call_time = current_date.replace(hour=current_time.hour, minute=minute)
                                timestamps.append(call_time)
    
    return sorted(timestamps)

def generate_summary(call_type, profile_type):
    technical_issues = [
        "network connectivity problems",
        "device configuration issues",
        "service interruption",
        "app functionality problems",
        "data speed concerns"
    ]
    
    promotional_topics = [
        "discussed current promotional offers",
        "explained family plan benefits",
        "reviewed upgrade options",
        "presented loyalty rewards program",
        "detailed premium features"
    ]
    
    if call_type == 'technical':
        issue = random.choice(technical_issues)
        return f"Customer reported {issue}. Provided troubleshooting steps and resolved the issue."
    else:
        promo = random.choice(promotional_topics)
        return f"Customer inquired about {promo}. Explained available options and benefits."

def create_seed_data(num_records, start_date=None, end_date=None):
    customers = load_customers()
    timestamps = generate_timestamps(num_records, start_date, end_date)
    calls = []
    
    while len(calls) < num_records and timestamps:
        for account_id, customer in customers.items():
            if len(calls) >= num_records:
                break
                
            # Bias for call type based on customer profile
            call_type_bias = 0.5  # default 50/50 chance
            if customer['profile_type'] == 'retention_required':
                call_type_bias = 0.8  # 80% chance of technical call
            elif customer['profile_type'] == 'high_value':
                call_type_bias = 0.3  # 30% chance of technical call
                
            # Bias for sentiment based on churn risk
            sentiment_bias = 0.7  # default
            if customer['churn_risk'] == 'high':
                sentiment_bias = 0.4
            elif customer['churn_risk'] == 'low':
                sentiment_bias = 0.8
                
            if not timestamps:
                break
                    
            timestamp = timestamps.pop()
            call_type = 'technical' if random.random() < call_type_bias else 'promotional'
            
            # Generate sentiment with some randomness around the bias
            sentiment = min(0.99, max(0.01, sentiment_bias + (random.random() * 0.4 - 0.2)))
            
            call = {
                "caller_name": customer['name'],
                "account_id": account_id,
                "timestamp": timestamp.isoformat(),
                "summary": generate_summary(call_type, customer['profile_type']),
                "call_type": call_type,
                "customer_profile_type": customer['profile_type'],
                "churn_risk": customer['churn_risk'],
                "overall_sentiment": round(sentiment, 2),
                "queue_time_seconds": random.randint(0, 300)
            }
            calls.append(call)
    
    # Sort calls by timestamp
    calls.sort(key=lambda x: x['timestamp'])
    return calls
    
def clean_tables(conn):
    """Clean all existing records from calls table"""
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM calls')
        conn.commit()
        print("Cleaned existing records from calls table")
    except Error as e:
        print(f"Error cleaning tables: {e}")
        
def insert_calls(conn, calls):
    """Insert calls into the database"""
    sql = '''INSERT INTO calls(
                caller_name, account_id, timestamp, summary, 
                call_type, customer_profile_type, churn_risk, 
                overall_sentiment, queue_time_seconds
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'''
    
    cur = conn.cursor()
    for call in calls:
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
        cur.execute(sql, values)
    
    conn.commit()

def print_statistics(calls):
    stats = {
        "total_calls": len(calls),
        "technical_calls": len([c for c in calls if c["call_type"] == "technical"]),
        "promotional_calls": len([c for c in calls if c["call_type"] == "promotional"]),
        "avg_sentiment": sum(c["overall_sentiment"] for c in calls) / len(calls),
        "calls_by_profile": {},
        "calls_by_churn": {}
    }
    
    for call in calls:
        stats["calls_by_profile"][call["customer_profile_type"]] = \
            stats["calls_by_profile"].get(call["customer_profile_type"], 0) + 1
        stats["calls_by_churn"][call["churn_risk"]] = \
            stats["calls_by_churn"].get(call["churn_risk"], 0) + 1
    
    print("\nSeed data statistics:")
    print(json.dumps(stats, indent=2))

def main():
    parser = argparse.ArgumentParser(description='Generate call center data')
    parser.add_argument('--num_records', type=int, default=100,
                      help='number of records to generate (default: 100)')
    parser.add_argument('--days_back', type=int,
                      help='for demo data, start this many days back')
    parser.add_argument('--calls_per_day', type=int,
                      help='for demo data, average calls per day')
    
    args = parser.parse_args()
    
    # Calculate date range if days_back is specified
    start_date = None
    end_date = None
    if args.days_back:
        end_date = datetime.now() + timedelta(days=1)  # Include full current day
        start_date = end_date - timedelta(days=args.days_back + 1)
        if args.calls_per_day:
            args.num_records = args.days_back * args.calls_per_day
    
    # Create database connection
    conn = create_connection()
    if conn is None:
        return
    
    try:
        # Clean existing data
        clean_tables(conn)
        
        # Generate the data
        calls = create_seed_data(args.num_records, start_date, end_date)
        
        # Insert into database
        insert_calls(conn, calls)
        
        # Print statistics
        print_statistics(calls)
        
        print(f"\nSuccessfully inserted {len(calls)} records into the database.")
        if start_date and end_date:
            print(f"Date range: {start_date.date()} to {end_date.date()}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()