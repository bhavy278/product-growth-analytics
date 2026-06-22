# Data Model: Product Growth Analytics Platform

The analytics warehouse schema is designed as a **Star Schema** in PostgreSQL. This layout separates facts (transactional events and logs) from dimensions (reference attributes) to optimize analytical querying speeds.

```text
       +------------------+
       |    dim_plan      |
       +------------------+
       | plan_id (PK)     |
       | plan_name        |
       +--------+---------+
                |
                | 1
                |
                | M
      +---------+---------+               +------------------+
      |   fact_payments   | M           1 |     dim_user     |
      +------------------+----------------+------------------+
      | payment_id (PK)  |                | user_id (PK)     |
      | user_id (FK)     |                | signup_date      |
      | amount           |                | country          |
      | date_id (FK)     |                | channel          |
      | payment_date     |                | current_plan     |
      +---------+--------+                +--------+---------+
                |                                  |
                | M                                | 1
                |                                  |
                | 1                                | M
      +---------+--------+                +--------+---------+
      |    dim_date      | M            1 |  fact_sessions   |
      +------------------+----------------+------------------+
      | date_id (PK)     |                | session_id (PK)  |
      | date             |                | user_id (FK)     |
      | week             |                | duration_minutes |
      | month            |                | date_id (FK)     |
      | quarter          |                | session_start    |
      | year             |                | device_type      |
      +---------+--------+                +------------------+
                |
                | 1
                |
                | M
      +---------+---------+
      |    fact_events    |
      +-------------------+
      | event_id (PK)     |
      | user_id (FK)      |
      | event_type        |
      | date_id (FK)      |
      | event_time        |
      +-------------------+
```

---

## 1. Fact Tables

### `fact_sessions`
Tracks user sessions, durations, device details, and references dates.
*   `session_id` (`VARCHAR(50)`, PK): Unique session identifier.
*   `user_id` (`VARCHAR(50)`, FK): References `dim_users`.
*   `session_duration_minutes` (`NUMERIC`): Length of session in minutes.
*   `date_id` (`INTEGER`, FK): References `dim_dates`.
*   `session_start` (`TIMESTAMP`): Time session started.
*   `device_type` (`VARCHAR(20)`): Client device (Desktop, Mobile, Tablet).

### `fact_events`
Tracks specific behavioral milestones within the SaaS app.
*   `event_id` (`VARCHAR(50)`, PK): Unique event log identifier.
*   `user_id` (`VARCHAR(50)`, FK): References `dim_users`.
*   `event_type` (`VARCHAR(30)`): Logged event type (`page_view`, `signup`, `login`, `search`, `upgrade`, `cancel`, `purchase`).
*   `date_id` (`INTEGER`, FK): References `dim_dates`.
*   `event_time` (`TIMESTAMP`): Event timestamp.

### `fact_payments`
Stores billing transactions.
*   `payment_id` (`VARCHAR(50)`, PK): Transaction identifier.
*   `user_id` (`VARCHAR(50)`, FK): References `dim_users`.
*   `amount` (`NUMERIC`): Dollar value of the transaction.
*   `date_id` (`INTEGER`, FK): References `dim_dates`.
*   `payment_date` (`DATE`): Settlement date.

---

## 2. Dimension Tables

### `dim_users`
Reference details for customer attributes.
*   `user_id` (`VARCHAR(50)`, PK): Unique sequential customer identifier.
*   `signup_date` (`DATE`): Account signup date.
*   `country` (`VARCHAR(10)`): User location.
*   `channel` (`VARCHAR(30)`): Acquisition channel (`Google`, `Meta`, `Organic`, `Referral`).
*   `current_plan` (`VARCHAR(20)`): Subscription plan (`Free`, `Pro`, `Enterprise`).

### `dim_dates`
Dynamically populated date lookup table.
*   `date_id` (`INTEGER`, PK): Date key formatted as `YYYYMMDD`.
*   `date` (`DATE`): Calendar date.
*   `week` (`INTEGER`): Week number (1-53).
*   `month` (`INTEGER`): Month index (1-12).
*   `quarter` (`INTEGER`): Calendar quarter (1-4).
*   `year` (`INTEGER`): Calendar year.

### `dim_plans`
Subscription configuration properties.
*   `plan_id` (`INTEGER`, PK): Plan tier level.
*   `plan_name` (`VARCHAR(20)`): Tier name (Free, Pro, Enterprise).

### `dim_variants`
Stores experiment test group assignments.
*   `user_id` (`VARCHAR(50)`, PK): References `dim_users`.
*   `experiment_id` (`VARCHAR(50)`): Experiment name (`EXP_2026_CTA_COLOR`).
*   `variant` (`VARCHAR(20)`): Assigment label (`Control`, `Variant`).
*   `assigned_date` (`TIMESTAMP`): Assignment timestamp.
