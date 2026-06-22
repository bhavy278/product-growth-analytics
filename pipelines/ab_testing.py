import numpy as np
from scipy import stats

def calculate_ab_metrics(control_conversions, control_size, variant_conversions=None, variant_size=None, variants=None):
    """
    Computes statistical significance metrics for an A/B or A/B/N test.
    Uses a Two-Proportion Z-Test.
    """
    # If control_size is 0, return fallback
    if control_size == 0:
        default_res = {
            'control_rate': 0.0,
            'variant_rate': 0.0,
            'lift_pct': 0.0,
            'z_score': 0.0,
            'p_value': 1.0,
            'ci_lower': 0.0,
            'ci_upper': 0.0,
            'significant': False
        }
        if variants is not None:
            return {'control_rate': 0.0, 'variants': []}
        return default_res

    p_c = control_conversions / control_size

    # Handle A/B/N case
    if variants is not None:
        n_comparisons = max(1, len(variants))
        alpha = 0.05
        # Bonferroni-adjusted critical Z-score
        # Two-tailed significance level: alpha / (2 * n_comparisons)
        # We want the Z-score corresponding to 1 - alpha / (2 * n_comparisons)
        z_crit = stats.norm.ppf(1.0 - (alpha / (2.0 * n_comparisons)))
        
        variant_results = []
        for var in variants:
            v_name = var['name']
            v_conv = var['conversions']
            v_size = var['size']
            
            if v_size == 0:
                variant_results.append({
                    'name': v_name, 'rate': 0.0, 'lift_pct': 0.0, 'z_score': 0.0,
                    'p_value': 1.0, 'ci_lower': 0.0, 'ci_upper': 0.0, 'significant': False
                })
                continue
                
            p_v = v_conv / v_size
            lift = (p_v - p_c) / p_c if p_c > 0 else 0.0
            lift_pct = lift * 100
            
            p_pool = (control_conversions + v_conv) / (control_size + v_size)
            if p_pool == 0 or p_pool == 1:
                z_score = 0.0
                p_val_nominal = 1.0
            else:
                se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / control_size + 1 / v_size))
                z_score = (p_v - p_c) / se_pool
                p_val_nominal = 2 * (1 - stats.norm.cdf(abs(z_score)))
                
            p_val_corrected = min(1.0, p_val_nominal * n_comparisons)
            
            se_diff = np.sqrt((p_c * (1 - p_c) / control_size) + (p_v * (1 - p_v) / v_size))
            margin_of_error = z_crit * se_diff
            
            ci_lower = (p_v - p_c) - margin_of_error
            ci_upper = (p_v - p_c) + margin_of_error
            
            variant_results.append({
                'name': v_name,
                'rate': float(p_v),
                'lift_pct': float(lift_pct),
                'z_score': float(z_score),
                'p_value': float(p_val_corrected),
                'ci_lower': float(ci_lower),
                'ci_upper': float(ci_upper),
                'significant': bool(p_val_corrected < alpha)
            })
            
        return {
            'control_rate': float(p_c),
            'variants': variant_results
        }
        
    # Standard A/B Case (single variant)
    else:
        v_conv = variant_conversions if variant_conversions is not None else 0
        v_size = variant_size if variant_size is not None else 0
        
        if v_size == 0:
            return {
                'control_rate': float(p_c),
                'variant_rate': 0.0,
                'lift_pct': 0.0,
                'z_score': 0.0,
                'p_value': 1.0,
                'ci_lower': 0.0,
                'ci_upper': 0.0,
                'significant': False
            }
            
        p_v = v_conv / v_size
        lift = (p_v - p_c) / p_c if p_c > 0 else 0.0
        lift_pct = lift * 100
        
        p_pool = (control_conversions + v_conv) / (control_size + v_size)
        if p_pool == 0 or p_pool == 1:
            z_score = 0.0
            p_value = 1.0
        else:
            se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / control_size + 1 / v_size))
            z_score = (p_v - p_c) / se_pool
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            
        se_diff = np.sqrt((p_c * (1 - p_c) / control_size) + (p_v * (1 - p_v) / v_size))
        margin_of_error = 1.96 * se_diff
        ci_lower = (p_v - p_c) - margin_of_error
        ci_upper = (p_v - p_c) + margin_of_error
        
        return {
            'control_rate': float(p_c),
            'variant_rate': float(p_v),
            'lift_pct': float(lift_pct),
            'z_score': float(z_score),
            'p_value': float(p_value),
            'ci_lower': float(ci_lower),
            'ci_upper': float(ci_upper),
            'significant': bool(p_value < 0.05)
        }

def run_chi_square(control_conversions, control_size, variant_conversions=None, variant_size=None, variants=None):
    """
    Runs a Chi-Square test of independence on A/B or A/B/N test results.
    """
    # Check for empty sizes
    if control_size == 0:
        return {'chi2': 0.0, 'p_value': 1.0, 'significant': False}
        
    contingency_rows = []
    
    # Control Row
    control_failures = control_size - control_conversions
    contingency_rows.append([control_conversions, control_failures])
    
    # Variant Rows
    if variants is not None:
        for var in variants:
            v_conv = var['conversions']
            v_size = var['size']
            if v_size == 0:
                return {'chi2': 0.0, 'p_value': 1.0, 'significant': False}
            v_failures = v_size - v_conv
            contingency_rows.append([v_conv, v_failures])
    else:
        v_conv = variant_conversions if variant_conversions is not None else 0
        v_size = variant_size if variant_size is not None else 0
        if v_size == 0:
            return {'chi2': 0.0, 'p_value': 1.0, 'significant': False}
        v_failures = v_size - v_conv
        contingency_rows.append([v_conv, v_failures])
        
    contingency_table = np.array(contingency_rows)
    
    if np.any(contingency_table < 0):
        return {'chi2': 0.0, 'p_value': 1.0, 'significant': False}
        
    try:
        chi2, p_val, dof, expected = stats.chi2_contingency(contingency_table)
        return {
            'chi2': float(chi2),
            'p_value': float(p_val),
            'significant': bool(p_val < 0.05)
        }
    except Exception as e:
        print(f"Chi-square calculation error: {e}")
        return {'chi2': 0.0, 'p_value': 1.0, 'significant': False}
