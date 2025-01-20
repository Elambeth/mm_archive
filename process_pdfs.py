import fitz  # PyMuPDF
from pathlib import Path
import json

class PDFProcessor:
    def __init__(self, pdfs_dir="pdfs"):
        self.pdfs_dir = Path(pdfs_dir)
        self.output_dir = Path("processed")
        self.output_dir.mkdir(exist_ok=True)

    def process_pdf(self, pdf_path):
        doc = fitz.open(pdf_path)
        
        # Extract text with structure
        content = {
            'text': '',
            'metadata': doc.metadata,
            'pages': [],
            'images': []
        }

        # Process each page
        for page_num, page in enumerate(doc):
            # Get text
            text = page.get_text()
            
            # Get images
            image_list = page.get_images()
            page_images = []
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                if base_image:
                    image_data = {
                        'page': page_num + 1,
                        'index': img_index,
                        'extension': base_image["ext"],
                        'image': base_image["image"]
                    }
                    page_images.append(image_data)

            content['pages'].append({
                'number': page_num + 1,
                'text': text
            })
            content['images'].extend(page_images)

        return content

    def process_all_pdfs(self):
        results = []
        for pdf_path in self.pdfs_dir.glob('*.pdf'):
            try:
                print(f"Processing {pdf_path.name}")
                content = self.process_pdf(pdf_path)
                
                # Save processed content
                output_file = self.output_dir / f"{pdf_path.stem}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    # Save text and metadata (not images) to JSON
                    json_content = {
                        'filename': pdf_path.name,
                        'metadata': content['metadata'],
                        'pages': content['pages']
                    }
                    json.dump(json_content, f, indent=2)
                
                # Save images separately
                images_dir = self.output_dir / pdf_path.stem / 'images'
                images_dir.mkdir(parents=True, exist_ok=True)
                for img in content['images']:
                    img_path = images_dir / f"page_{img['page']}_img_{img['index']}.{img['extension']}"
                    with open(img_path, 'wb') as f:
                        f.write(img['image'])
                
                results.append({
                    'filename': pdf_path.name,
                    'pages': len(content['pages']),
                    'images': len(content['images'])
                })
                
            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}")

        return results

if __name__ == "__main__":
    processor = PDFProcessor()
    results = processor.process_all_pdfs()
    
    print("\nProcessing Summary:")
    for result in results:
        print(f"{result['filename']}: {result['pages']} pages, {result['images']} images")