import sys
from fastapi.testclient import TestClient

# Add parent directory to path to allow importing local modules
sys.path.append("/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics")

from dashboard.api import app

client = TestClient(app)

def test_kpis_endpoint():
    res = client.get("/api/kpis")
    assert res.status_code == 200
    data = res.json()
    assert 'total_users' in data
    assert 'mau' in data
    assert 'mrr' in data
    assert 'churn_rate' in data

def test_funnels_endpoint():
    res = client.get("/api/funnels")
    assert res.status_code == 200
    data = res.json()
    assert 'steps' in data
    assert 'channels' in data
    assert len(data['steps']) == 4

def test_cohorts_endpoint():
    res = client.get("/api/cohorts")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert 'cohort_month' in data[0]
        assert 'retention_rates' in data[0]

def test_experiments_endpoint():
    res = client.get("/api/experiments")
    assert res.status_code == 200
    data = res.json()
    assert 'control_size' in data
    assert 'z_test' in data
    assert 'chi_square' in data

def test_simulate_experiment_endpoint():
    payload = {
        "control_conversions": 80,
        "control_size": 1000,
        "variant_conversions": 120,
        "variant_size": 1000
    }
    res = client.post("/api/simulate-experiment", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data['z_test']['significant'] is True
    assert data['chi_square']['significant'] is True

def test_predict_churn_endpoint():
    payload = {
        "plan": "Pro",
        "channel": "Google",
        "session_count": 15,
        "recency": 2,
        "device_type": "Desktop",
        "search_count": 5,
        "pv_count": 10,
        "total_events": 30,
        "total_revenue": 58.0
    }
    res = client.post("/api/predict-churn", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert 'churn_probability' in data
    assert 0.0 <= data['churn_probability'] <= 1.0
