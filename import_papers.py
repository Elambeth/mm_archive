import sqlite3
import pandas as pd
from datetime import datetime

def format_filename(row):
    year = str(row[2])  # Column indices: 0=empty, 1=type, 2=year, 3=date, 4=institution, 5=title, 6=link
    title = row[5]
    # Format title to match JSON files
    formatted_title = (title.lower()
        .replace(' ', '_')
        .replace(',', '')
        .replace(':', '')
        .replace('"', '')
        .replace('?', '')
        .replace('&', 'and')
    )
    return f"{year}_{formatted_title}.json"

def parse_date(date_str, year):
    # Handle dates like "12/13" or "1/14"
    month, day = date_str.split('/')
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

def import_papers():
    # Read CSV without headers, using numbered columns
    df = pd.read_csv('mauboussin_papers.csv', header=None)
    
    with sqlite3.connect('mauboussin_archive.db') as conn:
        cur = conn.cursor()
        
        for index, row in df.iterrows():
            try:
                filename = format_filename(row)
                pub_date = parse_date(row[3], row[2])  # date, year
                
                print(f"Processing: {filename}")
                
                cur.execute("""
                    INSERT INTO papers 
                    (title, pub_date, pub_year, institution, document_type, original_url, filename)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row[5],    # title
                    pub_date,
                    row[2],    # year
                    row[4],    # institution
                    row[1],    # type
                    row[6],    # link
                    filename
                ))
                
            except Exception as e:
                print(f"Error processing row: {row[5]}")
                print(f"Error: {str(e)}")
        
        conn.commit()
        print("Papers imported successfully!")

if __name__ == "__main__":
    import_papers()