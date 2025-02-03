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

def count_tokens(text: str) -> int:
    """Count tokens in text using cl100k_base tokenizer"""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_embedding_with_backoff(text, max_tokens=8191, timeout=30):
    """Get embedding with timeout"""
    if not text:
        return None
    
    # Limit token count
    n_tokens = count_tokens(text)
    if n_tokens > max_tokens:
        print(f"Warning: truncating text from {n_tokens} to {max_tokens} tokens")
        encoding = tiktoken.get_encoding("cl100k_base")
        text = encoding.decode(encoding.encode(text)[:max_tokens])
    
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

def process_pages_in_batches(batch_size=1):
    """Process pages without embeddings in batches"""
    conn = connect_to_db()
    skipped_pages = []
    
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
                            print(f"\nProcessing paper {paper_id}, page {page_number}")
                            embedding = get_embedding_with_backoff(content)
                            
                            if embedding:
                                updates.append((page_id, embedding))
                                print(f"Successfully generated embedding for paper {paper_id}, page {page_number}")
                            else:
                                print(f"Skipping empty content for paper {paper_id}, page {page_number}")
                                skipped_pages.append((paper_id, page_number, "Empty content"))
                                
                    except Exception as e:
                        error_msg = str(e)
                        print(f"Error processing paper {paper_id}, page {page_number}: {error_msg}")
                        skipped_pages.append((paper_id, page_number, error_msg))
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
                time.sleep(0.1)  # Small delay between batches
        
    finally:
        # Print summary of skipped pages
        if skipped_pages:
            print("\nSkipped Pages Summary:")
            print("=====================")
            for paper_id, page_number, reason in skipped_pages:
                print(f"Paper {paper_id}, Page {page_number}: {reason}")
            
            print(f"\nTotal pages skipped: {len(skipped_pages)}")
            
            # Save skipped pages to file
            with open('skipped_pages.txt', 'w') as f:
                f.write("Paper ID, Page Number, Reason\n")
                for paper_id, page_number, reason in skipped_pages:
                    f.write(f"{paper_id}, {page_number}, {reason}\n")
            print("\nSkipped pages have been saved to 'skipped_pages.txt'")
            
        conn.close()

if __name__ == "__main__":
    print("Starting embedding generation...")
    process_pages_in_batches()
    print("Finished generating embeddings")
    print("Check skipped_pages.txt for a list of any pages that were skipped")