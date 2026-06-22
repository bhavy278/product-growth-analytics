import os
import json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

def main():
    print("Initializing ETL Pipeline for Product Growth Analytics...")
    
    # Configure directories
    base_dir = "/Users/bhavy/Desktop/dev-space/antigravity-projects-2/product-growth-analytics"
    raw_dir = os.path.join(base_dir, "data", "raw")
    processed_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    
    # Database Connection
    db_url = "postgresql://postgres:postgres_password@localhost:5436/growth_analytics"
    engine = create_engine(db_url)
    
    datasets = ['users', 'sessions', 'events', 'subscriptions', 'payments', 'experiments']
    data_quality_report = {}
    
    for dataset in datasets:
        file_path = os.path.join(raw_dir, f"{dataset}.csv")
        if not os.path.exists(file_path):
            print(f"Error: Raw file {file_path} not found. Run generate_data first!")
            return
            
        print(f"Processing dataset: {dataset}...")
        df = pd.read_csv(file_path)
        
        # Data Quality Audits
        initial_row_count = len(df)
        null_counts = df.isnull().sum().to_dict()
        null_rates = (df.isnull().sum() / len(df)).to_dict()
        
        # Track and remove duplicates
        duplicate_count = df.duplicated().sum()
        df = df.drop_duplicates()
        
        # Handle specific columns/validation rules
        if dataset == 'payments':
            # Enforce positive amounts
            invalid_payments = len(df[df['amount'] <= 0])
            df = df[df['amount'] > 0]
        elif dataset == 'subscriptions':
            # Standardize end_date formatting
            df['end_date'] = df['end_date'].fillna('')
        elif dataset == 'users':
            # Clean missing plan types or country names
            df['plan_type'] = df['plan_type'].fillna('Free')
            df['country'] = df['country'].fillna('Unknown')
            
        final_row_count = len(df)
        
        # Log quality metrics
        data_quality_report[dataset] = {
            'initial_row_count': initial_row_count,
            'final_row_count': final_row_count,
            'duplicate_rows_removed': int(duplicate_count),
            'null_counts': null_counts,
            'null_rates': null_rates,
            'validation_failures_removed': int(initial_row_count - final_row_count - duplicate_count)
        }
        
        # Save to processed/ folder
        processed_path = os.path.join(processed_dir, f"clean_{dataset}.csv")
        df.to_csv(processed_path, index=False)
        print(f"  -> Saved clean file to {processed_path}")
        
        # Load into PostgreSQL staging tables
        table_name = f"raw_{dataset}"
        print(f"  -> Creating empty schema for table: {table_name}...")
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            conn.commit()
        # Use pandas to create schema (head of 0 rows)
        df.head(0).to_sql(table_name, engine, if_exists='replace', index=False)
        
        # Load using postgres COPY
        print(f"  -> Bulk copying data into PostgreSQL table: {table_name}...")
        raw_conn = engine.raw_connection()
        try:
            with raw_conn.cursor() as cur:
                with open(processed_path, 'r') as f:
                    cur.copy_expert(f"COPY {table_name} FROM STDIN WITH CSV HEADER", f)
            raw_conn.commit()
        finally:
            raw_conn.close()
        print(f"  -> Completed loading {table_name}.")

        
    # Save Data Quality Report
    report_path = os.path.join(processed_dir, "data_quality_report.json")
    with open(report_path, "w") as f:
        json.dump(data_quality_report, f, indent=4)
        
    print(f"ETL Pipeline completed successfully! Data quality report saved to {report_path}")

if __name__ == "__main__":
    main()

