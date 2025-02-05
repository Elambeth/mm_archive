import numpy as np
from openai import OpenAI
import psycopg2
from typing import List, Dict
import re
import os
from dotenv import load_dotenv

class MauboussinGPT:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get API keys from environment
        openai_api_key = os.getenv('OPENAI_API_KEY')
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        
        if not openai_api_key or not deepseek_api_key:
            raise ValueError("Missing required API keys in environment variables")
        
        # OpenAI client for embeddings
        self.embedding_client = OpenAI(api_key=openai_api_key)
        
        # Deepseek client for chat
        self.chat_client = OpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com"
        )
        
        # Database connection parameters from environment variables
        self.db_params = {
            'dbname': os.getenv('DB_NAME', 'mauboussin'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'alwayslearning'),
            'host': os.getenv('DB_HOST', 'localhost')
        }
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        response = self.embedding_client.embeddings.create(
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
        content = re.sub(r'\n\s*\d+\s*\n', '\n', content)
        content = re.sub(r'Morgan Stanley\.?', '', content)
        
        # Remove header/footer noise
        content = re.sub(r'^.*(?=\n\n)', '', content)  # Remove first line if followed by double newline
        content = re.sub(r'\n.*$', '', content)        # Remove last line
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()

    def get_content_snippet(self, content: str, max_length: int = 1500) -> str:
        """Get a meaningful content snippet of specified length"""
        # Clean the content first
        clean_content = self.clean_content(content)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in clean_content.split('\n') if p.strip()]
        
        # Filter out short lines (likely headers) and keep substantive paragraphs
        substantive_paragraphs = [p for p in paragraphs if len(p) > 50]
        
        if not substantive_paragraphs:
            return clean_content[:max_length]
            
        # Combine paragraphs up to max_length
        result = []
        current_length = 0
        
        for para in substantive_paragraphs:
            if current_length + len(para) + 2 <= max_length:  # +2 for newline
                result.append(para)
                current_length += len(para) + 2
            else:
                # If we can't fit the whole paragraph, add as much as we can
                space_left = max_length - current_length
                if space_left > 100:  # Only add partial paragraph if we can add something substantial
                    result.append(para[:space_left] + '...')
                break
                
        return '\n\n'.join(result)

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search for most relevant passages given a query"""
        query_embedding = self.get_embedding(query)

        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            # Get pages with context from surrounding pages
            cur.execute("""
                WITH RankedPages AS (
                    SELECT 
                        p.id, 
                        p.paper_id, 
                        p.page_number, 
                        p.content,
                        p.embedding,
                        papers.title, 
                        papers.year, 
                        papers.pdf_url,
                        LAG(p.content) OVER (PARTITION BY p.paper_id ORDER BY p.page_number) as prev_content,
                        LEAD(p.content) OVER (PARTITION BY p.paper_id ORDER BY p.page_number) as next_content
                    FROM pages p
                    JOIN papers ON p.paper_id = papers.id
                    WHERE p.embedding IS NOT NULL
                )
                SELECT * FROM RankedPages
            """)
            
            results = []
            for row in cur.fetchall():
                (page_id, paper_id, page_num, content, embedding_str, 
                 title, year, pdf_url, prev_content, next_content) = row
                
                # Calculate similarity
                page_embedding = self.parse_vector_string(embedding_str)
                similarity = self.cosine_similarity(query_embedding, page_embedding)
                
                # Get content with context
                main_content = self.get_content_snippet(content)
                context = ""
                
                if prev_content and similarity > 0.6:
                    prev_snippet = self.get_content_snippet(prev_content, 300)
                    if prev_snippet:
                        context += f"Previous page: {prev_snippet}\n\n"
                        
                if next_content and similarity > 0.6:
                    next_snippet = self.get_content_snippet(next_content, 300)
                    if next_snippet:
                        context += f"Next page: {next_snippet}"
                
                results.append({
                    'page_id': page_id,
                    'paper_id': paper_id,
                    'page_number': page_num,
                    'content': main_content,
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

    def create_prompt(self, query: str, search_results: List[Dict]) -> str:
        """Create a prompt for Deepseek using the search results"""
        prompt = f"""You are an AI assistant specialized in Michael Mauboussin's work. 
Answer the following question using ONLY the provided excerpts from his papers.

Question: {query}

Here are relevant excerpts from Mauboussin's papers:

"""
        for i, result in enumerate(search_results, 1):
            prompt += f"""
Excerpt {i} (from "{result['title']}", {result['year']}, page {result['page_number']}):
{result['content']}

"""
            if result.get('context'):
                prompt += f"Additional context:\n{result['context']}\n\n"

        prompt += """
Please provide a comprehensive answer that:
1. Synthesizes information from the provided excerpts
2. Uses specific quotes when appropriate (with paper title and year)
3. Cites the specific paper, year, and page number for key points
4. Maintains academic rigor while being accessible
5. Acknowledges any limitations if the provided excerpts don't fully answer the question

Answer:"""

        return prompt

    def generate_answer(self, prompt: str) -> str:
        """Generate answer using Deepseek"""
        try:
            response = self.chat_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are an AI assistant specialized in Michael Mauboussin's work."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def answer_question(self, query: str) -> Dict:
        """Complete pipeline: search -> create prompt -> generate answer"""
        # Get relevant passages
        search_results = self.search(query)
        
        # Create prompt
        prompt = self.create_prompt(query, search_results)
        
        # Generate answer
        answer = self.generate_answer(prompt)
        
        # Return both answer and sources
        return {
            'answer': answer,
            'sources': [
                {
                    'title': r['title'],
                    'year': r['year'],
                    'page': r['page_number'],
                    'url': r['pdf_url'],
                    'excerpt': r['content'][:200] + '...' if len(r['content']) > 200 else r['content']
                }
                for r in search_results
            ]
        }

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize bot without passing API key since it's now handled in __init__
    bot = MauboussinGPT()
    
    while True:
        print("\nAsk a question about Mauboussin's work (or 'quit' to exit):")
        query = input("> ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
            
        if not query:
            continue
        
        # Get answer and sources
        result = bot.answer_question(query)
        
        # Print answer
        print("\nAnswer:")
        print(result['answer'])
        
        # Print sources
        print("\nSources used:")
        for source in result['sources']:
            print(f"\n- {source['title']} ({source['year']}), page {source['page']}")
            print(f"  Excerpt: {source['excerpt']}")
            print(f"  URL: {source['url']}")

if __name__ == "__main__":
    main()