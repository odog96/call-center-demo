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

def create_metrics_tables_and_triggers(conn):
    """Create tables for real-time metrics, hourly aggregations, daily summaries, and their triggers"""
    try:
        cursor = conn.cursor()
        
        # Drop existing triggers first to avoid conflicts
        cursor.execute('DROP TRIGGER IF EXISTS update_current_metrics;')
        cursor.execute('DROP TRIGGER IF EXISTS update_hourly_metrics;')
        cursor.execute('DROP TRIGGER IF EXISTS update_daily_summary;')
        
        # Create real-time metrics table
        create_current_metrics_sql = '''
        CREATE TABLE IF NOT EXISTS calls_metrics_current (
            metric_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            active_calls_count INTEGER DEFAULT 0,
            avg_queue_time_last_5min REAL DEFAULT 0,
            avg_sentiment_last_5min REAL DEFAULT 0,
            technical_calls_count INTEGER DEFAULT 0,
            promotional_calls_count INTEGER DEFAULT 0,
            high_risk_calls_count INTEGER DEFAULT 0
        );
        '''
        
        # Create hourly metrics table
        create_hourly_metrics_sql = '''
        CREATE TABLE IF NOT EXISTS calls_hourly_metrics (
            hour_timestamp DATETIME PRIMARY KEY,
            total_calls INTEGER DEFAULT 0,
            avg_queue_time REAL DEFAULT 0,
            avg_sentiment REAL DEFAULT 0,
            technical_calls_count INTEGER DEFAULT 0,
            promotional_calls_count INTEGER DEFAULT 0,
            high_risk_calls_count INTEGER DEFAULT 0,
            avg_queue_time_technical REAL DEFAULT 0,
            avg_queue_time_promotional REAL DEFAULT 0
        );
        '''
        
        # Create daily summary table
        create_daily_summary_sql = '''
        CREATE TABLE IF NOT EXISTS calls_daily_summary (
            date DATE PRIMARY KEY,
            total_calls INTEGER DEFAULT 0,
            avg_queue_time REAL DEFAULT 0,
            avg_sentiment REAL DEFAULT 0,
            technical_calls_pct REAL DEFAULT 0,
            high_risk_calls_pct REAL DEFAULT 0,
            calls_by_profile_type TEXT,  -- JSON string storing profile type distribution
            calls_by_churn_risk TEXT     -- JSON string storing churn risk distribution
        );
        '''
        
        # Create trigger for real-time metrics
        create_current_metrics_trigger = '''
        CREATE TRIGGER update_current_metrics
        AFTER INSERT ON calls
        BEGIN
            UPDATE calls_metrics_current 
            SET 
                metric_timestamp = CURRENT_TIMESTAMP,
                active_calls_count = (
                    SELECT COUNT(id) FROM (
                        SELECT id FROM calls 
                        WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                    )
                ),
                avg_queue_time_last_5min = (
                    SELECT TOTAL(queue_time_seconds) * 1.0 / COUNT(id) FROM (
                        SELECT id, queue_time_seconds FROM calls 
                        WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                    )
                ),
                avg_sentiment_last_5min = (
                    SELECT TOTAL(overall_sentiment) * 1.0 / COUNT(id) FROM (
                        SELECT id, overall_sentiment FROM calls 
                        WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                    )
                ),
                technical_calls_count = (
                    SELECT COUNT(id) FROM (
                        SELECT id FROM calls 
                        WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                        AND call_type = 'technical'
                    )
                ),
                promotional_calls_count = (
                    SELECT COUNT(id) FROM (
                        SELECT id FROM calls 
                        WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                        AND call_type = 'promotional'
                    )
                ),
                high_risk_calls_count = (
                    SELECT COUNT(id) FROM (
                        SELECT id FROM calls 
                        WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
                        AND churn_risk = 'high'
                    )
                );
        END;
        '''
        
        # Create trigger for hourly metrics
        create_hourly_metrics_trigger = '''
        CREATE TRIGGER update_hourly_metrics
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
                (SELECT COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)),
                (SELECT TOTAL(queue_time_seconds) * 1.0 / COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)),
                (SELECT TOTAL(overall_sentiment) * 1.0 / COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)),
                (SELECT COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)
                 AND c2.call_type = 'technical'),
                (SELECT COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)
                 AND c2.call_type = 'promotional'),
                (SELECT COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)
                 AND c2.churn_risk = 'high'),
                (SELECT TOTAL(queue_time_seconds) * 1.0 / COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)
                 AND c2.call_type = 'technical'),
                (SELECT TOTAL(queue_time_seconds) * 1.0 / COUNT(*) FROM calls c2 
                 WHERE strftime('%Y-%m-%d %H', c2.timestamp) = strftime('%Y-%m-%d %H', NEW.timestamp)
                 AND c2.call_type = 'promotional');
        END;
        '''
        
        # Create trigger for daily summary
        create_daily_summary_trigger = '''
        CREATE TRIGGER update_daily_summary
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
                (SELECT COUNT(*) FROM calls c2 WHERE date(c2.timestamp) = date(NEW.timestamp)),
                (SELECT TOTAL(queue_time_seconds) * 1.0 / COUNT(*) FROM calls c2 
                 WHERE date(c2.timestamp) = date(NEW.timestamp)),
                (SELECT TOTAL(overall_sentiment) * 1.0 / COUNT(*) FROM calls c2 
                 WHERE date(c2.timestamp) = date(NEW.timestamp)),
                (SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM calls c3 
                 WHERE date(c3.timestamp) = date(NEW.timestamp))
                 FROM calls c2 WHERE date(c2.timestamp) = date(NEW.timestamp) 
                 AND c2.call_type = 'technical'),
                (SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM calls c3 
                 WHERE date(c3.timestamp) = date(NEW.timestamp))
                 FROM calls c2 WHERE date(c2.timestamp) = date(NEW.timestamp) 
                 AND c2.churn_risk = 'high'),
                (
                    SELECT json_group_array(
                        json_object(
                            'type', customer_profile_type,
                            'count', cnt
                        )
                    )
                    FROM (
                        SELECT customer_profile_type, COUNT(*) as cnt
                        FROM calls
                        WHERE date(timestamp) = date(NEW.timestamp)
                        GROUP BY customer_profile_type
                    )
                ),
                (
                    SELECT json_group_array(
                        json_object(
                            'risk', churn_risk,
                            'count', cnt
                        )
                    )
                    FROM (
                        SELECT churn_risk, COUNT(*) as cnt
                        FROM calls
                        WHERE date(timestamp) = date(NEW.timestamp)
                        GROUP BY churn_risk
                    )
                );
        END;
        '''
        
        # Execute all creation statements
        cursor.execute(create_current_metrics_sql)
        cursor.execute(create_hourly_metrics_sql)
        cursor.execute(create_daily_summary_sql)
        
        # Create triggers
        cursor.execute(create_current_metrics_trigger)
        cursor.execute(create_hourly_metrics_trigger)
        cursor.execute(create_daily_summary_trigger)
        
        # Initialize calls_metrics_current with a single row if it doesn't exist
        cursor.execute('''
        INSERT OR IGNORE INTO calls_metrics_current DEFAULT VALUES;
        ''')
        
        # Populate hourly metrics with historical data
        cursor.execute('''
        INSERT INTO calls_hourly_metrics (
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
            datetime(strftime('%Y-%m-%d %H:00:00', timestamp)),
            COUNT(*),
            TOTAL(queue_time_seconds) * 1.0 / COUNT(*),
            TOTAL(overall_sentiment) * 1.0 / COUNT(*),
            SUM(CASE WHEN call_type = 'technical' THEN 1 ELSE 0 END),
            SUM(CASE WHEN call_type = 'promotional' THEN 1 ELSE 0 END),
            SUM(CASE WHEN churn_risk = 'high' THEN 1 ELSE 0 END),
            TOTAL(CASE WHEN call_type = 'technical' THEN queue_time_seconds ELSE 0 END) * 1.0 / 
                NULLIF(SUM(CASE WHEN call_type = 'technical' THEN 1 ELSE 0 END), 0),
            TOTAL(CASE WHEN call_type = 'promotional' THEN queue_time_seconds ELSE 0 END) * 1.0 / 
                NULLIF(SUM(CASE WHEN call_type = 'promotional' THEN 1 ELSE 0 END), 0)
        FROM calls
        GROUP BY strftime('%Y-%m-%d %H', timestamp);
        ''')

        # Populate daily summary with historical data
        cursor.execute('''
        INSERT INTO calls_daily_summary (
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
            date(timestamp),
            COUNT(*),
            TOTAL(queue_time_seconds) * 1.0 / COUNT(*),
            TOTAL(overall_sentiment) * 1.0 / COUNT(*),
            SUM(CASE WHEN call_type = 'technical' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
            SUM(CASE WHEN churn_risk = 'high' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
            (
                SELECT json_group_array(
                    json_object(
                        'type', customer_profile_type,
                        'count', cnt
                    )
                )
                FROM (
                    SELECT customer_profile_type, COUNT(*) as cnt
                    FROM calls c2
                    WHERE date(c2.timestamp) = date(c1.timestamp)
                    GROUP BY customer_profile_type
                )
            ),
            (
                SELECT json_group_array(
                    json_object(
                        'risk', churn_risk,
                        'count', cnt
                    )
                )
                FROM (
                    SELECT churn_risk, COUNT(*) as cnt
                    FROM calls c2
                    WHERE date(c2.timestamp) = date(c1.timestamp)
                    GROUP BY churn_risk
                )
            )
        FROM calls c1
        GROUP BY date(timestamp);
        ''')

        # Update current metrics
        cursor.execute('''
        UPDATE calls_metrics_current
        SET metric_timestamp = CURRENT_TIMESTAMP,
            active_calls_count = (
                SELECT COUNT(*) FROM calls 
                WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
            ),
            avg_queue_time_last_5min = (
                SELECT TOTAL(queue_time_seconds) * 1.0 / COUNT(*) FROM calls 
                WHERE datetime(timestamp) >= datetime('now', '-5 minutes')
            ),
            avg_sentiment_last_5min = (
                SELECT TOTAL(overall_sentiment) * 1.0 / COUNT(*) FROM calls 
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
        ''')
        conn.commit()
        print("Successfully created metrics tables and triggers")
        
    except Error as e:
        print(f"Error creating metrics tables and triggers: {e}")

def main():
    # Create connection
    conn = create_connection()
    
    if conn is not None:
        # Create metrics tables and triggers
        create_metrics_tables_and_triggers(conn)
        
        # Close connection
        conn.close()
        print("Database connection closed")
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()