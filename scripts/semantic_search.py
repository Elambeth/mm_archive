import numpy as np
from openai import OpenAI
import psycopg2
from typing import List, Dict, Tuple
import re

class MauboussinSearch:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.db_params = {
            'dbname': 'mauboussin',
            'user': 'postgres',
            'password': 'alwayslearning',
            'host': 'localhost'
        }

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for input text"""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def parse_vector_string(self, vector_str: str) -> List[float]:
        """Convert string vector to list of floats"""
        clean_str = vector_str.strip('[]')
        return [float(x) for x in clean_str.split(',')]

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def clean_content(self, content: str) -> str:
        """Clean the content by removing boilerplate text and formatting"""
        # Remove copyright notices and headers
        content = re.sub(r'©.*?reserved\.', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'Exp\.\s+\d{1,2}/\d{1,2}/\d{4}', '', content)
        
        # Remove page numbers and excessive whitespace
        content = re.sub(r'\n\s*\d+\s*\n', '\n', content)
        
        # Remove Morgan Stanley references
        content = re.sub(r'Morgan Stanley\.?', '', content)
        
        # Clean up multiple newlines and spaces
        content = re.sub(r'\n\s*\n', '\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()

    def get_content_snippet(self, content: str, max_length: int = 500) -> str:
        """Get a meaningful content snippet of specified length"""
        # Clean the content first
        clean_content = self.clean_content(content)
        
        # If content is shorter than max_length, return it all
        if len(clean_content) <= max_length:
            return clean_content
        
        # Find a good breaking point near max_length
        end_pos = max_length
        while end_pos > max_length - 100 and end_pos < len(clean_content):
            if clean_content[end_pos] in '.!?':
                break
            end_pos += 1
        
        return clean_content[:end_pos + 1].strip()

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search for most relevant passages given a query"""
        query_embedding = self.get_embedding(query)

        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            # Get pages with their metadata and surrounding context
            cur.execute("""
                SELECT 
                    p.id, 
                    p.paper_id, 
                    p.page_number, 
                    p.content,
                    p.embedding,
                    papers.title, 
                    papers.year, 
                    papers.pdf_url,
                    LAG(p.content, 1) OVER (PARTITION BY p.paper_id ORDER BY p.page_number) as prev_page,
                    LEAD(p.content, 1) OVER (PARTITION BY p.paper_id ORDER BY p.page_number) as next_page
                FROM pages p
                JOIN papers ON p.paper_id = papers.id
                WHERE p.embedding IS NOT NULL
            """)
            
            results = []
            for row in cur.fetchall():
                (page_id, paper_id, page_num, content, embedding_str, 
                 title, year, pdf_url, prev_page, next_page) = row
                
                # Calculate similarity
                page_embedding = self.parse_vector_string(embedding_str)
                similarity = self.cosine_similarity(query_embedding, page_embedding)
                
                # Get clean content snippet
                content_snippet = self.get_content_snippet(content)
                
                # Only include context if it seems relevant
                context = ""
                if prev_page and similarity > 0.6:
                    context += "Previous page: " + self.get_content_snippet(prev_page, 200) + "\n\n"
                if next_page and similarity > 0.6:
                    context += "Next page: " + self.get_content_snippet(next_page, 200)
                
                results.append({
                    'page_id': page_id,
                    'paper_id': paper_id,
                    'page_number': page_num,
                    'content': content_snippet,
                    'context': context if context.strip() else None,
                    'title': title,
                    'year': year,
                    'pdf_url': pdf_url,
                    'similarity': similarity
                })

            # Sort by similarity and get top results
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:num_results]

        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

def main():
    OPENAI_API_KEY = ""  # Replace with your key
    searcher = MauboussinSearch(OPENAI_API_KEY)
    
    while True:
        # Get user input
        print("\nEnter your question about Mauboussin's work (or 'quit' to exit):")
        query = input("> ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
            
        if not query:
            continue
        
        # Search and display results
        results = searcher.search(query)
        
        print(f"\nTop results for query: '{query}'\n")
        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} (Similarity: {result['similarity']:.3f}) ---")
            print(f"Paper: {result['title']} ({result['year']})")
            print(f"Page: {result['page_number']}")
            print(f"Content:\n{result['content']}")
            
            if result.get('context'):
                print(f"\nContext:\n{result['context']}")
                
            print(f"\nPDF URL: {result['pdf_url']}")
            print("-" * 80)

if __name__ == "__main__":
    main()