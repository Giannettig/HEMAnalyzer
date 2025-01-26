import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.hemanalyzer.database import get_db
from src.hemanalyzer.models.countries import CountryList

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=CountryList, summary="Get Paginated List of Countries")
async def get_countries(
    name: Optional[str] = Query(None, description="Filter by country name"),
    region: Optional[str] = Query(None, description="Filter by region"),
    sub_region: Optional[str] = Query(None, description="Filter by sub-region"),
    population_min: Optional[int] = Query(None, description="Minimum active fencers"),
    population_max: Optional[int] = Query(None, description="Maximum active fencers"),
    community: Optional[int] = Query(None, description="Filter by community ID"),
    community_label: Optional[str] = Query(None, description="Filter by community label"),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db=Depends(get_db),
):
    try:
        query = """
            SELECT 
                country_id, 
                country_name, 
                country_code,
                region, 
                sub_region, 
                population AS active_fencers, 
                community, 
                community_label 
            FROM countries 
            WHERE 1=1
        """
        params = {"limit": limit, "skip": skip}

        if name:
            query += " AND country_name ILIKE :name"
            params["name"] = f"%{name}%"
        if region:
            query += " AND region ILIKE :region"
            params["region"] = f"%{region}%"
        if sub_region:
            query += " AND sub_region ILIKE :sub_region"
            params["sub_region"] = f"%{sub_region}%"
        if population_min:
            query += " AND population >= :population_min"
            params["population_min"] = population_min
        if population_max:
            query += " AND population <= :population_max"
            params["population_max"] = population_max
        if community:
            query += " AND community = :community"
            params["community"] = community
        if community_label:
            query += " AND community_label ILIKE :community_label"
            params["community_label"] = f"%{community_label}%"

        query += " ORDER BY country_name LIMIT :limit OFFSET :skip"
        results = db.execute(text(query), params).fetchall()
        total = db.execute(text("SELECT COUNT(*) FROM countries WHERE 1=1")).scalar()

        return CountryList(
            items=[dict(row._mapping) for row in results],
            total=total,
            page=skip // limit + 1,
            size=limit,
        )
    except SQLAlchemyError as e:
        logger.error(f"Error fetching countries: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
