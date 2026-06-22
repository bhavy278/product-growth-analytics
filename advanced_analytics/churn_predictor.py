import os
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report

# Global paths
MODEL_PATH = "/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics/advanced_analytics/churn_model.pkl"
LABEL_ENCODERS_PATH = "/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics/advanced_analytics/label_encoders.pkl"

def train_churn_model():
    """
    Queries database for paid users, engineers behavioral features,
    and trains a Random Forest Classifier to predict churn.
    """
    print("Training Churn Prediction Model...")
    db_url = "postgresql://postgres:postgres_password@localhost:5436/growth_analytics"
    engine = create_engine(db_url)
    
    # Query paid users features and target label
    # Target variable: churned (1 if status is 'cancelled', 0 if 'active')
    query = """
        with user_cohort as (
            select user_id, plan, status from stg_subscriptions
            where plan in ('Pro', 'Enterprise')
        ),
        user_channel as (
            select user_id, channel from dim_users
        ),
        user_sessions as (
            select
                user_id,
                count(distinct session_id) as session_count,
                extract(day from ('2026-06-22'::timestamp - max(session_start))) as recency,
                max(device_type) as device_type
            from fact_sessions
            group by user_id
        ),
        user_events as (
            select
                user_id,
                sum(case when event_type = 'search' then 1 else 0 end) as search_count,
                sum(case when event_type = 'page_view' then 1 else 0 end) as pv_count,
                count(event_id) as total_events
            from fact_events
            group by user_id
        ),
        user_payments as (
            select
                user_id,
                sum(amount) as total_revenue
            from fact_payments
            group by user_id
        )
        select
            c.user_id,
            c.plan,
            ch.channel,
            coalesce(s.session_count, 0) as session_count,
            coalesce(s.recency, 365) as recency,
            coalesce(s.device_type, 'Desktop') as device_type,
            coalesce(e.search_count, 0) as search_count,
            coalesce(e.pv_count, 0) as pv_count,
            coalesce(e.total_events, 0) as total_events,
            coalesce(p.total_revenue, 0.0) as total_revenue,
            case when c.status = 'cancelled' then 1 else 0 end as churned
        from user_cohort c
        join user_channel ch on c.user_id = ch.user_id
        left join user_sessions s on c.user_id = s.user_id
        left join user_events e on c.user_id = e.user_id
        left join user_payments p on c.user_id = p.user_id
    """
    
    df = pd.read_sql(query, engine)
    
    if len(df) < 50:
        print("Not enough dataset to train a robust model. Skipping training.")
        return
        
    # Features and Target
    X = df[['plan', 'channel', 'session_count', 'recency', 'device_type', 'search_count', 'pv_count', 'total_events', 'total_revenue']]
    y = df['churned']
    
    # Encode categorical variables
    encoders = {}
    X_encoded = X.copy()
    
    for col in ['plan', 'channel', 'device_type']:
        le = LabelEncoder()
        X_encoded[col] = le.fit_transform(X[col])
        encoders[col] = le
        
    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(X_encoded, y, test_size=0.2, random_state=42, stratify=y)
    
    # Train Random Forest Model
    model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Training Complete! Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save model and encoders
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoders, LABEL_ENCODERS_PATH)
    print(f"Model and Label Encoders successfully pickled and saved.")

def predict_single_user_churn(plan, channel, session_count, recency, device_type, search_count, pv_count, total_events, total_revenue):
    """
    Predicts the churn probability for a single user using pre-trained model.
    """
    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABEL_ENCODERS_PATH):
        # Fallback if model not trained yet
        # Higher recency and mobile device leads to higher churn probability
        base_prob = 0.15
        if recency > 90:
            base_prob += 0.55
        elif recency > 30:
            base_prob += 0.25
            
        if device_type == 'Mobile':
            base_prob += 0.15
            
        return min(0.95, max(0.05, base_prob))
        
    try:
        model = joblib.load(MODEL_PATH)
        encoders = joblib.load(LABEL_ENCODERS_PATH)
        
        # Build input row
        input_data = pd.DataFrame([{
            'plan': plan,
            'channel': channel,
            'session_count': session_count,
            'recency': recency,
            'device_type': device_type,
            'search_count': search_count,
            'pv_count': pv_count,
            'total_events': total_events,
            'total_revenue': total_revenue
        }])
        
        # Encode categorical variables using loaded encoders
        for col in ['plan', 'channel', 'device_type']:
            le = encoders[col]
            # Handle unseen labels by falling back to the first class if not found
            val = input_data.loc[0, col]
            if val in le.classes_:
                input_data.loc[0, col] = le.transform([val])[0]
            else:
                input_data.loc[0, col] = 0
                
        # Make prediction
        prob = model.predict_proba(input_data)[0][1]
        return float(prob)
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return 0.5

if __name__ == "__main__":
    train_churn_model()
