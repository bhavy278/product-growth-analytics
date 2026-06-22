import sys
sys.path.append("/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics")

import pytest
import numpy as np
from pipelines.ab_testing import calculate_ab_metrics, run_chi_square

def test_ab_metrics_standard():
    # Setup values with clear lift: Control 8% (80/1000) vs Variant 12% (120/1000)
    res = calculate_ab_metrics(
        control_conversions=80,
        control_size=1000,
        variant_conversions=120,
        variant_size=1000
    )
    
    assert res['control_rate'] == 0.08
    assert res['variant_rate'] == 0.12
    assert res['lift_pct'] == pytest.approx(50.0) # 0.12 is 50% lift over 0.08
    assert res['z_score'] > 0
    assert res['p_value'] < 0.05
    assert res['significant'] is True
    assert res['ci_lower'] > 0 # difference is positive and significant

def test_ab_metrics_no_difference():
    res = calculate_ab_metrics(
        control_conversions=50,
        control_size=1000,
        variant_conversions=50,
        variant_size=1000
    )
    
    assert res['control_rate'] == 0.05
    assert res['variant_rate'] == 0.05
    assert res['lift_pct'] == 0.0
    assert res['z_score'] == 0.0
    assert res['p_value'] == 1.0
    assert res['significant'] is False

def test_ab_metrics_empty():
    res = calculate_ab_metrics(
        control_conversions=0,
        control_size=0,
        variant_conversions=0,
        variant_size=0
    )
    
    assert res['control_rate'] == 0.0
    assert res['variant_rate'] == 0.0
    assert res['significant'] is False

def test_chi_square_independence():
    res = run_chi_square(
        control_conversions=80,
        control_size=1000,
        variant_conversions=120,
        variant_size=1000
    )
    
    assert res['chi2'] > 0
    assert res['p_value'] < 0.05
    assert res['significant'] is True
