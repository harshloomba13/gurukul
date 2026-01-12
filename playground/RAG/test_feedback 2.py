import sqlite3
import pandas as pd

conn = sqlite3.connect('default.sqlite')
feedback_df = pd.read_sql_query("""
    SELECT record_id, name, result, status 
    FROM trulens_feedbacks 
    WHERE result IS NOT NULL AND status != 'failed'
""", conn)

print('Valid feedbacks:', len(feedback_df))
print('Unique records with feedback:', feedback_df['record_id'].nunique())

feedback_pivot = feedback_df.pivot_table(
    index='record_id', 
    columns='name', 
    values='result', 
    aggfunc='first'
).reset_index()

print('Pivot shape:', feedback_pivot.shape)
print('Pivot columns:', list(feedback_pivot.columns))
print(feedback_pivot)

conn.close()