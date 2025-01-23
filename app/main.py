from fastapi import FastAPI
import logging
from .routers import countries_router, clubs_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HEMA Analyzer API",
    description="""
    API for managing countries, clubs, and related data within the HEMA Analyzer system.

    ### Features:
    - Retrieve country details by ID.
    - Fetch a paginated list of countries with filters.
    - Retrieve club details, including associated fighters.
    - Fetch a paginated list of clubs with filters.
    """,
    version="1.0.3",
    contact={
        "name": "Giuliano Giannetti",
        "email": "giuliano@seznam.cz",
        "url": "https://hema-praha.cz",
    },
)

# Include routers with updated names
app.include_router(countries_router, prefix="/countries", tags=["countries"])
app.include_router(clubs_router, prefix="/clubs", tags=["clubs"])

@app.get("/")
async def root():
    return {"message": "Welcome to HEMA Ratings API"}