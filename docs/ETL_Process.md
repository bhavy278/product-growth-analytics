# ETL Process: Product Growth Analytics Platform

This document describes the design, execution, validation rules, and loading steps of the Extraction, Transformation, and Loading (ETL) pipeline.

## 1. Pipeline Execution Flow

```text
    +------------------+
    |  generate_data   | ---> Generates synthetic SaaS data to raw/
    +--------+---------+
             |
             v
    +------------------+
    |    etl.py        | ---> Deduplication & Validation Checks
    +--------+---------+
             |
             v
    +------------------+
    |  PostgreSQL Stg  | ---> Loads raw_* tables (replace mode)
    +--------+---------+
             |
             v
    +------------------+
    |    dbt run       | ---> Builds fact_* and dim_* stars tables
    +------------------+
```

---

## 2. Validation & Quality Rules

To ensure analytics warehouse reliability, `pipelines/etl.py` executes data quality validation rules before staging:

### Churn / End Date Formatting
*   **Problem**: Subscription cancellations contain empty strings representing active subscriptions in the CSV files.
*   **Resolution**: Null or empty strings in `end_date` are standardized to `NaN` or SQL `NULL` values so date arithmetic does not fail.

### Negative/Invalid Billing Transactions
*   **Problem**: Transaction metrics may contain zero or negative values.
*   **Resolution**: Validates that all values in the payment amount column are positive:
    ```python
    df = df[df['amount'] > 0]
    ```

### Deduplication
*   **Problem**: Retries or server glitches can create duplicate database logs.
*   **Resolution**: Identifies and drops duplicate rows based on unique composite key fields:
    ```python
    df = df.drop_duplicates()
    ```

---

## 3. Data Quality Report

The pipeline writes a `data_quality_report.json` to the processed folder auditing key metrics:
*   `initial_row_count`: Number of rows in source csv.
*   `final_row_count`: Number of rows loaded to database.
*   `duplicate_rows_removed`: Count of exact duplicate rows.
*   `null_counts`: Audit of missing fields per column.
*   `null_rates`: Ratio of missing fields.
*   `validation_failures_removed`: Count of rows failed validation.

This provides full auditable transparency over data quality metrics.
