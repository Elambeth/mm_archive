import sqlite3
import json
from pathlib import Path
import logging
import re
import unicodedata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def normalize_filename(filename):
    """Normalize a filename to match database format"""
    # Remove .json extension if present
    filename = filename.replace('.json', '')
    
    # Convert accented characters to ASCII
    filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
    
    # Replace common word variations
    filename = filename.replace('versus', 'vs')
    filename = filename.replace(' and ', ' ')
    filename = filename.replace('&', 'and')
    
    # Remove special characters
    filename = re.sub(r'["\'\(\)\?\:]', '', filename)
    
    # Replace multiple underscores and spaces with single underscore
    filename = re.sub(r'[_\s]+', '_', filename)
    
    # Remove underscores before and after dashes
    filename = re.sub(r'_*-_*', '-', filename)
    
    # Remove any remaining special characters
    filename = re.sub(r'[^a-zA-Z0-9_\-]', '', filename)
    
    # Add .json back
    return filename + '.json'

def debug_filename_match(cur, original_filename, normalized_filename):
    """Debug helper to find close matches"""
    cur.execute("SELECT filename FROM papers WHERE filename LIKE ?", 
               (f"%{normalized_filename[:10]}%",))
    similar = cur.fetchall()
    if similar:
        logging.info(f"Similar filenames in DB for {original_filename}:")
        for s in similar:
            logging.info(f"  DB has: {s[0]}")

def process_json_files():
    """Process all JSON files and link their tags to papers"""
    db_path = 'mauboussin_archive.db'
    json_dir = 'processed_papers'
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get all standard tags from database for matching
    cur.execute("SELECT id, name FROM tags")
    standard_tags = {row[1]: row[0] for row in cur.fetchall()}
    logging.info(f"Loaded {len(standard_tags)} standard tags")
    
    # Get all paper filenames for debugging
    cur.execute("SELECT filename FROM papers")
    db_filenames = {row[0] for row in cur.fetchall()}
    logging.info(f"Found {len(db_filenames)} papers in database")
    
    # Process each JSON file
    json_dir = Path(json_dir)
    processed = 0
    skipped = 0
    skipped_files = []
    
    for json_path in json_dir.glob('*.json'):
        try:
            # Read the JSON file
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Get the filename and normalize it
            original_filename = json_path.name
            normalized_filename = normalize_filename(original_filename)
            
            # Find corresponding paper
            cur.execute("SELECT id FROM papers WHERE filename = ?", (normalized_filename,))
            paper_result = cur.fetchone()
            
            if not paper_result:
                # Try alternate normalization if first attempt fails
                alt_normalized = normalize_filename(original_filename.replace('_', ' '))
                cur.execute("SELECT id FROM papers WHERE filename = ?", (alt_normalized,))
                paper_result = cur.fetchone()
            
            if not paper_result:
                logging.warning(f"No matching paper found for {original_filename}")
                debug_filename_match(cur, original_filename, normalized_filename)
                skipped += 1
                skipped_files.append(original_filename)
                continue
            
            paper_id = paper_result[0]
            
            # Process tags from metadata
            json_tags = data.get('metadata', {}).get('tags', [])
            
            # Match and insert tags
            tags_added = []
            for tag in json_tags:
                # Look for exact match first
                tag_id = standard_tags.get(tag)
                
                # Try case-insensitive match if no exact match
                if not tag_id:
                    tag_lower = tag.lower()
                    for std_tag, std_id in standard_tags.items():
                        if std_tag.lower() == tag_lower:
                            tag_id = std_id
                            break
                
                if tag_id:
                    try:
                        cur.execute("""
                            INSERT OR IGNORE INTO paper_tags (paper_id, tag_id)
                            VALUES (?, ?)
                        """, (paper_id, tag_id))
                        tags_added.append(tag)
                    except sqlite3.IntegrityError as e:
                        logging.error(f"Error linking tag {tag} to paper {original_filename}: {e}")
                else:
                    logging.warning(f"Unmatched tag '{tag}' in {original_filename}")
            
            if tags_added:
                logging.info(f"Added tags {', '.join(tags_added)} to {original_filename}")
            
            conn.commit()
            processed += 1
            
            if processed % 10 == 0:
                logging.info(f"Processed {processed} files")
                
        except Exception as e:
            logging.error(f"Error processing {json_path}: {e}")
            conn.rollback()
            skipped += 1
            skipped_files.append(json_path.name)
    
    # Final stats
    logging.info(f"""
    Import completed:
    - Files processed: {processed}
    - Files skipped: {skipped}
    """)
    
    if skipped_files:
        logging.info("Skipped files:")
        for f in skipped_files:
            logging.info(f"  {f}")
    
    conn.close()

if __name__ == "__main__":
    process_json_files()