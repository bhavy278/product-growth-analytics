# Dashboard Guide: Product Growth Analytics

The user interface is designed as an interactive web-based Business Intelligence (BI) dashboard implementing modern glassmorphism. It uses Chart.js for visualizations.

## 1. Dashboard Pages & Tabs

### Executive Summary
*   **Purpose**: Provides high-level KPIs for business performance (users, MRR, ARR, active ratio, LTV).
*   **Visuals**:
    *   **Active User Trends (MAU / WAU / DAU)**: Line chart tracking engagement growth.
    *   **Growth Segment Mix**: Horizontal bar chart displaying RFM segments.

### Conversion Funnel
*   **Purpose**: Pinpoints user drop-off bottlenecks.
*   **Visuals**:
    *   **Funnel Chart**: Horizontal bar chart visualizing the user flow (`page_view` -> `signup` -> `login` -> `upgrade`).
    *   **Conversion Rate by Channel**: Bar chart comparing channels.

### Cohort Retention
*   **Purpose**: Analyzes product stickiness over time.
*   **Visuals**:
    *   **Cohort Heatmap Table**: Styled grid displaying month-over-month retention rates colored using HSL transparency weights.
    *   **Retention Curves**: Multi-line chart illustrating retention decay across signup cohorts.

### MRR & ARR Analytics
*   **Purpose**: Displays subscription billing metrics.
*   **Visuals**:
    *   **Revenue by Subscription Plan**: Doughnut chart showing contribution share.
    *   **Revenue Share by Channel**: Pie chart illustrating customer LTV by channel.

### A/B Experiments
*   **Purpose**: Declares experimentation outcomes.
*   **Visuals**:
    *   **Conversion Rate Bar Chart**: Compares Control and Variant rates.
    *   **Stats Panel**: Real-time display of Z-score, P-value, and statistical significance badges.

### Analytics Tools
*   **Purpose**: Interactive growth simulation playground.
*   **Form Features**:
    *   **ML Churn Predictor Form**: Form to test customer churn probabilities with a visual risk bar (Low/Medium/High risk).
    *   **A/B Test Significance Simulator**: Form to calculate statistical significance on custom sample sizes and conversion rates.
