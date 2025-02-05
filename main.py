from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from search import MauboussinGPT
import traceback
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your RAG system
try:
    bot = MauboussinGPT()  # No longer need to pass API key
    logger.info("Successfully initialized MauboussinGPT")
except Exception as e:
    logger.error(f"Failed to initialize MauboussinGPT: {str(e)}")
    logger.error(traceback.format_exc())
    raise

class Query(BaseModel):
    query: str

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {"status": "ok", "message": "API is running"}

@app.post("/api/ask")
async def ask_question(query: Query):
    try:
        logger.info(f"Received query: {query.query}")
        
        # Log the steps
        logger.info("Step 1: Starting answer generation")
        
        # Get answer from RAG system
        result = bot.answer_question(query.query)
        
        logger.info("Step 2: Got result from bot")
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result content: {result}")
        
        if not isinstance(result, dict):
            raise ValueError(f"Expected dict result, got {type(result)}")
            
        if 'answer' not in result:
            raise ValueError(f"Result missing 'answer' key. Keys present: {result.keys()}")
            
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")