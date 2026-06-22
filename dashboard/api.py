import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine
import pandas as pd
import numpy as np

# Add parent directory to path to allow importing local modules
sys.path.append("/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics")

from pipelines.ab_testing import calculate_ab_metrics, run_chi_square
from advanced_analytics.cohort_analysis import calculate_cohort_retention
from advanced_analytics.segmentation import calculate_rfm_segments
from advanced_analytics.churn_predictor import predict_single_user_churn

app = FastAPI(title="Product Growth Analytics & A/B Testing Platform API")

# Database Connection
db_url = "postgresql://postgres:postgres_password@localhost:5436/growth_analytics"
engine = create_engine(db_url)

# Mount static files (like CSS) if needed
static_dir = "/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics/dashboard"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class ChurnPredictionRequest(BaseModel):
    plan: str
    channel: str
    session_count: int
    recency: int
    device_type: str
    search_count: int
    pv_count: int
    total_events: int
    total_revenue: float

class SimulationRequest(BaseModel):
    control_conversions: int
    control_size: int
    variant_conversions: int
    variant_size: int

@app.get("/")
def get_dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/kpis")
def get_kpis():
    try:
        # Total Users
        users_df = pd.read_sql("select count(*) as cnt from dim_users", engine)
        total_users = int(users_df.iloc[0]['cnt'])
        
        # Monthly Active Users (unique users in the last month of data)
        # We assume the max date in sessions is the simulation end: 2026-06-22
        active_users_df = pd.read_sql("""
            select 
                count(distinct user_id) as mau,
                count(distinct case when session_start >= '2026-06-15'::timestamp then user_id end) as wau,
                count(distinct case when session_start >= '2026-06-21'::timestamp then user_id end) as dau
            from fact_sessions
        """, engine)
        
        mau = int(active_users_df.iloc[0]['mau'])
        wau = int(active_users_df.iloc[0]['wau'])
        dau = int(active_users_df.iloc[0]['dau'])
        
        # Revenue metrics (from fact_payments)
        # MRR: monthly revenue in the last full month (e.g. May/June 2026)
        mrr_df = pd.read_sql("""
            select sum(amount) as mrr 
            from fact_payments 
            where payment_date >= '2026-05-22'::date
        """, engine)
        mrr = float(mrr_df.iloc[0]['mrr'] or 0.0)
        arr = mrr * 12
        
        # ARPU: Average revenue per active user (MRR / MAU)
        arpu = mrr / mau if mau > 0 else 0.0
        
        # Churn Rate: cancellations / total subscriptions (paid) in history
        churn_df = pd.read_sql("""
            select 
                count(case when status = 'cancelled' then 1 end) as churned,
                count(*) as total 
            from stg_subscriptions 
            where plan in ('Pro', 'Enterprise')
        """, engine)
        
        churned = int(churn_df.iloc[0]['churned'] or 0)
        total_paid = int(churn_df.iloc[0]['total'] or 0)
        churn_rate = (churned / total_paid * 100) if total_paid > 0 else 0.0
        
        # LTV: ARPU / Monthly Churn Rate (where Churn Rate is decimal)
        monthly_churn_decimal = (churn_rate / 100.0) / 12.0 # simplified monthly churn
        ltv = arpu / monthly_churn_decimal if monthly_churn_decimal > 0 else arpu * 24
        
        # Revenue by plan
        plan_rev_df = pd.read_sql("""
            select 
                sub.plan as label,
                sum(p.amount) as value
            from fact_payments p
            join stg_subscriptions sub on p.user_id = sub.user_id
            group by sub.plan
        """, engine)
        plan_revenue = plan_rev_df.to_dict(orient='records')
        
        # Revenue by channel
        channel_rev_df = pd.read_sql("""
            select 
                u.channel as label,
                sum(p.amount) as value
            from fact_payments p
            join dim_users u on p.user_id = u.user_id
            group by u.channel
        """, engine)
        channel_revenue = channel_rev_df.to_dict(orient='records')

        return {
            'total_users': total_users,
            'dau': dau,
            'wau': wau,
            'mau': mau,
            'mrr': mrr,
            'arr': arr,
            'arpu': arpu,
            'churn_rate': churn_rate,
            'ltv': ltv,
            'plan_revenue': plan_revenue,
            'channel_revenue': channel_revenue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/active-users")
def get_active_users():
    try:
        # month-by-month active users count (unique users in sessions)
        query = """
            select 
                to_char(session_start, 'YYYY-MM') as month,
                count(distinct user_id) as active_users
            from fact_sessions
            group by month
            order by month
        """
        df = pd.read_sql(query, engine)
        return df.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/funnels")
def get_funnels():
    try:
        # standard steps: Homepage view -> Signup event -> Login event -> Upgrade/Purchase event
        funnel_query = """
            with homepage_views as (
                select distinct user_id from fact_events where event_type = 'page_view'
            ),
            signups as (
                select distinct user_id from fact_events where event_type = 'signup'
            ),
            logins as (
                select distinct user_id from fact_events where event_type = 'login'
            ),
            upgrades as (
                select distinct user_id from fact_events where event_type in ('upgrade', 'purchase')
            )
            select
                (select count(*) from homepage_views) as homepage,
                (select count(*) from signups) as signup,
                (select count(*) from logins) as login,
                (select count(*) from upgrades) as upgrade
        """
        funnel_df = pd.read_sql(funnel_query, engine)
        
        steps = [
            {'step': '1. Homepage View', 'count': int(funnel_df.iloc[0]['homepage'])},
            {'step': '2. Account Signup', 'count': int(funnel_df.iloc[0]['signup'])},
            {'step': '3. Account Login', 'count': int(funnel_df.iloc[0]['login'])},
            {'step': '4. Paid Conversion', 'count': int(funnel_df.iloc[0]['upgrade'])}
        ]
        
        # Channel conversion analysis
        channel_conversions = pd.read_sql("""
            select 
                u.channel,
                count(distinct u.user_id) as total_users,
                count(distinct case when sub.plan in ('Pro', 'Enterprise') then u.user_id end) as paid_conversions
            from dim_users u
            left join stg_subscriptions sub on u.user_id = sub.user_id
            group by u.channel
        """, engine)
        
        channel_data = []
        for _, row in channel_conversions.iterrows():
            total = int(row['total_users'])
            paid = int(row['paid_conversions'])
            conv_rate = (paid / total * 100) if total > 0 else 0.0
            channel_data.append({
                'channel': row['channel'],
                'total_users': total,
                'paid_conversions': paid,
                'conversion_rate': float(conv_rate)
            })
            
        return {
            'steps': steps,
            'channels': channel_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cohorts")
def get_cohorts():
    try:
        matrix = calculate_cohort_retention()
        return matrix
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments")
def get_experiments():
    try:
        # Query experiment size and conversion rates
        # Variant conversion: user signed up, assigned to variant, and has upgrade subscription
        stats_query = """
            with exp_users as (
                select user_id, variant from dim_variants
            ),
            conversions as (
                select 
                    user_id,
                    max(case when plan in ('Pro', 'Enterprise') then 1 else 0 end) as converted
                from stg_subscriptions
                group by user_id
            )
            select 
                eu.variant,
                count(eu.user_id) as group_size,
                sum(coalesce(c.converted, 0)) as conversions
            from exp_users eu
            left join conversions c on eu.user_id = c.user_id
            group by eu.variant
        """
        
        df = pd.read_sql(stats_query, engine)
        
        control_size = 0
        control_conv = 0
        variant_size = 0
        variant_conv = 0
        
        for _, row in df.iterrows():
            if row['variant'] == 'Control':
                control_size = int(row['group_size'])
                control_conv = int(row['conversions'])
            elif row['variant'] == 'Variant':
                variant_size = int(row['group_size'])
                variant_conv = int(row['conversions'])
                
        metrics = calculate_ab_metrics(control_conv, control_size, variant_conv, variant_size)
        chi_stats = run_chi_square(control_conv, control_size, variant_conv, variant_size)
        
        return {
            'experiment_id': 'EXP_2026_CTA_COLOR',
            'control_size': control_size,
            'control_conversions': control_conv,
            'variant_size': variant_size,
            'variant_conversions': variant_conv,
            'z_test': metrics,
            'chi_square': chi_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/segments")
def get_segments():
    try:
        segments = calculate_rfm_segments()
        return segments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/predict-churn")
def predict_churn(req: ChurnPredictionRequest):
    try:
        prob = predict_single_user_churn(
            plan=req.plan,
            channel=req.channel,
            session_count=req.session_count,
            recency=req.recency,
            device_type=req.device_type,
            search_count=req.search_count,
            pv_count=req.pv_count,
            total_events=req.total_events,
            total_revenue=req.total_revenue
        )
        return {'churn_probability': float(prob)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate-experiment")
def simulate_experiment(req: SimulationRequest):
    try:
        metrics = calculate_ab_metrics(
            req.control_conversions,
            req.control_size,
            req.variant_conversions,
            req.variant_size
        )
        chi_stats = run_chi_square(
            req.control_conversions,
            req.control_size,
            req.variant_conversions,
            req.variant_size
        )
        return {
            'z_test': metrics,
            'chi_square': chi_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
