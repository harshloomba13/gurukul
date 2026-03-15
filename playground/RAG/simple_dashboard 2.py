#!/usr/bin/env python3
"""Simple dashboard to view TruLens data when the official dashboard has issues."""

import sqlite3
import pandas as pd
import streamlit as st
import json
import os

def load_trulens_data(db_path="default.sqlite"):
    """Load data from TruLens database."""
    conn = sqlite3.connect(db_path)
    
    # Get basic records
    records_df = pd.read_sql_query("""
        SELECT record_id, app_id, input, output, ts, record_json 
        FROM trulens_records 
        ORDER BY ts DESC
    """, conn)
    
    # Get feedback data - exclude failed evaluations
    try:
        feedback_df = pd.read_sql_query("""
            SELECT record_id, name, result, status
            FROM trulens_feedbacks
            WHERE result IS NOT NULL AND status != 'failed'
        """, conn)
    except Exception as e:
        st.warning(f"Could not load feedback data: {e}")
        feedback_df = pd.DataFrame()
    
    conn.close()
    return records_df, feedback_df

def parse_feedback_results(feedback_df):
    """Parse feedback results."""
    if feedback_df.empty:
        return pd.DataFrame()
    
    # The result is already a float score, so just pivot
    feedback_pivot = feedback_df.pivot_table(
        index='record_id',
        columns='name',
        values='result',
        aggfunc='first'
    ).reset_index()
    
    return feedback_pivot

def main():
    st.set_page_config(page_title="TruLens Data Viewer", layout="wide")
    st.title("🦑 TruLens Data Viewer")
    
    # Load data
    try:
        records_df, feedback_df = load_trulens_data()
        st.success(f"Loaded {len(records_df)} records")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    if records_df.empty:
        st.warning("No records found in database")
        return
    
    # Parse feedback
    feedback_pivot = parse_feedback_results(feedback_df)
    
    # Merge records with feedback
    if not feedback_pivot.empty:
        combined_df = records_df.merge(feedback_pivot, on='record_id', how='left')
        feedback_cols = [col for col in feedback_pivot.columns if col != 'record_id']
    else:
        combined_df = records_df
        feedback_cols = []
    
    # Display summary statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", len(combined_df))
    with col2:
        st.metric("Feedback Metrics", len(feedback_cols))
    with col3:
        if feedback_cols:
            avg_score = combined_df[feedback_cols].mean().mean()
            st.metric("Average Score", f"{avg_score:.3f}" if not pd.isna(avg_score) else "N/A")
    
    # Show feedback summary
    if feedback_cols:
        st.subheader("📊 Feedback Scores Summary")
        feedback_summary = combined_df[feedback_cols].describe()
        st.dataframe(feedback_summary)
        
        # Plot feedback scores
        st.subheader("📈 Feedback Scores Distribution")
        for col in feedback_cols:
            if combined_df[col].notna().any():
                st.write(f"**{col}**")
                hist_data = combined_df[col].dropna()
                st.histogram(hist_data, bins=20)
    
    # Show detailed records
    st.subheader("📋 Detailed Records")
    
    # Select columns to display
    display_cols = ['record_id', 'input', 'output'] + feedback_cols
    display_cols = [col for col in display_cols if col in combined_df.columns]
    
    # Add search/filter
    search_term = st.text_input("🔍 Search in questions and answers:")
    if search_term:
        mask = (
            combined_df['input'].str.contains(search_term, case=False, na=False) |
            combined_df['output'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = combined_df[mask]
    else:
        filtered_df = combined_df
    
    # Display records
    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True
    )
    
    # Show individual record details
    if st.checkbox("Show detailed record view"):
        record_idx = st.selectbox("Select record:", range(len(filtered_df)))
        if record_idx < len(filtered_df):
            record = filtered_df.iloc[record_idx]
            
            st.subheader(f"Record {record['record_id']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Question:**")
                st.write(record['input'])
            with col2:
                st.write("**Answer:**")
                st.write(record['output'])
            
            if feedback_cols:
                st.write("**Feedback Scores:**")
                for col in feedback_cols:
                    score = record.get(col)
                    if pd.notna(score):
                        st.metric(col, f"{score:.3f}")

if __name__ == "__main__":
    main()