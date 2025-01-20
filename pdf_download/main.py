import asyncio
import aiohttp
from pathlib import Path
import csv

class MauboussinDownloader:
    def __init__(self):
        self.output_dir = Path("pdfs")
        self.output_dir.mkdir(exist_ok=True)

    def create_filename(self, row):
        # Year is in the third column (index 2)
        year = row[2]
        # Title is in the sixth column (index 5)
        title = row[5]
        # Clean title for filename
        clean_title = ''.join(c if c.isalnum() or c.isspace() else '_' for c in title)
        clean_title = clean_title.replace(' ', '_').lower()
        return f"{year}_{clean_title}.pdf"

    async def download_pdf(self, session, url, filename):
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
                    return True
                else:
                    print(f"Failed to download {url}: Status {response.status}")
                    return False
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    async def download_all(self, csv_path):
        data = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 7:  # We need at least 7 columns
                    url = row[6]  # URL is in the seventh column
                    data.append((row, url))

        async with aiohttp.ClientSession() as session:
            tasks = []
            for row, url in data:
                filename = self.create_filename(row)
                if filename:
                    task = self.download_pdf(session, url, filename)
                    tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            print(f"\nDownloaded {sum(1 for r in results if r is True)} PDFs")

if __name__ == "__main__":
    downloader = MauboussinDownloader()
    asyncio.run(downloader.download_all('mauboussin_papers.csv'))