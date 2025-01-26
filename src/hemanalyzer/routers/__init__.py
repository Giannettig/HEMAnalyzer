from .clubs import router as clubs_router
from .countries import router as countries_router
from .fighters import router as fighters_router

__all__ = ["countries_router", "clubs_router", "fighters_router"]
