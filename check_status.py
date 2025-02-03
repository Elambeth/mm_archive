import psycopg2

# Database connection parameters
DB_PARAMS = {
    'dbname': 'mauboussin',
    'user': 'postgres',
    'password': 'alwayslearning',
    'host': 'localhost'
}

def check_embedding_status():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    try:
        # Get total counts
        print("\nChecking database status...")
        
        # Total pages
        cur.execute("SELECT COUNT(*) FROM pages")
        total_pages = cur.fetchone()[0]
        print(f"Total pages in database: {total_pages}")
        
        # Pages with embeddings
        cur.execute("SELECT COUNT(*) FROM pages WHERE embedding IS NOT NULL")
        with_embeddings = cur.fetchone()[0]
        print(f"Pages with embeddings: {with_embeddings}")
        
        # Pages without embeddings
        cur.execute("SELECT COUNT(*) FROM pages WHERE embedding IS NULL")
        without_embeddings = cur.fetchone()[0]
        print(f"Pages without embeddings: {without_embeddings}")
        
        # Check most recent papers processed
        print("\nMost recently processed pages:")
        cur.execute("""
            SELECT paper_id, page_number 
            FROM pages 
            WHERE embedding IS NOT NULL 
            ORDER BY id DESC 
            LIMIT 5
        """)
        recent_pages = cur.fetchall()
        for paper_id, page_number in recent_pages:
            print(f"Paper {paper_id}, Page {page_number}")
            
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    check_embedding_status()