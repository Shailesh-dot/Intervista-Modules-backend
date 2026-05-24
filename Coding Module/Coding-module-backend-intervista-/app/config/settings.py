import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

JUDGE0_URL = os.getenv("JUDGE0_URL")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY")