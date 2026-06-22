import os
import random
import urllib.request
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def main():
    print("Initializing Data Generator for Product Growth Analytics & A/B Testing Platform...")
    
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample-size', type=str, default='25000', 
                        help='Number of users to sample from ab_data.csv, or "all" to use the entire dataset')
    args = parser.parse_args()
    
    # Set random seeds for reproducibility
    random.seed(42)
    np.random.seed(42)
    
    # Configure directories
    base_dir = "/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics"
    raw_dir = os.path.join(base_dir, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    
    ab_data_path = os.path.join(raw_dir, "ab_data.csv")
    
    # Download ab_data.csv if it does not exist
    if not os.path.exists(ab_data_path):
        url = "https://raw.githubusercontent.com/ozlerhakan/ab-test/master/ab_data.csv"
        print(f"Downloading {url} to {ab_data_path}...")
        try:
            urllib.request.urlretrieve(url, ab_data_path)
            print("Download successful!")
        except Exception as e:
            print(f"Error downloading Kaggle dataset: {e}")
            return
            
    # Load and clean ab_data.csv
    print(f"Loading Kaggle A/B Testing Dataset from {ab_data_path}...")
    df_ab = pd.read_csv(ab_data_path)
    
    # Clean mismatching rows: only keep old_page for control and new_page for treatment
    df_ab = df_ab[
        ((df_ab['group'] == 'control') & (df_ab['landing_page'] == 'old_page')) |
        ((df_ab['group'] == 'treatment') & (df_ab['landing_page'] == 'new_page'))
    ]
    
    # Drop duplicates by user_id
    df_ab = df_ab.drop_duplicates(subset=['user_id'])
    
    # Handle sample size
    total_users_available = len(df_ab)
    if args.sample_size.lower() == 'all':
        print(f"Using all {total_users_available} available users.")
    else:
        try:
            sample_size = int(args.sample_size)
            sample_size = min(sample_size, total_users_available)
            df_ab = df_ab.sample(n=sample_size, random_state=42)
            print(f"Sampled {sample_size} users from the original {total_users_available} users.")
        except ValueError:
            print(f"Invalid sample size '{args.sample_size}'. Defaulting to 25000 users.")
            df_ab = df_ab.sample(n=min(25000, total_users_available), random_state=42)
            
    # Simulation timeframe: 12 months (2025-06-22 to 2026-06-22)
    start_sim_date = datetime(2025, 6, 22)
    end_sim_date = datetime(2026, 6, 22)
    
    # Shift and scale timestamps of the Kaggle dataset to cover the entire simulation window
    df_ab['timestamp'] = pd.to_datetime(df_ab['timestamp'])
    orig_min = df_ab['timestamp'].min()
    orig_max = df_ab['timestamp'].max()
    orig_range = orig_max - orig_min
    target_range = end_sim_date - start_sim_date
    
    if orig_range.total_seconds() > 0:
        df_ab['scaled_date'] = start_sim_date + (df_ab['timestamp'] - orig_min) * (target_range.total_seconds() / orig_range.total_seconds())
    else:
        df_ab['scaled_date'] = start_sim_date
        
    users = []
    experiments = []
    subscriptions = []
    payments = []
    sessions = []
    events = []
    
    countries = ['US', 'US', 'US', 'US', 'CA', 'GB', 'DE']
    channels = ['Google', 'Google', 'Meta', 'Organic', 'Organic', 'Referral']
    device_types = ['Desktop', 'Desktop', 'Mobile', 'Mobile', 'Tablet']
    
    # Stats trackers
    sub_id_counter = 1
    pay_id_counter = 1
    session_id_counter = 1
    event_id_counter = 1
    
    print("Generating consistent relational entities based on A/B test data...")
    
    for _, row in df_ab.iterrows():
        user_id = f"USR_{row['user_id']}"
        signup_date = row['scaled_date']
        
        country = random.choice(countries)
        channel = random.choice(channels)
        
        # Determine experimental variant for users signing up on or after 2026-01-01
        is_experiment = signup_date >= datetime(2026, 1, 1)
        variant = 'N/A'
        
        if is_experiment:
            # Variant mapping: control -> Control, treatment -> Variant
            variant = 'Control' if row['group'] == 'control' else 'Variant'
            experiments.append({
                'experiment_id': 'EXP_2026_CTA_COLOR',
                'variant': variant,
                'user_id': user_id,
                'assigned_date': signup_date.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        # Conversion comes directly from the Kaggle converted column
        is_converted = row['converted'] == 1
        plan_type = 'Free'
        
        if is_converted:
            # Plan Choice: Pro vs Enterprise
            plan_type = 'Enterprise' if random.random() < 0.15 else 'Pro'
            
        users.append({
            'user_id': user_id,
            'signup_date': signup_date.strftime('%Y-%m-%d'),
            'country': country,
            'acquisition_channel': channel,
            'plan_type': plan_type
        })
        
        # Build Subscription history if converted
        if plan_type in ['Pro', 'Enterprise']:
            sub_start_date = signup_date + timedelta(days=random.randint(0, 3)) # upgrades shortly after signup
            status = 'active'
            sub_end_date = None
            
            # Simulate Churn based on attributes to introduce signals for ML
            # Churn signals: Mobile has higher churn, Referral has lower churn
            base_churn_prob = 0.05 if plan_type == 'Pro' else 0.02
            device_multiplier = 1.4 if random.choice(device_types) == 'Mobile' else 0.8
            channel_multiplier = 0.7 if channel == 'Referral' else 1.1
            monthly_churn_prob = base_churn_prob * device_multiplier * channel_multiplier
            
            # Check month-by-month if they churned before the end of simulation
            current_date = sub_start_date
            churned = False
            
            while current_date < end_sim_date and not churned:
                # Add payment for active month
                amount = 29.00 if plan_type == 'Pro' else 299.00
                payments.append({
                    'payment_id': f"PAY{pay_id_counter:05d}",
                    'user_id': user_id,
                    'amount': amount,
                    'payment_date': current_date.strftime('%Y-%m-%d')
                })
                pay_id_counter += 1
                
                # Check for churn at month end
                if random.random() < monthly_churn_prob:
                    churned = True
                    # Churn happens sometime in the next 30 days
                    churn_days = random.randint(5, 28)
                    sub_end_date = current_date + timedelta(days=churn_days)
                    if sub_end_date > end_sim_date:
                        sub_end_date = end_sim_date
                    status = 'cancelled'
                else:
                    current_date += timedelta(days=30)
            
            subscriptions.append({
                'subscription_id': f"SUB{sub_id_counter:04d}",
                'user_id': user_id,
                'plan': plan_type,
                'start_date': sub_start_date.strftime('%Y-%m-%d'),
                'end_date': sub_end_date.strftime('%Y-%m-%d') if sub_end_date else '',
                'status': status
            })
            sub_id_counter += 1
            
        else:
            # Free plan subscription
            subscriptions.append({
                'subscription_id': f"SUB{sub_id_counter:04d}",
                'user_id': user_id,
                'plan': 'Free',
                'start_date': signup_date.strftime('%Y-%m-%d'),
                'end_date': '',
                'status': 'active'
            })
            sub_id_counter += 1
            
        # Simulate Sessions & Events
        # Power users vs regular users: Churned or Free users have fewer sessions
        active_days = (end_sim_date - signup_date).days
        if plan_type in ['Pro', 'Enterprise'] and sub_end_date is None:
            # Active Paid: High activity
            session_freq = random.randint(8, 25) # sessions per month
        elif plan_type in ['Pro', 'Enterprise'] and sub_end_date is not None:
            # Churned: Active until cancellation, then dead
            active_days = (sub_end_date - signup_date).days
            session_freq = random.randint(4, 12)
        else:
            # Free plan: Lower activity
            session_freq = random.randint(2, 6)
            
        total_sessions = int((active_days / 30.0) * session_freq)
        total_sessions = max(1, total_sessions)
        
        session_dates = sorted([
            signup_date + timedelta(days=random.randint(0, max(1, active_days)))
            for _ in range(total_sessions)
        ])
        
        for sess_date in session_dates:
            session_id = f"SESS{session_id_counter:06d}"
            device = random.choice(device_types)
            
            # Session times
            start_hour = random.randint(0, 23)
            start_min = random.randint(0, 59)
            duration_mins = random.randint(2, 75)
            
            sess_start = sess_date.replace(hour=start_hour, minute=start_min, second=0)
            sess_end = sess_start + timedelta(minutes=duration_mins)
            
            sessions.append({
                'session_id': session_id,
                'user_id': user_id,
                'session_start': sess_start.strftime('%Y-%m-%d %H:%M:%S'),
                'session_end': sess_end.strftime('%Y-%m-%d %H:%M:%S'),
                'device_type': device
            })
            session_id_counter += 1
            
            # Generate events for this session
            sess_events = []
            
            # Check if this is the signup date session
            is_signup_session = sess_date.date() == signup_date.date()
            
            if is_signup_session:
                sess_events.append('page_view')
                sess_events.append('signup')
            else:
                sess_events.append('page_view')
                sess_events.append('login')
                
            # Random page view & search activity
            num_searches = random.randint(0, 4)
            for _ in range(num_searches):
                sess_events.append('search')
                
            # Add purchase and upgrade events if they match paid subscription start
            if plan_type in ['Pro', 'Enterprise']:
                sub_start = subscriptions[sub_id_counter - 2]['start_date']
                if sess_date.strftime('%Y-%m-%d') == sub_start:
                    sess_events.append('purchase')
                    sess_events.append('upgrade')
                    
            # Add cancel event if they match subscription end
            if plan_type in ['Pro', 'Enterprise'] and sub_end_date is not None:
                if sess_date.strftime('%Y-%m-%d') == sub_end_date.strftime('%Y-%m-%d'):
                    sess_events.append('cancel')
                    
            # Distribute events within the session duration
            for idx, event_type in enumerate(sess_events):
                offset_seconds = int((duration_mins * 60) * (idx + 1) / (len(sess_events) + 1))
                event_time = sess_start + timedelta(seconds=offset_seconds)
                
                events.append({
                    'event_id': f"EVT{event_id_counter:07d}",
                    'user_id': user_id,
                    'event_time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': event_type
                })
                event_id_counter += 1
                
    # Save datasets to data/raw
    print("Writing files to raw directory...")
    pd.DataFrame(users).to_csv(os.path.join(raw_dir, "users.csv"), index=False)
    pd.DataFrame(sessions).to_csv(os.path.join(raw_dir, "sessions.csv"), index=False)
    pd.DataFrame(events).to_csv(os.path.join(raw_dir, "events.csv"), index=False)
    pd.DataFrame(subscriptions).to_csv(os.path.join(raw_dir, "subscriptions.csv"), index=False)
    pd.DataFrame(payments).to_csv(os.path.join(raw_dir, "payments.csv"), index=False)
    pd.DataFrame(experiments).to_csv(os.path.join(raw_dir, "experiments.csv"), index=False)
    
    print("Data Generation Complete! Output files saved to data/raw:")
    print(f"  -> Users: {len(users)} rows")
    print(f"  -> Sessions: {len(sessions)} rows")
    print(f"  -> Events: {len(events)} rows")
    print(f"  -> Subscriptions: {len(subscriptions)} rows")
    print(f"  -> Payments: {len(payments)} rows")
    print(f"  -> Experiments: {len(experiments)} rows")

if __name__ == "__main__":
    main()
