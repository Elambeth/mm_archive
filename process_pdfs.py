import fitz
from pathlib import Path
import json
import re
from collections import defaultdict

def serialize_mupdf_types(obj):
    """Convert PyMuPDF types to serializable dictionaries"""
    if hasattr(obj, 'x') and hasattr(obj, 'y'):  # Point
        return {"x": obj.x, "y": obj.y}
    elif hasattr(obj, 'x0') and hasattr(obj, 'y0'):  # Rect
        return {
            "x0": obj.x0,
            "y0": obj.y0,
            "x1": obj.x1,
            "y1": obj.y1
        }
    return obj

def get_drawing_bounds(drawing):
    """Get the bounding box of a drawing"""
    rect = drawing['rect']
    return (rect['x0'], rect['y0'], rect['x1'], rect['y1'])

def cluster_drawings(drawings, distance_threshold=20):
    """Group drawings that are close together into potential diagrams"""
    if not drawings:
        return []

    clusters = []
    current_cluster = [drawings[0]]
    current_bounds = get_drawing_bounds(drawings[0])

    for drawing in drawings[1:]:
        bounds = get_drawing_bounds(drawing)
        
        # Check if this drawing is close to current cluster
        if (abs(bounds[0] - current_bounds[0]) < distance_threshold and
            abs(bounds[1] - current_bounds[1]) < distance_threshold):
            # Add to current cluster
            current_cluster.append(drawing)
            # Expand bounds
            current_bounds = (
                min(current_bounds[0], bounds[0]),
                min(current_bounds[1], bounds[1]),
                max(current_bounds[2], bounds[2]),
                max(current_bounds[3], bounds[3])
            )
        else:
            # Start new cluster if current is large enough
            if len(current_cluster) > 5:  # Minimum drawings for a diagram
                clusters.append((current_cluster, current_bounds))
            current_cluster = [drawing]
            current_bounds = bounds

    # Add last cluster if large enough
    if len(current_cluster) > 5:
        clusters.append((current_cluster, current_bounds))

    return clusters

def is_meaningful_diagram(cluster, bounds):
    """Determine if a cluster represents a meaningful diagram"""
    # Calculate size of bounding box
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    area = width * height

    # Count different types of drawing commands
    command_types = defaultdict(int)
    for drawing in cluster:
        for item in drawing['items']:
            command_types[item[0]] += 1

    # Criteria for a meaningful diagram:
    # 1. Minimum size
    if area < 10:  # Adjust threshold as needed
        return False

    # 2. Multiple types of drawing commands
    if len(command_types) < 2:
        return False

    # 3. Minimum number of elements
    if len(cluster) < 3:  # Adjust threshold as needed
        return False

    return True

class PDFProcessor:
    def __init__(self, pdfs_dir="pdf_download", mappings_file="paper_mappings.json"):
        self.pdfs_dir = Path(pdfs_dir)
        self.output_dir = Path("processed_papers_2")
        self.output_dir.mkdir(exist_ok=True)
        
        # Load mappings
        with open(mappings_file, 'r') as f:
            self.mappings = json.load(f)
        print(f"Loaded mappings for {len(self.mappings['files'])} papers")
        
        # Extract ID mapping
        self.id_mapping = {}
        for filename, metadata in self.mappings['files'].items():
            if match := re.match(r'(mm_\d{3})_', filename):
                paper_id = match.group(1)
                self.id_mapping[filename] = paper_id

    def process_pdf(self, pdf_path):
        doc = fitz.open(pdf_path)
        print(f"Processing {pdf_path.name} - {doc.page_count} pages")
        
        content = {
            'filename': pdf_path.name,
            'metadata': {
                **doc.metadata,
                **self.mappings['files'].get(pdf_path.name, {}),
                'tags': []
            },
            'pages': [],
            'diagrams': []  # Changed from 'drawings' to 'diagrams'
        }

        # Process each page
        for page_num, page in enumerate(doc):
            print(f"\nProcessing page {page_num + 1}")
            
            # Get text and drawings
            text = page.get_text()
            drawings = page.get_drawings()
            
            if drawings:
                # Convert drawings to serializable format
                processed_drawings = []
                for draw_index, drawing in enumerate(drawings):
                    drawing_data = {
                        'page': page_num + 1,
                        'index': draw_index,
                        'rect': serialize_mupdf_types(drawing['rect']),
                        'items': [[item[0]] + [serialize_mupdf_types(p) for p in item[1:]] 
                                for item in drawing['items']],
                        'color': drawing.get('color'),
                        'fill': drawing.get('fill'),
                        'width': drawing.get('width', 1.0),
                        'stroke_opacity': drawing.get('stroke_opacity', 1),
                        'fill_opacity': drawing.get('fill_opacity', 1),
                        'closePath': drawing.get('closePath', False)
                    }
                    processed_drawings.append(drawing_data)

                # Find clusters of drawings that might be diagrams
                clusters = cluster_drawings(processed_drawings)
                
                # Filter for meaningful diagrams
                meaningful_diagrams = []
                for cluster, bounds in clusters:
                    if is_meaningful_diagram(cluster, bounds):
                        diagram_data = {
                            'page': page_num + 1,
                            'bounds': {
                                'x0': bounds[0],
                                'y0': bounds[1],
                                'x1': bounds[2],
                                'y1': bounds[3]
                            },
                            'drawings': cluster
                        }
                        meaningful_diagrams.append(diagram_data)
                
                if meaningful_diagrams:
                    print(f"Found {len(meaningful_diagrams)} meaningful diagrams on page {page_num + 1}")
                    content['diagrams'].extend(meaningful_diagrams)

            content['pages'].append({
                'number': page_num + 1,
                'text': text
            })

        return content

    def process_all_pdfs(self):
        results = []
        
        for pdf_path in self.pdfs_dir.glob('*.pdf'):
            try:
                print(f"\nProcessing {pdf_path.name}")
                content = self.process_pdf(pdf_path)
                
                paper_id = self.get_standardized_name(pdf_path.name)
                if not paper_id:
                    print(f"Warning: Could not find ID for {pdf_path.name}")
                    continue
                
                output_file = self.output_dir / f"{paper_id}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)
                
                result = {
                    'paper_id': paper_id,
                    'filename': pdf_path.name,
                    'pages': len(content['pages']),
                    'diagrams': len(content['diagrams'])
                }
                results.append(result)
                print(f"Saved {paper_id}.json with {result['diagrams']} diagrams")
                
            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}")
                import traceback
                traceback.print_exc()

        # Save summary
        with open(self.output_dir / 'processing_summary.json', 'w') as f:
            json.dump(results, f, indent=2)

        return results

    def get_standardized_name(self, pdf_filename):
        return self.id_mapping.get(pdf_filename)

if __name__ == "__main__":
    processor = PDFProcessor()
    results = processor.process_all_pdfs()
    
    print("\nProcessing Summary:")
    total_diagrams = 0
    papers_with_diagrams = 0
    for result in results:
        if result['diagrams'] > 0:
            papers_with_diagrams += 1
        total_diagrams += result['diagrams']
        print(f"{result['paper_id']}: {result['pages']} pages, {result['diagrams']} diagrams")
    
    print(f"\nTotal diagrams found: {total_diagrams}")
    print(f"Papers with diagrams: {papers_with_diagrams}/{len(results)}")