from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import aadhaar_routes
from app.routes import face_routes
from app.routes import interview_routes
from app.routes import verification_routes
from app.routes import liveness_routes
from app.routes import profile_routes

app = FastAPI(title="AI Verification Full System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routes
app.include_router(aadhaar_routes.router)
app.include_router(face_routes.router)
app.include_router(interview_routes.router)

# Data routes
app.include_router(verification_routes.router)

# Liveness routes
app.include_router(liveness_routes.router)

# Profile routes
app.include_router(profile_routes.router)