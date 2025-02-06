import sqlite3
from sqlite3 import Error
import os
import pandas as pd

def create_connection():
    """Create a database connection to a SQLite database"""
    if os.path.exists('call_center.db'):
        os.remove('call_center.db')
        print("Existing database removed.")
    
    try:
        conn = sqlite3.connect('call_center.db')
        print(f"Successfully connected to SQLite. SQLite version: {sqlite3.version}")
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_calls_table(conn):
    """Create the calls table"""
    try:
        cursor = conn.cursor()
        cursor.execute('''DROP TABLE IF EXISTS calls''')
        create_table_sql = '''
        CREATE TABLE calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_name TEXT NOT NULL,
            account_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            summary TEXT,
            call_type TEXT CHECK(call_type IN ('technical', 'promotional')),
            customer_profile_type TEXT CHECK(customer_profile_type IN ('high_value', 'value_seeker', 'new_convert', 'retention_required', 'basic_user')),
            churn_risk TEXT CHECK(churn_risk IN ('high', 'medium', 'low')),
            overall_sentiment REAL CHECK(overall_sentiment >= 0 AND overall_sentiment <= 1),
            queue_time_seconds INTEGER CHECK(queue_time_seconds >= 0)
        );
        '''
        cursor.execute(create_table_sql)
        print("Successfully created the calls table")
    except Error as e:
        print(f"Error creating calls table: {e}")

import sqlite3
from sqlite3 import Error
import os
import pandas as pd

def create_connection():
    """Create a database connection to a SQLite database"""
    if os.path.exists('call_center.db'):
        os.remove('call_center.db')
        print("Existing database removed.")
    
    try:
        conn = sqlite3.connect('call_center.db')
        print(f"Successfully connected to SQLite. SQLite version: {sqlite3.version}")
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_calls_table(conn):
    """Create the calls table"""
    try:
        cursor = conn.cursor()
        cursor.execute('''DROP TABLE IF EXISTS calls''')
        create_table_sql = '''
        CREATE TABLE calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_name TEXT NOT NULL,
            account_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            summary TEXT,
            call_type TEXT CHECK(call_type IN ('technical', 'promotional')),
            customer_profile_type TEXT CHECK(customer_profile_type IN ('high_value', 'value_seeker', 'new_convert', 'retention_required', 'basic_user')),
            churn_risk TEXT CHECK(churn_risk IN ('high', 'medium', 'low')),
            overall_sentiment REAL CHECK(overall_sentiment >= 0 AND overall_sentiment <= 1),
            queue_time_seconds INTEGER CHECK(queue_time_seconds >= 0)
        );
        '''
        cursor.execute(create_table_sql)
        print("Successfully created the calls table")
    except Error as e:
        print(f"Error creating calls table: {e}")

def create_metrics_table(conn):
    """Create and populate the metrics table with proper data types"""
    try:
        cursor = conn.cursor()
        cursor.execute('''DROP TABLE IF EXISTS metrics''')
        create_table_sql = '''
        CREATE TABLE metrics (
            fiscal_period DATE NOT NULL PRIMARY KEY,
            total_subscribers INTEGER NOT NULL CHECK(total_subscribers >= 0),
            total_monthly_revenue DECIMAL(10,2) NOT NULL CHECK(total_monthly_revenue >= 0),
            arpu DECIMAL(10,2) NOT NULL CHECK(arpu >= 0),
            avg_call_handling_time INTEGER NOT NULL CHECK(avg_call_handling_time >= 0),
            churn_rate DECIMAL(5,2) NOT NULL CHECK(churn_rate >= 0 AND churn_rate <= 100),
            campaign_engagement_percentage DECIMAL(5,2) NOT NULL CHECK(campaign_engagement_percentage >= 0 AND campaign_engagement_percentage <= 100),
            campaign_uptake_percentage DECIMAL(5,2) NOT NULL CHECK(campaign_uptake_percentage >= 0 AND campaign_uptake_percentage <= 100),
            campaign_uptake_target DECIMAL(5,2) CHECK(campaign_uptake_target IS NULL OR (campaign_uptake_target >= 0 AND campaign_uptake_target <= 100))
        );
        '''
        cursor.execute(create_table_sql)
        
        # First read everything as strings
        df = pd.read_csv('metrics.csv', dtype=str)
        
        # Print the first few fiscal period values for debugging
        print("Sample fiscal periods:", df['fiscal_period'].head().tolist())
        
        # Try to parse dates with multiple formats
        def parse_date(date_str):
            if pd.isna(date_str):
                return None
            
            date_formats = [
                '%Y-%m-%d',    # 2024-01-31
                '%m/%d/%Y',    # 1/31/2024
                '%m/%d/%y',    # 1/31/24
                '%b %Y',       # Jan 2024
                '%Y-%m'        # 2024-01
            ]
            
            for fmt in date_formats:
                try:
                    return pd.to_datetime(date_str, format=fmt).strftime('%Y-%m-%d')
                except:
                    continue
            
            # If no format works, try pandas' default parser
            try:
                return pd.to_datetime(date_str).strftime('%Y-%m-%d')
            except:
                print(f"Warning: Could not parse date: {date_str}")
                return None

        # Clean and convert fiscal_period
        df['fiscal_period'] = df['fiscal_period'].apply(parse_date)
        
        def clean_numeric(x):
            if pd.isna(x):
                return x
            # Remove commas, dollar signs, and whitespace
            x = str(x).replace(',', '').replace('$', '').strip()
            # Handle percentage values
            if '%' in x:
                return float(x.replace('%', ''))
            return x
        
        # Define column types and their cleaning approaches
        numeric_columns = {
            'total_subscribers': {'type': int, 'is_percentage': False},
            'total_monthly_revenue': {'type': float, 'is_percentage': False},
            'arpu': {'type': float, 'is_percentage': False},
            'avg_call_handling_time': {'type': int, 'is_percentage': False},
            'churn_rate': {'type': float, 'is_percentage': True},
            'campaign_engagement_percentage': {'type': float, 'is_percentage': True},
            'campaign_uptake_percentage': {'type': float, 'is_percentage': True},
            'campaign_uptake_target': {'type': float, 'is_percentage': True}
        }
        
        # Process each column based on its type
        for col, info in numeric_columns.items():
            df[col] = df[col].apply(clean_numeric)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if info['type'] == int:
                df[col] = df[col].astype(int)
        
        # Write to SQLite with proper types
        df.to_sql('metrics', conn, if_exists='replace', index=False,
                 dtype={
                     'fiscal_period': 'DATE',
                     'total_subscribers': 'INTEGER',
                     'total_monthly_revenue': 'DECIMAL(10,2)',
                     'arpu': 'DECIMAL(10,2)',
                     'avg_call_handling_time': 'INTEGER',
                     'churn_rate': 'DECIMAL(5,2)',
                     'campaign_engagement_percentage': 'DECIMAL(5,2)',
                     'campaign_uptake_percentage': 'DECIMAL(5,2)',
                     'campaign_uptake_target': 'DECIMAL(5,2)'
                 })
        
        print("Successfully created and populated the metrics table with proper data types")
        
    except Error as e:
        print(f"Error with metrics table: {e}")

def main():
    conn = create_connection()
    if conn is not None:
        create_calls_table(conn)
        create_metrics_table(conn)
        conn.close()
        print("Database connection closed")
    else:
        print("Error! Cannot create the database connection.")

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()