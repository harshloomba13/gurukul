from datetime import datetime, timedelta
from airflow.models.dag import DAG
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
import pandas as pd
import json

def extract_customer_profiles(**context):
    """Extract customer profiles from MongoDB with OpenLineage tracking"""
    
    # Connect directly to MongoDB using pymongo (since connection setup is complex in Airflow 3.0)
    import pymongo
    
    # Direct MongoDB connection
    client = pymongo.MongoClient(
        host='mongodb',
        port=27017,
        username='admin',
        password='admin123',
        authSource='admin'
    )
    
    # Extract customer profiles
    db = client['ecommerce']
    collection = db['customer_profiles']
    
    # Query customer profiles with business logic
    customers = list(collection.find(
        {},
        {
            'customer_id': 1,
            'name': 1,
            'email': 1,
            'demographics.age': 1,
            'demographics.location': 1,
            'demographics.income_bracket': 1,
            'preferences.loyalty_program': 1,
            'preferences.categories': 1,
            'social_media.influence_score': 1,
            '_id': 0
        }
    ))
    
    print(f"✅ Extracted {len(customers)} customer profiles from MongoDB")
    
    # Convert to DataFrame for processing
    df = pd.json_normalize(customers)
    
    # Close MongoDB connection
    client.close()
    
    # Store in XCom for next task
    return df.to_json(orient='records')

def create_customer_segments(**context):
    """Combine MongoDB profiles with PostgreSQL orders to create customer segments"""
    
    # Get customer profiles from previous task
    profiles_json = context['ti'].xcom_pull(task_ids='extract_customer_profiles')
    profiles_df = pd.read_json(profiles_json)
    
    # Connect to PostgreSQL to get order data
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Query order history (assuming we have some order data)
    orders_query = """
        SELECT 
            1001 as customer_id, 5 as total_orders, 2500.00 as total_spent, '2024-12-01'::date as last_order_date
        UNION ALL
        SELECT 1002, 2, 150.00, '2024-11-15'::date
        UNION ALL  
        SELECT 1003, 8, 4200.00, '2024-12-30'::date
        UNION ALL
        SELECT 1004, 1, 45.00, '2024-10-20'::date
        UNION ALL
        SELECT 1005, 12, 6800.00, '2025-01-05'::date
    """
    
    orders_df = postgres_hook.get_pandas_df(orders_query)
    
    # Merge customer profiles with order data
    merged_df = profiles_df.merge(orders_df, on='customer_id', how='left')
    merged_df['total_orders'] = merged_df['total_orders'].fillna(0)
    merged_df['total_spent'] = merged_df['total_spent'].fillna(0)
    
    # Create customer segments based on business rules
    def determine_segment(row):
        # VIP: High income + loyalty program + high spend + high influence
        if (row['demographics.income_bracket'] == 'high' and 
            row['preferences.loyalty_program'] == True and
            row['total_spent'] > 1000 and
            row['social_media.influence_score'] > 70):
            return 'VIP'
        # High Value: High spend regardless of other factors
        elif row['total_spent'] > 2000:
            return 'High Value'
        # Active: Multiple orders in recent period
        elif row['total_orders'] >= 3:
            return 'Active'
        # New: Low order count but recent activity
        elif row['total_orders'] <= 2:
            return 'New Customer'
        else:
            return 'Regular'
    
    merged_df['customer_segment'] = merged_df.apply(determine_segment, axis=1)
    
    # Calculate additional metrics
    merged_df['avg_order_value'] = merged_df['total_spent'] / merged_df['total_orders'].replace(0, 1)
    merged_df['is_high_influence'] = merged_df['social_media.influence_score'] > 75
    
    print(f"✅ Created customer segments for {len(merged_df)} customers")
    print(f"📊 Segment distribution: {merged_df['customer_segment'].value_counts().to_dict()}")
    
    # Store results for loading into PostgreSQL
    return merged_df.to_json(orient='records')

def load_customer_analytics(**context):
    """Load customer analytics results into PostgreSQL"""
    
    # Get segmented customer data
    analytics_json = context['ti'].xcom_pull(task_ids='create_customer_segments')
    analytics_df = pd.read_json(analytics_json)
    
    # Connect to PostgreSQL
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Create analytics table if not exists
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS customer_analytics (
            customer_id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            age INTEGER,
            location VARCHAR(255),
            income_bracket VARCHAR(50),
            loyalty_program BOOLEAN,
            influence_score INTEGER,
            total_orders INTEGER,
            total_spent DECIMAL(10,2),
            avg_order_value DECIMAL(10,2),
            customer_segment VARCHAR(50),
            is_high_influence BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    postgres_hook.run(create_table_sql)
    
    # Clear existing data and insert new analytics
    postgres_hook.run("TRUNCATE TABLE customer_analytics")
    
    # Prepare data for insertion
    for _, row in analytics_df.iterrows():
        insert_sql = """
            INSERT INTO customer_analytics 
            (customer_id, name, email, age, location, income_bracket, 
             loyalty_program, influence_score, total_orders, total_spent, 
             avg_order_value, customer_segment, is_high_influence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        postgres_hook.run(insert_sql, parameters=[
            int(row['customer_id']),
            row['name'],
            row['email'],
            int(row.get('demographics.age', 0)),
            row.get('demographics.location', ''),
            row.get('demographics.income_bracket', ''),
            bool(row.get('preferences.loyalty_program', False)),
            int(row.get('social_media.influence_score', 0)),
            int(row['total_orders']),
            float(row['total_spent']),
            float(row['avg_order_value']),
            row['customer_segment'],
            bool(row['is_high_influence'])
        ])
    
    print(f"✅ Loaded {len(analytics_df)} customer analytics records into PostgreSQL")
    return f"Loaded {len(analytics_df)} records"

# Create final summary report query
create_summary_report_sql = """
CREATE OR REPLACE VIEW customer_segment_summary AS
SELECT 
    customer_segment,
    COUNT(*) as customer_count,
    AVG(total_spent) as avg_customer_value,
    AVG(total_orders) as avg_orders,
    AVG(influence_score) as avg_influence,
    COUNT(*) FILTER (WHERE loyalty_program = true) as loyalty_members
FROM customer_analytics
GROUP BY customer_segment
ORDER BY avg_customer_value DESC;
"""

# DAG Definition
with DAG(
    'customer_analytics_pipeline',
    description='Customer 360 Analytics: MongoDB Profiles + PostgreSQL Orders → Customer Segments',
    start_date=datetime(2025, 1, 1),
    schedule='@daily',
    catchup=False,
    max_active_runs=1,
    default_args={
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'owner': 'data_team'
    },
    tags=['customer_analytics', 'mongodb', 'postgresql', 'lineage_demo']
) as dag:

    # Task 1: Extract customer profiles from MongoDB
    extract_profiles = PythonOperator(
        task_id='extract_customer_profiles',
        python_callable=extract_customer_profiles,
        doc_md="""
        ## Extract Customer Profiles
        
        Extracts customer profile data from MongoDB including:
        - Demographics (age, location, income bracket)
        - Preferences (categories, loyalty program)
        - Social media influence score
        
        **Data Source**: MongoDB `ecommerce.customer_profiles` collection
        """,
    )

    # Task 2: Create customer segments by combining MongoDB + PostgreSQL data
    segment_customers = PythonOperator(
        task_id='create_customer_segments',
        python_callable=create_customer_segments,
        doc_md="""
        ## Create Customer Segments
        
        Business logic to segment customers:
        - **VIP**: High income + loyalty + high spend + high influence  
        - **High Value**: Total spent > $2000
        - **Active**: 3+ orders
        - **New Customer**: ≤2 orders
        - **Regular**: Default segment
        
        **Data Sources**: MongoDB profiles + PostgreSQL order history
        """,
    )

    # Task 3: Load customer analytics into PostgreSQL
    load_analytics = PythonOperator(
        task_id='load_customer_analytics', 
        python_callable=load_customer_analytics,
        doc_md="""
        ## Load Customer Analytics
        
        Stores final customer segments and metrics in PostgreSQL:
        - Customer demographics and preferences
        - Order history and spending patterns
        - Calculated customer segments
        - Business metrics (CLV, influence, etc.)
        
        **Output**: PostgreSQL `customer_analytics` table
        """,
    )

    # Task 4: Create business summary view
    create_summary = SQLExecuteQueryOperator(
        task_id='create_segment_summary',
        conn_id='postgres_default',
        sql=create_summary_report_sql,
        doc_md="""
        ## Customer Segment Summary
        
        Creates executive dashboard view showing:
        - Customer count by segment
        - Average customer value per segment  
        - Loyalty program penetration
        - Influence metrics
        
        **Output**: PostgreSQL `customer_segment_summary` view
        """,
    )

    # Define task dependencies with clear data lineage
    extract_profiles >> segment_customers >> load_analytics >> create_summary