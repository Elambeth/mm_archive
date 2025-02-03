import psycopg2
from openai import OpenAI
from psycopg2.extras import execute_values
import time
from tqdm import tqdm
import tiktoken
import random

# Database connection parameters
DB_PARAMS = {
    'dbname': 'mauboussin',
    'user': 'postgres',
    'password': 'alwayslearning',
    'host': 'localhost'
}

# Initialize OpenAI client
client = OpenAI(api_key='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')

def connect_to_db():
    """Create database connection"""
    return psycopg2.connect(**DB_PARAMS)

def count_tokens(text: str) -> int:
    """Count tokens in text using cl100k_base tokenizer (used by text-embedding-3-small)"""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_embedding_with_backoff(text, max_tokens=8191):
    """Get embedding with exponential backoff retry logic and token limit handling"""
    if not text:
        return None
    
    # Count tokens
    n_tokens = count_tokens(text)
    if n_tokens > max_tokens:
        print(f"Warning: text has {n_tokens} tokens, truncating to {max_tokens}")
        encoding = tiktoken.get_encoding("cl100k_base")
        text = encoding.decode(encoding.encode(text)[:max_tokens])
    
    # Exponential backoff parameters
    max_retries = 5
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {str(e)}")
                raise
            
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
            print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.1f} seconds...")
            time.sleep(delay)

def process_pages_in_batches(batch_size=5):
    """Process pages without embeddings in batches"""
    conn = connect_to_db()
    try:
        cur = conn.cursor()
        
        # Get total count of pages without embeddings
        cur.execute("SELECT COUNT(*) FROM pages WHERE embedding IS NULL")
        total_pages = cur.fetchone()[0]
        print(f"Found {total_pages} pages without embeddings")
        
        if total_pages == 0:
            print("All pages already have embeddings!")
            return
        
        # Process pages in batches
        with tqdm(total=total_pages, desc="Processing pages") as pbar:
            while True:
                # Get batch of pages
                cur.execute("""
                    SELECT id, paper_id, page_number, content 
                    FROM pages 
                    WHERE embedding IS NULL 
                    LIMIT %s
                """, (batch_size,))
                pages = cur.fetchall()
                
                if not pages:
                    break
                
                # Generate embeddings for batch
                updates = []
                for page_id, paper_id, page_number, content in pages:
                    try:
                        if content and content.strip():
                            embedding = get_embedding_with_backoff(content)
                            if embedding:
                                updates.append((page_id, embedding))
                                print(f"Generated embedding for paper {paper_id}, page {page_number}")
                            else:
                                print(f"Skipping empty content for paper {paper_id}, page {page_number}")
                    except Exception as e:
                        print(f"Error processing paper {paper_id}, page {page_number}: {str(e)}")
                        continue
                
                # Update database
                if updates:
                    execute_values(
                        cur,
                        "UPDATE pages SET embedding = data.embedding FROM (VALUES %s) AS data (id, embedding) WHERE pages.id = data.id",
                        updates,
                        template="(%s, %s)"
                    )
                    
                    conn.commit()
                    print(f"Committed batch of {len(updates)} embeddings")
                
                pbar.update(len(pages))
                time.sleep(0.1)  # Small delay to avoid rate limits
        
    finally:
        conn.close()

def recreate_vector_index():
    """Recreate the vector similarity index"""
    conn = connect_to_db()
    cur = conn.cursor()
    try:
        print("Recreating vector similarity index...")
        cur.execute("DROP INDEX IF EXISTS idx_pages_embedding")
        cur.execute("""
            CREATE INDEX idx_pages_embedding ON pages 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        conn.commit()
        print("Vector similarity index recreated successfully!")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("Starting embedding generation...")
    process_pages_in_batches()
    print("Finished generating embeddings")
    
    print("Recreating vector index...")
    recreate_vector_index()
    print("Done!")