import os

# PostgreSQL database URL — shared with C# knitnet-verification-api
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres.ukdiydoqhirukeqwlpld:RUDHRITHSANDY040505@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
)

# Storage paths
AADHAAR_STORAGE = "app/storage/aadhaar"
PASSPORT_STORAGE = "app/storage/passport"
EMBED_STORAGE = "app/storage/embeddings"

# Face similarity threshold
FACE_THRESHOLD = 0.5

# Cloudinary Settings
CLOUDINARY_CLOUD_NAME = "dkfidppml"
CLOUDINARY_API_KEY = "332916443119163"
CLOUDINARY_API_SECRET = "aOKjYIdkfaWOdA3WGeAJyhuo0d8"
