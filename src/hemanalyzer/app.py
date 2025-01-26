import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.hemanalyzer.routers import clubs_router, countries_router, fighters_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HEMA Analyzer API",
    description="API for managing HEMA tournament data including countries, clubs, and fighters.",
    version="1.0.3",
    contact={
        "name": "Giuliano Giannetti",
        "email": "giuliano@seznam.cz",
        "url": "https://hema-praha.cz",
    },
)

# Set up static files and templates
app.mount("/static", StaticFiles(directory="src/hemanalyzer/static"), name="static")
templates = Jinja2Templates(directory="src/hemanalyzer/templates")

# Include routers with API prefix
app.include_router(countries_router, prefix="/api/countries", tags=["countries"])
app.include_router(clubs_router, prefix="/api/clubs", tags=["clubs"])
app.include_router(fighters_router, prefix="/api/fighters", tags=["fighters"])


@app.get("/")
async def fighter_profile(request: Request):
    """Render the fighter profile page"""
    return templates.TemplateResponse("fighter_profile.html", {"request": request})
