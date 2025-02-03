import psycopg2
from openai import OpenAI
from psycopg2.extras import execute_values
import time
from tqdm import tqdm
import tiktoken
import random
from datetime import datetime

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

def get_page_stats():
    """Get statistics about processed and unprocessed pages"""
    conn = connect_to_db()
    cur = conn.cursor()
    try:
        # Get total pages
        cur.execute("SELECT COUNT(*) FROM pages")
        total_pages = cur.fetchone()[0]
        
        # Get pages with embeddings
        cur.execute("SELECT COUNT(*) FROM pages WHERE embedding IS NOT NULL")
        processed_pages = cur.fetchone()[0]
        
        # Get pages without embeddings
        cur.execute("SELECT COUNT(*) FROM pages WHERE embedding IS NULL")
        unprocessed_pages = cur.fetchone()[0]
        
        return {
            'total': total_pages,
            'processed': processed_pages,
            'unprocessed': unprocessed_pages
        }
    finally:
        cur.close()
        conn.close()

def get_embedding_with_backoff(text, max_tokens=8191, timeout=30):
    """Get embedding with timeout"""
    if not text:
        return None
    
    # Count and limit tokens
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    n_tokens = len(tokens)
    
    if n_tokens > max_tokens:
        print(f"Warning: truncating text from {n_tokens} to {max_tokens} tokens")
        text = encoding.decode(tokens[:max_tokens])
    
    start_time = time.time()
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Embedding generation timed out after {timeout} seconds")
                
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

def process_pages():
    """Process pages without embeddings"""
    conn = connect_to_db()
    skipped_pages = []
    processed_count = 0
    
    try:
        cur = conn.cursor()
        
        # Get initial stats
        stats = get_page_stats()
        print("\nInitial Status:")
        print(f"Total pages in database: {stats['total']}")
        print(f"Pages already processed: {stats['processed']}")
        print(f"Pages to process: {stats['unprocessed']}")
        print("\nStarting processing...\n")
        
        progress_bar = tqdm(total=stats['unprocessed'], desc="Processing pages")
        
        while True:
            # Get next unprocessed page
            cur.execute("""
                SELECT id, paper_id, page_number, content 
                FROM pages 
                WHERE embedding IS NULL 
                LIMIT 1
            """)
            
            page = cur.fetchone()
            if not page:
                break
                
            page_id, paper_id, page_number, content = page
            
            try:
                if content and content.strip():
                    print(f"\nProcessing paper {paper_id}, page {page_number}")
                    embedding = get_embedding_with_backoff(content)
                    
                    if embedding:
                        cur.execute(
                            "UPDATE pages SET embedding = %s WHERE id = %s",
                            (embedding, page_id)
                        )
                        conn.commit()
                        processed_count += 1
                        print(f"Successfully processed paper {paper_id}, page {page_number}")
                    else:
                        print(f"Skipping empty content for paper {paper_id}, page {page_number}")
                        skipped_pages.append((paper_id, page_number, "Empty content"))
                        
                else:
                    print(f"Skipping empty page: paper {paper_id}, page {page_number}")
                    skipped_pages.append((paper_id, page_number, "Empty page"))
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error processing paper {paper_id}, page {page_number}: {error_msg}")
                skipped_pages.append((paper_id, page_number, error_msg))
                continue
            
            progress_bar.update(1)
            
        progress_bar.close()
        
        # Get final stats
        final_stats = get_page_stats()
        print("\nFinal Status:")
        print(f"Total pages in database: {final_stats['total']}")
        print(f"Successfully processed: {processed_count}")
        print(f"Pages skipped: {len(skipped_pages)}")
        print(f"Remaining unprocessed: {final_stats['unprocessed']}")
        
    finally:
        # Save skipped pages to file
        if skipped_pages:
            print("\nSkipped Pages Summary:")
            print("=====================")
            for paper_id, page_number, reason in skipped_pages:
                print(f"Paper {paper_id}, Page {page_number}: {reason}")
            
            with open('skipped_pages.txt', 'w') as f:
                f.write("Paper ID, Page Number, Reason\n")
                for paper_id, page_number, reason in skipped_pages:
                    f.write(f"{paper_id}, {page_number}, {reason}\n")
            print("\nSkipped pages have been saved to 'skipped_pages.txt'")
        
        conn.close()

if __name__ == "__main__":
    print("Starting embedding generation...")
    process_pages()
    print("\nFinished processing all pages!")