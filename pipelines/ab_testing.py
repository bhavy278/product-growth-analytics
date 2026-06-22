import numpy as np
from scipy import stats

def calculate_ab_metrics(control_conversions, control_size, variant_conversions, variant_size):
    """
    Computes statistical significance metrics for an A/B test.
    Uses a Two-Proportion Z-Test.
    """
    if control_size == 0 or variant_size == 0:
        return {
            'control_rate': 0.0,
            'variant_rate': 0.0,
            'lift_pct': 0.0,
            'z_score': 0.0,
            'p_value': 1.0,
            'ci_lower': 0.0,
            'ci_upper': 0.0,
            'significant': False
        }
        
    p_c = control_conversions / control_size
    p_v = variant_conversions / variant_size
    
    # Lift
    lift = (p_v - p_c) / p_c if p_c > 0 else 0.0
    lift_pct = lift * 100
    
    # Z-Test for two proportions
    p_pool = (control_conversions + variant_conversions) / (control_size + variant_size)
    
    if p_pool == 0 or p_pool == 1:
        z_score = 0.0
        p_value = 1.0
    else:
        se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / control_size + 1 / variant_size))
        z_score = (p_v - p_c) / se_pool
        # Two-tailed test
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
    # Confidence Interval for difference (95% confidence)
    se_diff = np.sqrt((p_c * (1 - p_c) / control_size) + (p_v * (1 - p_v) / variant_size))
    margin_of_error = 1.96 * se_diff
    
    ci_lower = (p_v - p_c) - margin_of_error
    ci_upper = (p_v - p_c) + margin_of_error
    
    significant = p_value < 0.05
    
    return {
        'control_rate': float(p_c),
        'variant_rate': float(p_v),
        'lift_pct': float(lift_pct),
        'z_score': float(z_score),
        'p_value': float(p_value),
        'ci_lower': float(ci_lower),
        'ci_upper': float(ci_upper),
        'significant': bool(significant)
    }

def run_chi_square(control_conversions, control_size, variant_conversions, variant_size):
    """
    Runs a Chi-Square test of independence on A/B test results.
    """
    control_failures = control_size - control_conversions
    variant_failures = variant_size - variant_conversions
    
    contingency_table = np.array([
        [control_conversions, control_failures],
        [variant_conversions, variant_failures]
    ])
    
    # Check if we have enough sample sizes
    if np.any(contingency_table < 0) or control_size == 0 or variant_size == 0:
        return {
            'chi2': 0.0,
            'p_value': 1.0,
            'significant': False
        }
        
    chi2, p_val, dof, expected = stats.chi2_contingency(contingency_table)
    
    return {
        'chi2': float(chi2),
        'p_value': float(p_val),
        'significant': bool(p_val < 0.05)
    }
