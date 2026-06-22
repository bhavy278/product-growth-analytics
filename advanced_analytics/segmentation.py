import pandas as pd
import numpy as np
from sqlalchemy import create_engine

def calculate_rfm_segments():
    """
    Performs Recency, Frequency, and Monetary (RFM) analysis on users
    and classifies them into growth segments.
    """
    db_url = "postgresql://postgres:postgres_password@localhost:5436/growth_analytics"
    engine = create_engine(db_url)
    
    # Query sessions and payments aggregated by user
    query = """
        with recency_freq as (
            select
                user_id,
                extract(day from ('2026-06-22'::timestamp - max(session_start))) as recency,
                count(distinct session_id) as frequency
            from fact_sessions
            group by user_id
        ),
        monetary as (
            select
                user_id,
                sum(amount) as monetary
            from fact_payments
            group by user_id
        ),
        user_info as (
            select user_id, current_plan from dim_users
        )
        select
            u.user_id,
            u.current_plan,
            coalesce(rf.recency, 365) as recency,
            coalesce(rf.frequency, 0) as frequency,
            coalesce(m.monetary, 0.0) as monetary
        from user_info u
        left join recency_freq rf on u.user_id = rf.user_id
        left join monetary m on u.user_id = m.user_id
    """
    
    df = pd.read_sql(query, engine)
    
    # Define Segment Logic based on thresholds
    # Recency: < 30 days is Active, > 90 days is Inactive/At-Risk
    # Frequency: > 50 sessions is High Frequency, < 10 is Low Frequency
    # Monetary: Enterprise is High Value, Pro is Moderate Value, Free is 0
    
    def assign_segment(row):
        r = row['recency']
        f = row['frequency']
        m = row['monetary']
        plan = row['current_plan']
        
        if plan == 'Enterprise' and r < 30:
            return 'High-Value Champions'
        elif r < 14 and f > 40:
            return 'Power Users'
        elif r < 45 and plan in ['Pro', 'Enterprise']:
            return 'Loyal Customers'
        elif r > 90 and plan in ['Pro', 'Enterprise']:
            return 'At-Risk (Paid Churned)'
        elif r > 60:
            return 'Hibernating / Dormant'
        elif plan == 'Free' and f > 15:
            return 'Engaged Free Users'
        else:
            return 'New / Average Users'
            
    df['segment'] = df.apply(assign_segment, axis=1)
    
    # Calculate aggregate counts
    agg_df = df.groupby('segment').agg(
        user_count=('user_id', 'count'),
        avg_recency=('recency', 'mean'),
        avg_frequency=('frequency', 'mean'),
        avg_monetary=('monetary', 'mean')
    ).reset_index()
    
    # Sort by size
    agg_df = agg_df.sort_values(by='user_count', ascending=False)
    
    return agg_df.to_dict(orient='records')
