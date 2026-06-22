import pandas as pd
from sqlalchemy import create_engine

def calculate_cohort_retention():
    """
    Computes a cohort retention matrix based on users and sessions tables.
    """
    db_url = "postgresql://postgres:postgres_password@localhost:5436/growth_analytics"
    engine = create_engine(db_url)
    
    # Query signup dates and session dates
    users_query = "select user_id, signup_date from dim_users"
    sessions_query = """
        select distinct 
            user_id, 
            to_char(session_start, 'YYYY-MM') as session_month
        from fact_sessions
    """
    
    df_users = pd.read_sql(users_query, engine)
    df_sessions = pd.read_sql(sessions_query, engine)
    
    # Parse dates
    df_users['signup_date'] = pd.to_datetime(df_users['signup_date'])
    df_users['cohort_month'] = df_users['signup_date'].dt.to_period('M')
    
    # Join users and sessions
    df_merged = pd.merge(df_sessions, df_users, on='user_id')
    
    # Parse session month
    df_merged['session_month_dt'] = pd.to_datetime(df_merged['session_month'] + '-01')
    df_merged['session_month_period'] = df_merged['session_month_dt'].dt.to_period('M')
    
    # Calculate period index (number of months active since signup)
    df_merged['cohort_index'] = (df_merged['session_month_period'] - df_merged['cohort_month']).apply(lambda x: x.n)
    
    # Filter out indexes before signup month (e.g. index < 0)
    df_merged = df_merged[df_merged['cohort_index'] >= 0]
    
    # Group by cohort_month and cohort_index
    cohort_group = df_merged.groupby(['cohort_month', 'cohort_index'])['user_id'].nunique().reset_index()
    
    # Pivot to get matrix
    cohort_matrix = cohort_group.pivot(index='cohort_month', columns='cohort_index', values='user_id')
    
    # Get actual cohort sizes (total users signed up in each cohort month)
    cohort_sizes = df_users.groupby('cohort_month')['user_id'].nunique()
    
    # Divide by cohort size to get percentages
    retention_matrix = cohort_matrix.divide(cohort_sizes, axis=0)
    
    # Convert indexes to string format for JSON response
    retention_matrix.index = retention_matrix.index.astype(str)
    cohort_sizes.index = cohort_sizes.index.astype(str)
    
    # Fill NaN values with 0.0
    retention_matrix = retention_matrix.fillna(0.0)
    
    # Build list structure for easy JSON usage
    results = []
    for month in retention_matrix.index:
        row = retention_matrix.loc[month].to_dict()
        results.append({
            'cohort_month': month,
            'cohort_size': int(cohort_sizes.loc[month]),
            'retention_rates': {str(k): float(v) for k, v in row.items()}
        })
        
    return results
