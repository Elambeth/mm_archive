import json
import os
from pathlib import Path
from typing import List, Dict
import asyncio
from datetime import datetime
from openai import OpenAI

class PaperTagger:
    # Define valid tags as a class constant
    VALID_TAGS = {
        "Alpha generation",
        "Base rates",
        "Behavioral finance",
        "Business lifecycle & longevity",
        "Business models & growth",
        "Capital allocation",
        "Competitive advantage",
        "Decision making",
        "Expectations analysis",
        "Financial metrics",
        "Investment process",
        "Market structure",
        "Mergers & acquisitions",
        "Quantitative methods",
        "Risk management",
        "ROIC analysis",
        "Skill vs luck",
        "Technology & innovation",
        "Valuation methods"
    }

    def __init__(self, json_dir: str, deepseek_api_key: str):
        self.json_dir = Path(json_dir)
        self.api_key = deepseek_api_key
        self.tag_prompt = """
        Analyze the paper's content and assign 2-4 tags from the following list. Return only the tags in a JSON list.
        Available tags:
        - Alpha generation: Strategies for generating excess returns
        - Base rates: Using historical probabilities and statistical evidence
        - Behavioral finance: Psychology of markets and investing
        - Business lifecycle & longevity: Company evolution and survival
        - Business models & growth: How companies create and capture value
        - Capital allocation: How companies deploy capital
        - Competitive advantage: Sources and sustainability of advantages
        - Decision making: Analysis of choices and judgment
        - Expectations analysis: Study of market expectations
        - Financial metrics: Key financial measures and indicators
        - Investment process: Systematic approaches to investing
        - Market structure: How markets are organized and function
        - Mergers & acquisitions: Corporate transactions and deals
        - Quantitative methods: Mathematical and statistical approaches
        - Risk management: Understanding and managing uncertainty
        - ROIC analysis: Return on invested capital focus
        - Skill vs luck: Distinguishing skill from randomness
        - Technology & innovation: Tech impact and innovation
        - Valuation methods: Approaches to valuing assets
        """

    def validate_tags(self, tags: List[str]) -> List[str]:
        """Ensure only valid tags are included."""
        return [tag for tag in tags if tag in self.VALID_TAGS]

    def extract_content(self, json_path: Path) -> Dict:
        """Extract relevant content from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Get first two pages of text (usually contains abstract and intro)
        text = "\n".join(page['text'] for page in data['pages'][:2] if page.get('text'))
        
        return {
            'filename': data['filename'],
            'title': Path(data['filename']).stem,
            'text': text
        }

    def get_tags(self, content: Dict) -> List[str]:
        """Get tags from Deepseek API using OpenAI SDK."""
        prompt = f"""
        Title: {content['title']}
        Content: {content['text']}
        
        IMPORTANT: Return ONLY a JSON array of tag names without descriptions. 
        For example: ["ROIC analysis", "Capital allocation"]
        
        {self.tag_prompt}
        """
        
        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a research paper tagger. Return only a JSON array of tag names without descriptions."},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            print("Raw API response:", response.choices[0].message.content)
            
            try:
                text = response.choices[0].message.content
                # Remove markdown formatting if present
                if '```json' in text:
                    text = text[text.find('['):text.rfind(']')+1]
                
                tags = json.loads(text)
                # Clean tags by taking everything before the colon
                clean_tags = [tag.split(':')[0].strip() for tag in tags]
                return self.validate_tags(clean_tags)
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return []
                
        except Exception as e:
            print(f"API error: {str(e)}")
            return []

    async def process_files(self):
        """Process all JSON files and update their metadata with tags."""
        print(f"Looking for JSON files in: {self.json_dir}")
        json_files = list(self.json_dir.glob('*.json'))
        print(f"Found {len(json_files)} JSON files")
        
        if not json_files:
            print("No JSON files found in directory!")
            return
            
        for json_file in json_files:
            print(f"\nProcessing: {json_file}")
            try:
                # Read file
                print("Reading file...")
                with open(json_file, 'r') as f:
                    paper_data = json.load(f)
                
                # Get and validate tags
                print("Extracting content...")
                content = self.extract_content(json_file)
                print("Getting tags from Deepseek...")
                tags = self.get_tags(content)
                
                print(f"Received tags: {tags}")
                
                # Update metadata
                paper_data['metadata']['tags'] = tags
                paper_data['metadata']['tagged_at'] = datetime.now().isoformat()
                
                # Write back to file
                print("Writing updated file...")
                with open(json_file, 'w') as f:
                    json.dump(paper_data, f, indent=2)
                
                print(f"Successfully tagged {content['filename']}")
                
            except Exception as e:
                print(f"Error processing {json_file}: {str(e)}")


def main():
    # Your Deepseek API key
    api_key = "sk-231c14752f1d4b3c8517869bc332cf0e"  # Replace with your actual API key
    
    # Path to your test directory with JSON files
    json_dir = r"C:\Users\elamb\OneDrive\Desktop\mm_archive\new_processed"  # Use raw string with full path
    
    tagger = PaperTagger(
        json_dir=json_dir,
        deepseek_api_key=api_key
    )
    
    asyncio.run(tagger.process_files())

if __name__ == '__main__':
    main()