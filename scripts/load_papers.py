import json
import os
import psycopg2
from datetime import datetime
from psycopg2.extras import execute_values

# Database connection parameters
DB_PARAMS = {
    'dbname': 'mauboussin',
    'user': 'postgres',
    'password': 'alwayslearning',  # Replace with your password
    'host': 'localhost'
}

def connect_to_db():
    """Create database connection"""
    return psycopg2.connect(**DB_PARAMS)

def parse_date(date_str, year_str):
    """Parse date string like '12/13' with year into datetime"""
    if date_str and year_str:
        try:
            month, day = date_str.split('/')
            return f"{year_str}-{month}-{day}"
        except:
            return None
    return None

def load_paper(conn, json_file_path):
    """Load a single paper JSON file into the database"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cur = conn.cursor()
    try:
        # Extract paper ID from filename
        paper_id = data['filename'].split('_')[1]  # Gets 'xxx' from 'mm_xxx_...'
        
        # Insert paper
        csv_data = data['metadata']['csv_data']
        date_published = parse_date(csv_data.get('date'), csv_data.get('year'))
        
        cur.execute("""
            INSERT INTO papers (id, title, year, date_published, institution, 
                              original_filename, pdf_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                year = EXCLUDED.year,
                date_published = EXCLUDED.date_published,
                institution = EXCLUDED.institution,
                original_filename = EXCLUDED.original_filename,
                pdf_url = EXCLUDED.pdf_url,
                updated_at = CURRENT_TIMESTAMP
        """, (
            paper_id,
            csv_data.get('title'),
            csv_data.get('year'),
            date_published,
            csv_data.get('institution'),
            data['filename'],
            csv_data.get('url')
        ))

        # Insert tags
        for tag in data['metadata'].get('tags', []):
            # Insert tag if it doesn't exist
            cur.execute("""
                INSERT INTO tags (name)
                VALUES (%s)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
            """, (tag,))
            result = cur.fetchone()
            
            if result:
                tag_id = result[0]
            else:
                # Get existing tag id
                cur.execute("SELECT id FROM tags WHERE name = %s", (tag,))
                tag_id = cur.fetchone()[0]
            
            # Link tag to paper
            cur.execute("""
                INSERT INTO paper_tags (paper_id, tag_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (paper_id, tag_id))

        # Insert pages
        page_data = []
        for page in data['pages']:
            page_data.append((
                paper_id,
                page['number'],
                page['text']
            ))
        
        execute_values(cur, """
            INSERT INTO pages (paper_id, page_number, content)
            VALUES %s
            ON CONFLICT (paper_id, page_number) 
            DO UPDATE SET content = EXCLUDED.content
        """, page_data)

        # Insert other metadata
        for key, value in data['metadata'].items():
            if key not in ['csv_data', 'tags']:  # Skip already processed metadata
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                cur.execute("""
                    INSERT INTO paper_metadata (paper_id, key, value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (paper_id, key) DO UPDATE SET value = EXCLUDED.value
                """, (paper_id, key, str(value)))

        conn.commit()
        print(f"Successfully loaded paper {paper_id}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error loading paper {json_file_path}: {str(e)}")
        raise
    finally:
        cur.close()

def load_all_papers(json_dir):
    """Load all JSON files from a directory"""
    conn = connect_to_db()
    try:
        for filename in os.listdir(json_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(json_dir, filename)
                load_paper(conn, file_path)
    finally:
        conn.close()

if __name__ == "__main__":
    # Replace with your JSON files directory
    JSON_DIR = "C:/Users/elamb/OneDrive/Desktop/mm_archive/new_processed"
    load_all_papers(JSON_DIR)
    
    # After loading data, you might want to recreate the vector similarity index:
    conn = connect_to_db()
    cur = conn.cursor()
    try:
        cur.execute("DROP INDEX IF EXISTS idx_pages_embedding")
        cur.execute("""
            CREATE INDEX idx_pages_embedding ON pages 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()