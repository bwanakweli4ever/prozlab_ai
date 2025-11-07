# app/main.py - Add static file serving
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # Add this import
import os
from pathlib import Path

from app.config.settings import settings
from app.routes import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# Set all CORS origins
# Configure CORS - explicitly list dev frontends when credentials are used
default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
cors_origins = getattr(settings, "CORS_ORIGINS", None) or default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(exist_ok=True)

# Create profile images subdirectory
profile_images_dir = uploads_dir / "profile_images"
profile_images_dir.mkdir(exist_ok=True)

# Mount static files for uploaded content
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {"message": "ProzLab Backend API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True)