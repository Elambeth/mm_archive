import asyncio
import aiohttp
from pathlib import Path
import csv
import json

class MauboussinDownloader:
    def __init__(self):
        self.output_dir = Path("pdfs_again")
        self.output_dir.mkdir(exist_ok=True)
        # Create mapping file to store ID relationships
        self.mappings_file = Path("paper_mappings.json")
        self.mappings = {'files': {}}

    def create_filename(self, row_id, row):
        """Create filename with ID prefix"""
        # Year is in the third column (index 2)
        year = row[2]
        # Title is in the sixth column (index 5)
        title = row[5]
        # Clean title for filename
        clean_title = ''.join(c if c.isalnum() or c.isspace() else '_' for c in title)
        clean_title = clean_title.replace(' ', '_').lower()
        return f"mm_{row_id:03d}_{year}_{clean_title}.pdf"

    async def download_pdf(self, session, row_id, row, url, filename):
        pdf_path = self.output_dir / filename
        if pdf_path.exists():
            print(f"Already exists: {filename}")
            return True
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    pdf_path.write_bytes(content)
                    print(f"Downloaded: {filename}")
                    # Store mapping
                    self.mappings['files'][filename] = {
                        'id': row_id,
                        'year': row[2],
                        'date': row[3],
                        'institution': row[4],
                        'title': row[5],
                        'url': url
                    }
                    return True
                else:
                    print(f"Failed to download {url}: Status {response.status}")
                    return False
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    def save_mappings(self):
        """Save ID mappings to JSON file"""
        with open(self.mappings_file, 'w') as f:
            json.dump(self.mappings, f, indent=2)

    async def download_all(self, csv_path):
        # Read CSV data
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)

        async with aiohttp.ClientSession() as session:
            tasks = []
            for row_id, row in enumerate(rows, 1):  # Start IDs at 1
                if len(row) >= 7:  # Ensure row has enough columns
                    url = row[6]  # URL is in the seventh column
                    filename = self.create_filename(row_id, row)
                    task = self.download_pdf(session, row_id, row, url, filename)
                    tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Save the mappings
            self.save_mappings()
            
            successful = sum(1 for r in results if r is True)
            print(f"\nDownloaded {successful} new PDFs")
            print(f"Created mappings for {len(self.mappings['files'])} files")

if __name__ == "__main__":
    downloader = MauboussinDownloader()
    asyncio.run(downloader.download_all('mauboussin_papers.csv'))