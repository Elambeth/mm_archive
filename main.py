import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from search import MauboussinGPT
import traceback
import os
from dotenv import load_dotenv
import time

class ColoredFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        # Use a standard datetime format string
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

# Set up enhanced logging
logger = logging.getLogger("mauboussin_gpt")
logger.setLevel(logging.DEBUG)

# Console handler with color formatting
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(ColoredFormatter())
logger.addHandler(ch)


# This won't work with Vercel as it won't be persistent
# File handler for persistent logs
'''
fh = logging.FileHandler('mauboussin_gpt.log')
fh.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
fh.setFormatter(file_formatter)
logger.addHandler(fh)
'''

# Make sure we don't propagate to root logger
logger.propagate = False

# Load environment variables
load_dotenv()

app = FastAPI()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.mount("/pdfs", StaticFiles(directory="data/pdfs_again"), name="pdfs")

# Initialize RAG system with detailed logging
try:
    logger.info("Initializing MauboussinGPT...")
    start_time = time.time()
    bot = MauboussinGPT()
    init_time = time.time() - start_time
    logger.info(f"Successfully initialized MauboussinGPT in {init_time:.2f} seconds")
except Exception as e:
    logger.critical(f"Failed to initialize MauboussinGPT: {str(e)}")
    logger.critical(traceback.format_exc())
    raise

class Query(BaseModel):
    query: str

class TimedOperation:
    def __init__(self, name):
        self.name = name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"Starting {self.name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is None:
            logger.info(f"Completed {self.name} in {duration:.2f} seconds")
        else:
            logger.error(f"Failed {self.name} after {duration:.2f} seconds")

@app.post("/api/ask")
async def ask_question(query: Query):
    request_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    logger.info(f"Request {request_id}: Received query: {query.query}")
    
    try:
        result = {}
        
        # Track timing for each major operation
        with TimedOperation(f"Request {request_id}: Searching relevant documents") as op:
            search_results = bot.search(query.query)
            result['search_complete'] = True
            
        with TimedOperation(f"Request {request_id}: Creating prompt") as op:
            prompt = bot.create_prompt(query.query, search_results)
            result['prompt_complete'] = True
            
        with TimedOperation(f"Request {request_id}: Generating answer") as op:
            answer = bot.generate_answer(prompt)
            result['answer'] = answer
            
        # Process sources
        with TimedOperation(f"Request {request_id}: Processing sources") as op:
            result['sources'] = [
                {
                    'id': r['paper_id'],
                    'title': r['title'],
                    'year': r['year'],
                    'page': r['page_number'],
                    'tags': r['tags'],
                    'filename': r['filename'],
                    'excerpt': r['content'][:200] + '...' if len(r['content']) > 200 else r['content']
                }
                for r in search_results
            ]
            
        logger.info(f"Request {request_id}: Successfully processed query")
        return JSONResponse(content=result)
        
    except Exception as e:
        error_msg = f"Request {request_id}: Error processing query: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc(),
                "request_id": request_id,
                "progress": result  # Include progress made before error
            }
        )

from mangum import Mangum
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")