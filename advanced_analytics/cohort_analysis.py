import pandas as pd
from sqlalchemy import create_engine

def calculate_cohort_retention():
    """
    Computes a cohort retention matrix based on users and sessions tables.
    Calculations are performed in PostgreSQL to optimize execution speed.
    """
    db_url = "postgresql://postgres:postgres_password@localhost:5436/growth_analytics"
    engine = create_engine(db_url)
    
    query = """
        with cohort_sizes as (
            select 
                to_char(signup_date, 'YYYY-MM') as cohort_month, 
                count(distinct user_id) as cohort_size
            from dim_users
            group by cohort_month
        ),
        user_cohorts as (
            select 
                user_id, 
                to_char(signup_date, 'YYYY-MM') as cohort_month
            from dim_users
        ),
        session_months as (
            select distinct 
                user_id, 
                to_char(session_start, 'YYYY-MM') as session_month
            from fact_sessions
        ),
        cohort_index_counts as (
            select 
                c.cohort_month,
                (extract(year from to_date(s.session_month, 'YYYY-MM')) - extract(year from to_date(c.cohort_month, 'YYYY-MM'))) * 12 + 
                (extract(month from to_date(s.session_month, 'YYYY-MM')) - extract(month from to_date(c.cohort_month, 'YYYY-MM'))) as cohort_index,
                count(distinct s.user_id) as active_users
            from user_cohorts c
            join session_months s on c.user_id = s.user_id
            group by c.cohort_month, cohort_index
        )
        select 
            cic.cohort_month,
            cic.cohort_index,
            cic.active_users,
            cs.cohort_size
        from cohort_index_counts cic
        join cohort_sizes cs on cic.cohort_month = cs.cohort_month
        where cic.cohort_index >= 0
        order by cic.cohort_month, cic.cohort_index
    """
    
    df = pd.read_sql(query, engine)
    
    results = []
    for month, group in df.groupby('cohort_month'):
        cohort_size = int(group.iloc[0]['cohort_size'])
        retention_rates = {}
        for _, row in group.iterrows():
            idx = int(row['cohort_index'])
            active = int(row['active_users'])
            rate = active / cohort_size if cohort_size > 0 else 0.0
            retention_rates[str(idx)] = float(rate)
            
        results.append({
            'cohort_month': month,
            'cohort_size': cohort_size,
            'retention_rates': retention_rates
        })
        
    return sorted(results, key=lambda x: x['cohort_month'])
