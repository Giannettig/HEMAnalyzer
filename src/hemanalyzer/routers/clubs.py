import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.hemanalyzer.database import get_db
from src.hemanalyzer.models.club import ClubList

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ClubList, summary="Get Paginated List of Clubs")
async def get_clubs(
    name: Optional[str] = Query(None, description="Filter by club name"),
    country: Optional[str] = Query(None, description="Filter by club country"),
    city: Optional[str] = Query(None, description="Filter by club city"),
    members_min: Optional[int] = Query(None, description="Minimum number of members"),
    members_max: Optional[int] = Query(None, description="Maximum number of members"),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db=Depends(get_db),
):
    try:
        club_query = """
            SELECT 
                c.club_id, 
                c.club_name, 
                c.club_code,
                c.club_country, 
                c.club_state, 
                c.club_city, 
                c.club_members, 
                pc.club_name AS parent_club, 
                c.club_url 
            FROM clubs c
            LEFT JOIN clubs pc ON c.club_parent_id = pc.club_id
            WHERE 1=1
        """
        params = {"limit": limit, "skip": skip}

        if name:
            club_query += " AND c.club_name ILIKE :name"
            params["name"] = f"%{name}%"
        if country:
            club_query += " AND c.club_country ILIKE :country"
            params["country"] = f"%{country}%"
        if city:
            club_query += " AND c.club_city ILIKE :city"
            params["city"] = f"%{city}%"
        if members_min:
            club_query += " AND c.club_members >= :members_min"
            params["members_min"] = members_min
        if members_max:
            club_query += " AND c.club_members <= :members_max"
            params["members_max"] = members_max

        total_query = f"SELECT COUNT(*) FROM ({club_query}) as subquery"
        total = db.execute(text(total_query), params).scalar()

        club_query += " ORDER BY c.club_name LIMIT :limit OFFSET :skip"
        clubs_result = db.execute(text(club_query), params).fetchall()

        club_ids = [row[0] for row in clubs_result]
        if club_ids:
            fighter_query = text("""
                SELECT fighter_club_id, ARRAY_AGG(fighter_id) as fighter_ids
                FROM fighters
                WHERE fighter_club_id = ANY(:club_ids)
                GROUP BY fighter_club_id
            """)
            fighter_result = db.execute(fighter_query, {"club_ids": club_ids}).fetchall()
            fighter_map = {row[0]: row[1] for row in fighter_result}
        else:
            fighter_map = {}

        clubs = []
        for row in clubs_result:
            club_data = {
                "club_id": row[0],
                "club_name": row[1],
                "club_code": row[2],
                "club_country": row[3],
                "club_state": row[4],
                "club_city": row[5],
                "club_members": row[6],
                "parent_club": row[7],
                "club_url": row[8],
                "fighter_ids": fighter_map.get(row[0], []),
            }
            clubs.append(club_data)

        return ClubList(items=clubs, total=total, page=(skip // limit) + 1, size=limit)
    except SQLAlchemyError as e:
        logger.error(f"Error fetching clubs: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
