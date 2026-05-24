from dotenv import load_dotenv
import os

load_dotenv()

JUDGE0_URL     = os.getenv("JUDGE0_URL", "http://localhost:2358")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY", "")
APP_ENV        = os.getenv("APP_ENV", "development")

# Auth
JWT_SECRET     = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM  = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
DATABASE_URL   = os.getenv("DATABASE_URL")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin123")
