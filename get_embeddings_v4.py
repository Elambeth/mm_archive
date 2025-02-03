import psycopg2
from openai import OpenAI
from psycopg2.extras import execute_values
import time
from tqdm import tqdm
import tiktoken
import random
import json
import logging
from datetime import datetime
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('embedding_process.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Database connection parameters
DB_PARAMS = {
    'dbname': 'mauboussin',
    'user': 'postgres',
    'password': 'alwayslearning',
    'host': 'localhost'
}

# Configuration
CONFIG = {
    'batch_size': 5,
    'max_tokens': 8191,
    'max_retries': 5,
    'base_delay': 1,
    'timeout': 30,  # seconds
    'max_page_time': 300,  # 5 minutes max per page
    'failed_pages_file': 'failed_pages.json'
}

# Initialize OpenAI client
client = OpenAI(api_key='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')

def connect_to_db():
    """Create database connection"""
    try:
        return psycopg2.connect(**DB_PARAMS)
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        raise

def load_failed_pages():
    """Load previously failed pages"""
    try:
        with open(CONFIG['failed_pages_file'], 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_failed_page(page_id, paper_id, page_number, error):
    """Save failed page to JSON file"""
    failed_pages = load_failed_pages()
    failed_pages[str(page_id)] = {
        'paper_id': paper_id,
        'page_number': page_number,
        'error': str(error),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(CONFIG['failed_pages_file'], 'w') as f:
        json.dump(failed_pages, f, indent=2)

def count_tokens(text: str) -> int:
    """Count tokens in text using cl100k_base tokenizer"""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_embedding_with_backoff(text, page_info=None):
    """Get embedding with improved error handling and timeouts"""
    if not text or not text.strip():
        return None
    
    # Count tokens and truncate if necessary
    n_tokens = count_tokens(text)
    if n_tokens > CONFIG['max_tokens']:
        logging.warning(f"Text has {n_tokens} tokens, truncating to {CONFIG['max_tokens']}")
        encoding = tiktoken.get_encoding("cl100k_base")
        text = encoding.decode(encoding.encode(text)[:CONFIG['max_tokens']])
    
    start_time = time.time()
    
    for attempt in range(CONFIG['max_retries']):
        try:
            # Check if we've exceeded max time for this page
            if time.time() - start_time > CONFIG['max_page_time']:
                raise TimeoutError(f"Processing time exceeded {CONFIG['max_page_time']} seconds")
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                timeout=CONFIG['timeout']
            )
            return response.data[0].embedding
            
        except Exception as e:
            if attempt == CONFIG['max_retries'] - 1:
                logging.error(f"Failed after {CONFIG['max_retries']} attempts: {str(e)}")
                if page_info:
                    save_failed_page(
                        page_info['id'],
                        page_info['paper_id'],
                        page_info['page_number'],
                        str(e)
                    )
                raise
            
            delay = CONFIG['base_delay'] * (2 ** attempt) + random.uniform(0, 0.1)
            logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.1f} seconds...")
            time.sleep(delay)

def process_pages_in_batches(start_page_id=None):
    """Process pages with improved error handling and resume capability"""
    conn = connect_to_db()
    try:
        cur = conn.cursor()
        
        # Get total count of remaining pages
        where_clause = "WHERE embedding IS NULL"
        if start_page_id:
            where_clause += f" AND id >= {start_page_id}"
        
        cur.execute(f"SELECT COUNT(*) FROM pages {where_clause}")
        total_pages = cur.fetchone()[0]
        logging.info(f"Found {total_pages} pages to process")
        
        if total_pages == 0:
            logging.info("No pages to process!")
            return
        
        # Process pages in batches
        with tqdm(total=total_pages, desc="Processing pages") as pbar:
            while True:
                # Get batch of pages
                cur.execute(f"""
                    SELECT id, paper_id, page_number, content 
                    FROM pages 
                    {where_clause}
                    ORDER BY id
                    LIMIT %s
                """, (CONFIG['batch_size'],))
                pages = cur.fetchall()
                
                if not pages:
                    break
                
                # Generate embeddings for batch
                updates = []
                for page_id, paper_id, page_number, content in pages:
                    page_info = {
                        'id': page_id,
                        'paper_id': paper_id,
                        'page_number': page_number
                    }
                    
                    try:
                        if content and content.strip():
                            embedding = get_embedding_with_backoff(content, page_info)
                            if embedding:
                                updates.append((page_id, embedding))
                                logging.info(f"Generated embedding for paper {paper_id}, page {page_number}")
                        else:
                            logging.warning(f"Skipping empty content for paper {paper_id}, page {page_number}")
                            save_failed_page(page_id, paper_id, page_number, "Empty content")
                            
                    except Exception as e:
                        logging.error(f"Error processing paper {paper_id}, page {page_number}: {str(e)}")
                        continue
                
                # Update database
                if updates:
                    try:
                        execute_values(
                            cur,
                            "UPDATE pages SET embedding = data.embedding FROM (VALUES %s) AS data (id, embedding) WHERE pages.id = data.id",
                            updates,
                            template="(%s, %s)"
                        )
                        conn.commit()
                        logging.info(f"Committed batch of {len(updates)} embeddings")
                    except Exception as e:
                        logging.error(f"Failed to update database: {str(e)}")
                        conn.rollback()
                
                pbar.update(len(pages))
                time.sleep(0.1)  # Small delay to avoid rate limits
        
    finally:
        conn.close()

def recreate_vector_index():
    """Recreate the vector similarity index"""
    conn = connect_to_db()
    cur = conn.cursor()
    try:
        logging.info("Recreating vector similarity index...")
        cur.execute("DROP INDEX IF EXISTS idx_pages_embedding")
        cur.execute("""
            CREATE INDEX idx_pages_embedding ON pages 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        conn.commit()
        logging.info("Vector similarity index recreated successfully!")
    except Exception as e:
        logging.error(f"Failed to recreate vector index: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process pages and generate embeddings')
    parser.add_argument('--resume', type=int, help='Resume from specific page ID')
    args = parser.parse_args()
    
    try:
        logging.info("Starting embedding generation...")
        process_pages_in_batches(start_page_id=args.resume)
        logging.info("Finished generating embeddings")
        
        logging.info("Recreating vector index...")
        recreate_vector_index()
        logging.info("Process completed successfully!")
        
    except KeyboardInterrupt:
        logging.info("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Process failed: {str(e)}")
        sys.exit(1)