import psycopg2
from rich.console import Console
from rich.table import Table

DB_PARAMS = {
    'dbname': 'mauboussin',
    'user': 'postgres',
    'password': 'alwayslearning',
    'host': 'localhost'
}

def count_vector_dimensions(vector_str):
    """Count dimensions in a vector string by counting commas and adding 1"""
    # Remove brackets and split by commas
    clean_str = vector_str.strip('[]')
    return len(clean_str.split(','))

def check_embedding_dimensions():
    console = Console()
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Get a sample of embeddings
        cur.execute("""
            SELECT id, embedding
            FROM pages 
            WHERE embedding IS NOT NULL
            LIMIT 10;
        """)
        
        results = cur.fetchall()
        dims = {}
        
        # Analyze dimensions
        for page_id, embedding in results:
            if embedding:
                dim = count_vector_dimensions(embedding)
                dims[dim] = dims.get(dim, 0) + 1
                
        # Create display table
        table = Table(title="Embedding Sample Analysis")
        table.add_column("Page ID", justify="right", style="cyan")
        table.add_column("Dimensions", justify="right", style="green")
        
        for page_id, embedding in results:
            dim = count_vector_dimensions(embedding) if embedding else 0
            table.add_row(
                str(page_id),
                str(dim)
            )
        
        # Print results
        console.print("\n[bold]Sample Embedding Analysis:[/bold]")
        console.print(table)
        
        # Print summary
        console.print("\n[bold]Dimension Distribution:[/bold]")
        for dim, count in dims.items():
            console.print(f"Dimension {dim}: {count} occurrences")
            
        # Let's also print the first few values of one embedding to verify format
        if results:
            sample_embedding = results[0][1]
            console.print("\n[bold]Sample Embedding Format:[/bold]")
            console.print(f"First 100 characters: {sample_embedding[:100]}")
            
    except Exception as e:
        console.print(f"[red]Error checking embeddings: {str(e)}[/red]")
    
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_embedding_dimensions()