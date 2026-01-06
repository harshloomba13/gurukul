#!/usr/bin/env python3
"""Debug script to check TruLens data."""

import sqlite3
import pandas as pd

def debug_data():
    conn = sqlite3.connect('default.sqlite')
    
    print("=== RECORDS TABLE ===")
    records_df = pd.read_sql_query("""
        SELECT record_id, input, output 
        FROM trulens_records 
        ORDER BY ts
    """, conn)
    print("Records shape:", records_df.shape)
    print("Records columns:", list(records_df.columns))
    print("Sample records:")
    print(records_df)
    print()
    
    print("=== FEEDBACKS TABLE ===")
    feedback_df = pd.read_sql_query("""
        SELECT record_id, name, result
        FROM trulens_feedbacks
        WHERE result IS NOT NULL
        ORDER BY record_id
        LIMIT 10
    """, conn)
    print("Feedbacks shape:", feedback_df.shape)
    print("Feedbacks columns:", list(feedback_df.columns))
    print("Sample feedbacks:")
    print(feedback_df)
    print()
    
    print("=== PIVOT TEST ===")
    if not feedback_df.empty:
        feedback_pivot = feedback_df.pivot_table(
            index='record_id',
            columns='name',
            values='result',
            aggfunc='first'
        ).reset_index()
        print("Pivot shape:", feedback_pivot.shape)
        print("Pivot columns:", list(feedback_pivot.columns))
        print("Pivot data:")
        print(feedback_pivot)
        print()
        
        print("=== MERGE TEST ===")
        combined_df = records_df.merge(feedback_pivot, on='record_id', how='left')
        print("Combined shape:", combined_df.shape)
        print("Combined columns:", list(combined_df.columns))
        print("Combined data:")
        print(combined_df[['record_id', 'input', 'Answer Relevance', 'Context Relevance', 'Groundedness']])
        
        print("\n=== RECORDS WITH FEEDBACK ===")
        has_feedback = combined_df['Answer Relevance'].notna()
        print(f"Records with feedback: {has_feedback.sum()} out of {len(combined_df)}")
        if has_feedback.any():
            print(combined_df[has_feedback][['input', 'Answer Relevance', 'Context Relevance', 'Groundedness']])
    
    conn.close()

if __name__ == "__main__":
    debug_data()