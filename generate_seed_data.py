import json
from datetime import datetime, timedelta
import random

def load_customers():
    with open('customers.json', 'r') as f:
        return json.load(f)

def generate_timestamps(num_days=30):
    timestamps = []
    now = datetime(2024, 12, 20)
    
    for i in range(num_days):
        current_date = now - timedelta(days=i)
        # 2-3 calls per day
        calls_per_day = random.randint(2, 3)
        for _ in range(calls_per_day):
            # Calls between 9AM and 5PM
            hour = random.randint(9, 16)
            minute = random.randint(0, 59)
            call_time = current_date.replace(hour=hour, minute=minute)
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

def create_seed_data():
    customers = load_customers()
    timestamps = generate_timestamps()
    calls = []
    
    for account_id, customer in customers.items():
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
            
        # 1-3 calls per customer
        num_calls = random.randint(1, 3)
        for _ in range(num_calls):
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
                #"call_duration_minutes": random.randint(5, 20), removed this
                "queue_time_seconds": random.randint(0, 300)
            }
            calls.append(call)
    
    # Sort calls by timestamp
    calls.sort(key=lambda x: x['timestamp'])
    return {"calls": calls}

def main():
    seed_data = create_seed_data()
    
    # Save to file
    with open('call_log.json', 'w') as f:
        json.dump(seed_data, f, indent=2)
    
    # Print statistics
    stats = {
        "total_calls": len(seed_data["calls"]),
        "technical_calls": len([c for c in seed_data["calls"] if c["call_type"] == "technical"]),
        "promotional_calls": len([c for c in seed_data["calls"] if c["call_type"] == "promotional"]),
        "avg_sentiment": sum(c["overall_sentiment"] for c in seed_data["calls"]) / len(seed_data["calls"]),
        "calls_by_profile": {},
        "calls_by_churn": {}
    }
    
    for call in seed_data["calls"]:
        stats["calls_by_profile"][call["customer_profile_type"]] = \
            stats["calls_by_profile"].get(call["customer_profile_type"], 0) + 1
        stats["calls_by_churn"][call["churn_risk"]] = \
            stats["calls_by_churn"].get(call["churn_risk"], 0) + 1
    
    print("\nSeed data statistics:")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()