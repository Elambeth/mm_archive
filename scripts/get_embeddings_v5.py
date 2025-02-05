import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI
from tqdm import tqdm
import time
from typing import List, Tuple

# Direct configuration - replace with your values
OPENAI_API_KEY = ""
DB_CONFIG = {
    "dbname": "mauboussin",  # Your database name
    "user": "postgres",      # Your postgres username
    "password": "alwayslearning",         # Your postgres password
    "host": "localhost",
    "port": "5432"
}

class EmbeddingProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()
        print("Connected to database successfully!")

    def get_pages_without_embeddings(self) -> List[Tuple[int, str]]:
        """Fetch all pages that don't have embeddings yet"""
        self.cur.execute("""
            SELECT id, content 
            FROM pages 
            WHERE embedding IS NULL
            ORDER BY id
        """)
        return self.cur.fetchall()

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API with rate limiting and retries"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"Failed to get embedding after {max_retries} attempts: {e}")
                    return None
                print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff

    def update_page_embedding(self, page_id: int, embedding: List[float]) -> bool:
        """Update a single page with its embedding"""
        try:
            self.cur.execute("""
                UPDATE pages 
                SET embedding = %s 
                WHERE id = %s
            """, (embedding, page_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating page {page_id}: {e}")
            return False

    def process_pages(self, batch_size: int = 10):
        """Process all pages without embeddings"""
        pages = self.get_pages_without_embeddings()
        if not pages:
            print("No pages found without embeddings.")
            return

        print(f"Found {len(pages)} pages without embeddings.")
        successful = 0
        failed = 0

        for page_id, content in tqdm(pages, desc="Processing pages"):
            # Clean content if necessary
            clean_content = content.strip()
            if not clean_content:
                print(f"Skipping page {page_id} - empty content")
                continue

            # Get embedding
            embedding = self.get_embedding(clean_content)
            if embedding is None:
                failed += 1
                continue

            # Update database
            if self.update_page_embedding(page_id, embedding):
                successful += 1
            else:
                failed += 1

            # Rate limiting
            time.sleep(0.1)  # Adjust based on your API limits

        print(f"\nProcessing complete:")
        print(f"Successfully processed: {successful}")
        print(f"Failed: {failed}")

    def close(self):
        """Close database connection"""
        self.cur.close()
        self.conn.close()

def main():
    processor = EmbeddingProcessor()
    try:
        processor.process_pages()
    finally:
        processor.close()

if __name__ == "__main__":
    main()