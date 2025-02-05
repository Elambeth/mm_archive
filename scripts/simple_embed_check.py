import psycopg2

DB_PARAMS = {
    'dbname': 'mauboussin',
    'user': 'postgres',
    'password': 'alwayslearning',
    'host': 'localhost'
}

def simple_check():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    try:
        # Simple check of one embedding
        cur.execute("""
            SELECT embedding 
            FROM pages 
            WHERE embedding IS NOT NULL 
            LIMIT 1;
        """)
        
        result = cur.fetchone()
        if result:
            embedding = result[0]
            print(f"Sample embedding found!")
            print(f"Type: {type(embedding)}")
            print(f"First few values: {str(embedding[:5])}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    simple_check()