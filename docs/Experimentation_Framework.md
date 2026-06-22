# Experimentation Framework: Product Growth Analytics

This document details the statistical methodologies, metrics, and parameters behind the A/B testing engine implemented on this platform.

## 1. Experiment Overview

*   **Experiment ID**: `EXP_2026_CTA_COLOR`
*   **Hypothesis**: Changing the checkout Call-To-Action (CTA) button color from Blue (Control) to Green (Variant) decreases cognitive friction, leading to a statistically significant increase in the conversion upgrade rate.
*   **Target Population**: All users signing up on or after `2026-01-01`.
*   **Sample Split**: 50% Control, 50% Variant (randomly assigned).

---

## 2. Statistical Metrics & Mathematics

The platform computes the following A/B statistics via `pipelines/ab_testing.py`:

### Conversion Rate ($p$)
The proportion of users in a group who converted (upgraded to paid):
$$p = \frac{\text{Conversions}}{\text{Group Size}}$$

### Lift
The relative increase in conversion rate of the Variant group ($p_v$) compared to the Control group ($p_c$):
$$\text{Lift} = \frac{p_v - p_c}{p_c}$$

### Two-Proportion Z-Test
Used to determine if the difference in conversion rates between the groups is statistically significant:
1.  **Pooled Conversion Rate** ($p_{\text{pool}}$):
    $$p_{\text{pool}} = \frac{x_c + x_v}{n_c + n_v}$$
    Where $x_c, x_v$ are conversions, and $n_c, n_v$ are group sizes.
2.  **Pooled Standard Error** ($SE_{\text{pool}}$):
    $$SE_{\text{pool}} = \sqrt{p_{\text{pool}} \cdot (1 - p_{\text{pool}}) \cdot \left( \frac{1}{n_c} + \frac{1}{n_v} \right)}$$
3.  **Z-Score**:
    $$z = \frac{p_v - p_c}{SE_{\text{pool}}}$$
4.  **P-value** (Two-tailed):
    $$p\text{-value} = 2 \cdot (1 - \Phi(|z|))$$
    Where $\Phi$ is the Cumulative Distribution Function (CDF) of the standard normal distribution. If $p\text{-value} < 0.05$, we reject the null hypothesis and declare statistical significance.

### 95% Confidence Interval
Provides an interval estimation for the difference in proportions ($p_v - p_c$):
1.  **Standard Error of the Difference** ($SE_{\text{diff}}$):
    $$SE_{\text{diff}} = \sqrt{\frac{p_c \cdot (1 - p_c)}{n_c} + \frac{p_v \cdot (1 - p_v)}{n_v}}$$
2.  **95% Confidence Interval (CI)**:
    $$\text{CI} = (p_v - p_c) \pm (1.96 \cdot SE_{\text{diff}})$$
    If the interval does not contain $0.0$, the results are statistically significant.
