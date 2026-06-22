import os
import sys
import time
import queue
import uuid
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np

# Add parent directory to path to allow importing local modules
sys.path.append("/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics")

from pipelines.ab_testing import calculate_ab_metrics, run_chi_square
from advanced_analytics.cohort_analysis import calculate_cohort_retention
from advanced_analytics.segmentation import calculate_rfm_segments
from advanced_analytics.churn_predictor import predict_single_user_churn, get_feature_importances
from advanced_analytics.survival_analysis import calculate_survival_ltv

app = FastAPI(title="Vana | Growth Analytics & A/B Testing API")

# Database Connection
db_url = "postgresql://postgres:postgres_password@localhost:5436/growth_analytics"
engine = create_engine(db_url)

# In-Memory Event Ingestion Buffer
class EventBuffer:
    def __init__(self, db_engine, batch_size=50, flush_interval=5.0):
        self.engine = db_engine
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue = queue.Queue()
        self.last_flush = time.time()
        self.lock = threading.Lock()
        
        # Periodic background flush thread
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()
        
    def add_event(self, user_id: str, event_type: str, event_time: str = None):
        if not event_time:
            event_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        event_id = f"EVT_{uuid.uuid4().hex[:8].upper()}"
        
        self.queue.put({
            'event_id': event_id,
            'user_id': user_id,
            'event_time': event_time,
            'event_type': event_type
        })
        
    def _worker_loop(self):
        while True:
            time.sleep(0.5)
            qsize = self.queue.qsize()
            elapsed = time.time() - self.last_flush
            
            if qsize >= self.batch_size or (qsize > 0 and elapsed >= self.flush_interval):
                self.flush()
                
    def flush(self):
        with self.lock:
            batch = []
            while not self.queue.empty():
                try:
                    batch.append(self.queue.get_nowait())
                except queue.Empty:
                    break
            
            if not batch:
                return
                
            self.last_flush = time.time()
            
            # SQL Bulk Insert
            try:
                with self.engine.begin() as conn:
                    stmt = text("INSERT INTO raw_events (event_id, user_id, event_time, event_type) VALUES (:event_id, :user_id, :event_time, :event_type)")
                    conn.execute(stmt, batch)
                print(f"[EventBuffer] Successfully flushed {len(batch)} events to raw_events table.")
            except Exception as e:
                print(f"[EventBuffer] Error flushing batch to database: {e}")

event_buffer = EventBuffer(engine)

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

class TrackRequest(BaseModel):
    user_id: str
    event_type: str
    event_time: str = None

class VariantInput(BaseModel):
    name: str
    conversions: int
    size: int

class SimulationRequest(BaseModel):
    control_conversions: int
    control_size: int
    variant_conversions: int = None
    variant_size: int = None
    variants: list[VariantInput] = None

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
            select
                count(distinct case when event_type = 'page_view' then user_id end) as homepage,
                count(distinct case when event_type = 'signup' then user_id end) as signup,
                count(distinct case when event_type = 'login' then user_id end) as login,
                count(distinct case when event_type in ('upgrade', 'purchase') then user_id end) as upgrade
            from fact_events
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
        
        control_row = df[df['variant'] == 'Control']
        control_size = int(control_row.iloc[0]['group_size']) if not control_row.empty else 0
        control_conv = int(control_row.iloc[0]['conversions']) if not control_row.empty else 0
        
        treatment_rows = df[(df['variant'] != 'Control') & (df['variant'] != 'N/A')]
        
        variants_list = []
        for _, row in treatment_rows.iterrows():
            variants_list.append({
                'name': row['variant'],
                'size': int(row['group_size']),
                'conversions': int(row['conversions'])
            })
            
        # Legacy single-variant support
        first_variant_name = 'Variant'
        first_variant_size = 0
        first_variant_conv = 0
        if len(variants_list) > 0:
            first_variant_name = variants_list[0]['name']
            first_variant_size = variants_list[0]['size']
            first_variant_conv = variants_list[0]['conversions']
            
        legacy_metrics = calculate_ab_metrics(control_conv, control_size, first_variant_conv, first_variant_size)
        legacy_chi_stats = run_chi_square(control_conv, control_size, first_variant_conv, first_variant_size)
        
        # Multi-variant metrics
        multi_metrics = calculate_ab_metrics(control_conv, control_size, variants=variants_list)
        multi_chi_stats = run_chi_square(control_conv, control_size, variants=variants_list)
        
        return {
            'experiment_id': 'EXP_2026_CTA_COLOR',
            'control_size': control_size,
            'control_conversions': control_conv,
            'variant_size': first_variant_size,
            'variant_conversions': first_variant_conv,
            'z_test': legacy_metrics,
            'chi_square': legacy_chi_stats,
            'variants': multi_metrics.get('variants', []),
            'global_chi_square': multi_chi_stats
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
        if req.variants is not None and len(req.variants) > 0:
            variants_list = [{'name': v.name, 'conversions': v.conversions, 'size': v.size} for v in req.variants]
            multi_metrics = calculate_ab_metrics(req.control_conversions, req.control_size, variants=variants_list)
            multi_chi_stats = run_chi_square(req.control_conversions, req.control_size, variants=variants_list)
            
            first_v = variants_list[0]
            legacy_metrics = calculate_ab_metrics(req.control_conversions, req.control_size, first_v['conversions'], first_v['size'])
            legacy_chi_stats = run_chi_square(req.control_conversions, req.control_size, first_v['conversions'], first_v['size'])
            
            return {
                'z_test': legacy_metrics,
                'chi_square': legacy_chi_stats,
                'variants': multi_metrics.get('variants', []),
                'global_chi_square': multi_chi_stats
            }
        else:
            v_conv = req.variant_conversions if req.variant_conversions is not None else 0
            v_size = req.variant_size if req.variant_size is not None else 0
            metrics = calculate_ab_metrics(req.control_conversions, req.control_size, v_conv, v_size)
            chi_stats = run_chi_square(req.control_conversions, req.control_size, v_conv, v_size)
            return {
                'z_test': metrics,
                'chi_square': chi_stats
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/churn-features")
def get_churn_features():
    try:
        importances = get_feature_importances()
        return importances
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/track")
def track_event(req: TrackRequest):
    try:
        event_buffer.add_event(req.user_id, req.event_type, req.event_time)
        return {"status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/survival-ltv")
def get_survival_ltv():
    try:
        data = calculate_survival_ltv()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
