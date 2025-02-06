import sqlite3
from sqlite3 import Error

def create_connection():
    """Create a database connection to the SQLite database"""
    try:
        conn = sqlite3.connect('call_center.db')
        print(f"Successfully connected to SQLite. SQLite version: {sqlite3.version}")
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_triggers(conn):
    """Create triggers for updating metrics tables"""
    try:
        cursor = conn.cursor()
        
        # Trigger to update real-time metrics
        update_current_metrics_trigger = '''
        CREATE TRIGGER IF NOT EXISTS update_current_metrics
        AFTER INSERT ON calls
        BEGIN
            -- Update current metrics
            UPDATE calls_metrics_current
            SET metric_timestamp = CURRENT_TIMESTAMP,
                active_calls_count = (
                    SELECT COUNT(*) FROM calls 
                    WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                ),
                avg_queue_time_last_5min = (
                    SELECT AVG(queue_time_seconds) FROM calls 
                    WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                ),
                avg_sentiment_last_5min = (
                    SELECT AVG(overall_sentiment) FROM calls 
                    WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                ),
                technical_calls_count = (
                    SELECT COUNT(*) FROM calls 
                    WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                    AND call_type = 'technical'
                ),
                promotional_calls_count = (
                    SELECT COUNT(*) FROM calls 
                    WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                    AND call_type = 'promotional'
                ),
                high_risk_calls_count = (
                    SELECT COUNT(*) FROM calls 
                    WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                    AND churn_risk = 'high'
                );
        END;
        '''
        
        # Trigger to update hourly metrics
        update_hourly_metrics_trigger = '''
        CREATE TRIGGER IF NOT EXISTS update_hourly_metrics
        AFTER INSERT ON calls
        BEGIN
            INSERT OR REPLACE INTO calls_hourly_metrics (
                hour_timestamp,
                total_calls,
                avg_queue_time,
                avg_sentiment,
                technical_calls_count,
                promotional_calls_count,
                high_risk_calls_count,
                avg_queue_time_technical,
                avg_queue_time_promotional
            )
            SELECT 
                datetime(strftime('%Y-%m-%d %H:00:00', NEW.timestamp)),
                COUNT(*),
                AVG(queue_time_seconds),
                AVG(overall_sentiment),
                SUM(CASE WHEN call_type = 'technical' THEN 1 ELSE 0 END),
                SUM(CASE WHEN call_type = 'promotional' THEN 1 ELSE 0 END),
                SUM(CASE WHEN churn_risk = 'high' THEN 1 ELSE 0 END),
                AVG(CASE WHEN call_type = 'technical' THEN queue_time_seconds END),
                AVG(CASE WHEN call_type = 'promotional' THEN queue_time_seconds END)
            FROM calls
            WHERE datetime(timestamp) >= datetime(strftime('%Y-%m-%d %H:00:00', NEW.timestamp))
            AND datetime(timestamp) < datetime(strftime('%Y-%m-%d %H:00:00', NEW.timestamp), '+1 hour')
            GROUP BY strftime('%Y-%m-%d %H', timestamp);
        END;
        '''
        
        # Trigger to update daily summary
        update_daily_summary_trigger = '''
        CREATE TRIGGER IF NOT EXISTS update_daily_summary
        AFTER INSERT ON calls
        BEGIN
            INSERT OR REPLACE INTO calls_daily_summary (
                date,
                total_calls,
                avg_queue_time,
                avg_sentiment,
                technical_calls_pct,
                high_risk_calls_pct,
                calls_by_profile_type,
                calls_by_churn_risk
            )
            SELECT 
                date(NEW.timestamp),
                COUNT(*),
                AVG(queue_time_seconds),
                AVG(overall_sentiment),
                CAST(SUM(CASE WHEN call_type = 'technical' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100,
                CAST(SUM(CASE WHEN churn_risk = 'high' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100,
                json_group_object(
                    customer_profile_type, 
                    COUNT(*)
                ),
                json_group_object(
                    churn_risk,
                    COUNT(*)
                )
            FROM calls
            WHERE date(timestamp) = date(NEW.timestamp)
            GROUP BY date(timestamp);
        END;
        '''
        
        # Execute creation of all triggers
        cursor.execute(update_current_metrics_trigger)
        cursor.execute(update_hourly_metrics_trigger)
        cursor.execute(update_daily_summary_trigger)
        
        conn.commit()
        print("Successfully created triggers")
        
    except Error as e:
        print(f"Error creating triggers: {e}")

def main():
    # Create connection
    conn = create_connection()
    
    if conn is not None:
        # Create triggers
        create_triggers(conn)
        
        # Close connection
        conn.close()
        print("Database connection closed")
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()