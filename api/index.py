import sys
import os

# Add the project root to path so `app` can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env for local dev (env vars come from Vercel dashboard in production)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from app import create_app

# Vercel's Python runtime looks for an object named `app`
app = create_app()
