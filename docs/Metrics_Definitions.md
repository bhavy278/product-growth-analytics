# Metrics Definitions: Product Growth Analytics Platform

This document outlines the standard definitions, formulas, and analytics representations of KPIs tracked in this platform.

## 1. Growth Metrics

### Daily Active Users (DAU)
*   **Definition**: The count of unique users who initiated at least one session in a 24-hour window.
*   **Formula**:
    $$\text{DAU} = \text{Unique Count of } \texttt{user\_id} \text{ in } \texttt{fact\_sessions} \text{ where } \texttt{session\_start} \text{ matches date } T$$

### Weekly Active Users (WAU)
*   **Definition**: The count of unique users who initiated at least one session in a 7-day window.
*   **Formula**:
    $$\text{WAU} = \text{Unique Count of } \texttt{user\_id} \text{ in } \texttt{fact\_sessions} \text{ where } \texttt{session\_start} \in [T-6, T]$$

### Monthly Active Users (MAU)
*   **Definition**: The count of unique users who initiated at least one session in a 30-day window.
*   **Formula**:
    $$\text{MAU} = \text{Unique Count of } \texttt{user\_id} \text{ in } \texttt{fact\_sessions} \text{ where } \texttt{session\_start} \in [T-29, T]$$

### DAU / MAU Engagement Ratio
*   **Definition**: Measures product stickiness (the frequency with which active users return to the product).
*   **Formula**:
    $$\text{Engagement Ratio} = \left( \frac{\text{DAU}}{\text{MAU}} \right) \times 100$$

---

## 2. Conversion Metrics

### Landing-to-Signup Rate
*   **Definition**: Percentage of landing page visitors who register an account.
*   **Formula**:
    $$\text{Conversion Rate} = \left( \frac{\text{Count of users with event\_type = 'signup'}}{\text{Count of users with event\_type = 'page\_view'}} \right) \times 100$$

### Signup-to-Upgrade Rate
*   **Definition**: Percentage of registered users who upgrade to a paid plan.
*   **Formula**:
    $$\text{Upgrade Rate} = \left( \frac{\text{Count of paid subscription users}}{\text{Count of registered users}} \right) \times 100$$

---

## 3. Retention & Churn Metrics

### Cohort Retention Rate
*   **Definition**: The percentage of users in a signup cohort who return to use the product in subsequent periods.
*   **Formula**:
    $$\text{Retention Rate}_{\text{Month } N} = \left( \frac{\text{Active Users in Month } N \text{ belonging to Cohort } C}{\text{Total Signup Users in Cohort } C} \right) \times 100$$

### Paid Customer Churn Rate
*   **Definition**: The percentage of paid subscription users who cancel their subscriptions in a given month.
*   **Formula**:
    $$\text{Churn Rate} = \left( \frac{\text{Cancellations in Month } M}{\text{Active Paid Subscriptions at start of Month } M} \right) \times 100$$

---

## 4. Revenue Metrics

### Monthly Recurring Revenue (MRR)
*   **Definition**: Normalized monthly subscription revenue.
*   **Formula**:
    $$\text{MRR} = \sum (\text{Active Subscription Plan Prices})$$

### Annual Recurring Revenue (ARR)
*   **Definition**: Normalized yearly subscription revenue.
*   **Formula**:
    $$\text{ARR} = \text{MRR} \times 12$$

### Average Revenue Per User (ARPU)
*   **Definition**: The average revenue generated per active customer.
*   **Formula**:
    $$\text{ARPU} = \frac{\text{MRR}}{\text{MAU}}$$

### Customer Lifetime Value (LTV)
*   **Definition**: The projected revenue a customer will generate throughout their lifecycle.
*   **Formula**:
    $$\text{LTV} = \frac{\text{ARPU}}{\text{Monthly Churn Rate}}$$
