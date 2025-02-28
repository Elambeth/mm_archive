# Create a new file called api/index.py
from main import app

# This is needed for Vercel serverless functions
def handler(request, response):
    return app(request, response)