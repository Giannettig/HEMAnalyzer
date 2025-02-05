import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.hemanalyzer.database import get_db
from src.hemanalyzer.models.fighters import FighterResponse

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_model=FighterResponse, summary="Search Fighters")
async def search_fighters(
    name: Optional[str] = Query(None, description="Filter by fighter name"),
    club: Optional[str] = Query(None, description="Filter by club name"),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db=Depends(get_db),
):
    # Get fighter details query
    fighter_query = """
        SELECT 
            f.fighter_id,
            f.fighter_name,
            f.fighter_club_name,
            f.fighter_nationality,
            c.country_code,
            f.rank_longsword,
            0 as total_events,
            0 as total_matches,
            0 as win_rate
        FROM fighters f
        LEFT JOIN countries c ON LOWER(f.fighter_nationality) = LOWER(c.country_name)
        WHERE 1=1
    """

    params = {"limit": limit, "skip": skip}

    if name:
        fighter_query += " AND LOWER(f.fighter_name) LIKE LOWER(:name)"
        params["name"] = f"%{name}%"
    if club:
        fighter_query += " AND f.fighter_club_name ILIKE :club"
        params["club"] = f"%{club}%"

    fighter_query += """
        ORDER BY 
            CASE 
                WHEN LOWER(f.fighter_name) = LOWER(:exact_name) THEN 0
                ELSE 1
            END,
            f.fighter_name
        LIMIT :limit OFFSET :skip
    """
    if name:
        params["exact_name"] = name
    else:
        params["exact_name"] = ""

    try:
        # Get fighters
        fighters = []
        results = db.execute(text(fighter_query), params).fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) 
            FROM fighters f
            WHERE 1=1
            {" AND f.fighter_name ILIKE :name" if name else ""}
            {" AND f.fighter_club_name ILIKE :club" if club else ""}
        """
        total = db.execute(text(count_query), params).scalar() or 0

        # Comment out queries dictionary as it's not needed in response
        # queries = {"fighter_query": fighter_query}

        for row in results:
            fighter_data = dict(row._mapping)
            fighter_id = fighter_data["fighter_id"]

            # Get stats with corrected win rate calculation
            stats_query = """
                WITH fighter_matches AS (
                    SELECT 
                        COUNT(*) as total_matches,
                        COUNT(CASE WHEN result = 'WIN' THEN 1 END) as wins,
                        COUNT(DISTINCT e.event_id) as total_events
                    FROM match_results m
                    JOIN tournaments t ON m.tournament_id = t.tournament_id
                    JOIN events e ON t.event_id = e.event_id
                    WHERE m.fighter_id = :fighter_id
                )
                SELECT 
                    CASE 
                        WHEN total_matches > 0 
                        THEN ROUND((wins::float / total_matches) * 100) || '%'
                        ELSE 'error'
                    END as win_rate,
                    wins,
                    total_matches,
                    total_events
                FROM fighter_matches
            """
            # queries["stats_query"] = stats_query
            stats_result = db.execute(text(stats_query), {"fighter_id": fighter_id}).fetchone()

            # Get weapons usage
            weapons_query = """
                SELECT 
                    t.tournament_weapon as weapon,
                    COUNT(*) as matches
                FROM match_results m
                JOIN tournaments t ON m.tournament_id = t.tournament_id
                WHERE m.fighter_id = :fighter_id
                GROUP BY t.tournament_weapon
                ORDER BY matches DESC
            """
            # queries["weapons_query"] = weapons_query
            weapons_result = db.execute(text(weapons_query), {"fighter_id": fighter_id}).fetchall()

            # Get tournament attendance with event brand
            tournaments_query = """
                WITH tournament_years AS (
                    SELECT DISTINCT
                        e.event_brand as tournament_name,
                        e.event_year as year,
                        c.country_code,
                        e.event_country,
                        MAX(e.event_date) as latest_event_date,
                        ROUND(AVG(t.fighter_count)::numeric, 0) as avg_fighters
                    FROM match_results m
                    JOIN tournaments t ON m.tournament_id = t.tournament_id
                    JOIN events e ON t.event_id = e.event_id
                    LEFT JOIN countries c ON LOWER(e.event_country) = LOWER(c.country_name)
                    WHERE m.fighter_id = :fighter_id
                    GROUP BY e.event_brand, e.event_year, c.country_code, e.event_country
                ),
                medals AS (
                    SELECT DISTINCT
                        e.event_brand as tournament_name,
                        t.tournament_name as sub_tournament,
                        e.event_year as year,
                        CASE 
                            WHEN m.is_final AND m.result = 'WIN' THEN 'gold'
                            WHEN m.is_final AND m.result = 'LOSS' THEN 'silver'
                            ELSE NULL 
                        END as medal_type
                    FROM match_results m
                    JOIN tournaments t ON m.tournament_id = t.tournament_id
                    JOIN events e ON t.event_id = e.event_id
                    WHERE m.fighter_id = :fighter_id
                    AND m.is_final = true
                    AND m.result IN ('WIN', 'LOSS')
                    GROUP BY 
                        e.event_brand,
                        t.tournament_name,
                        e.event_year,
                        CASE 
                            WHEN m.is_final AND m.result = 'WIN' THEN 'gold'
                            WHEN m.is_final AND m.result = 'LOSS' THEN 'silver'
                            ELSE NULL 
                        END
                ),
                tournament_stats AS (
                    SELECT 
                        e.event_brand as tournament_name,
                        COUNT(*) as total_matches,
                        COUNT(DISTINCT e.event_id) as total_events,
                        COUNT(CASE WHEN m.result = 'WIN' THEN 1 END)::float / NULLIF(COUNT(*), 0)::float * 100 as win_rate
                    FROM match_results m
                    JOIN tournaments t ON m.tournament_id = t.tournament_id
                    JOIN events e ON t.event_id = e.event_id
                    WHERE m.fighter_id = :fighter_id
                    GROUP BY e.event_brand
                )
                SELECT 
                    t.tournament_name,
                    t.country_code,
                    t.event_country,
                    array_agg(t.year ORDER BY t.year) as years,
                    array_length(array_agg(t.year), 1) as year_count,
                    COALESCE(s.total_matches, 0) as total_matches,
                    COALESCE(s.total_events, 0) as total_events,
                    CAST(COALESCE(s.win_rate, 0) AS NUMERIC(10,1)) as win_rate,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'tournament', m.sub_tournament,
                                'year', m.year,
                                'type', m.medal_type
                            )
                        ) FILTER (WHERE m.medal_type IS NOT NULL),
                        '[]'::json
                    ) as medals,
                    MAX(t.latest_event_date) as latest_event_date,
                    ROUND(AVG(t.avg_fighters)::numeric, 0) as avg_fighters
                FROM tournament_years t
                LEFT JOIN tournament_stats s ON t.tournament_name = s.tournament_name
                LEFT JOIN medals m ON t.tournament_name = m.tournament_name
                GROUP BY t.tournament_name, t.country_code, t.event_country, s.total_matches, s.total_events, s.win_rate
                ORDER BY MAX(t.latest_event_date) DESC, year_count DESC
            """
            # queries["tournaments_query"] = tournaments_query
            tournaments_result = db.execute(
                text(tournaments_query), {"fighter_id": fighter_id}
            ).fetchall()

            # Get recent matches
            matches_query = """
                SELECT 
                    e.event_brand as event_name,
                    t.tournament_name,
                    COALESCE(f.fighter_name, 'Unknown Opponent') as opponent_name,
                    m.result,
                    t.tournament_weapon as weapon,
                    e.event_date,
                    m.win_chance
                FROM match_results m
                JOIN tournaments t ON m.tournament_id = t.tournament_id
                JOIN events e ON t.event_id = e.event_id
                LEFT JOIN fighters f ON m.opponent_id = f.fighter_id
                WHERE m.fighter_id = :fighter_id
                ORDER BY e.event_date DESC, m.fight_id DESC
            """
            # queries["matches_query"] = matches_query
            matches_result = db.execute(text(matches_query), {"fighter_id": fighter_id}).fetchall()

            # Get achievements
            achievements_query = """
                SELECT 
                    fighter_id,
                    achievement_name,
                    achievement_description,
                    achievement_icon,
                    achievement_tier,
                    percentile,
                    achieved
                FROM achievements
                WHERE fighter_id = :fighter_id
                ORDER BY percentile DESC
            """
            # queries["achievements_query"] = achievements_query
            achievements_result = db.execute(
                text(achievements_query), {"fighter_id": fighter_id}
            ).fetchall()

            # Get countries visited with statistics
            countries_query = """
                SELECT 
                    e.event_country as name,
                    c.country_code,
                    COUNT(DISTINCT e.event_id) as total_events,
                    COUNT(DISTINCT m.match_id) as total_matches,
                    SUM(CASE WHEN m.result = 'WIN' THEN 1 ELSE 0 END) as wins
                FROM match_results m
                JOIN tournaments t ON m.tournament_id = t.tournament_id
                JOIN events e ON t.event_id = e.event_id
                LEFT JOIN countries c ON LOWER(e.event_country) = LOWER(c.country_name)
                WHERE m.fighter_id = :fighter_id
                AND e.event_country IS NOT NULL
                GROUP BY e.event_country, c.country_code
                HAVING COUNT(DISTINCT e.event_id) > 0
                ORDER BY e.event_country
            """
            countries = db.execute(text(countries_query), {"fighter_id": fighter_id}).fetchall()

            # Convert country names to codes and add to fighter data
            fighter_data["countries_visited"] = []
            for country in countries:
                country_data = {
                    "name": country.name,
                    "country_code": country.country_code,
                    "total_events": country.total_events,
                    "total_matches": country.total_matches,
                    "wins": country.wins,
                }
                fighter_data["countries_visited"].append({**country_data})

            # Build complete fighter object
            fighter = {
                "fighter_id": fighter_data["fighter_id"],
                "fighter_name": fighter_data["fighter_name"],
                "fighter_nationality": fighter_data["fighter_nationality"],
                "fighter_club_name": fighter_data["fighter_club_name"],
                "country_code": fighter_data["country_code"],
                "rank_longsword": fighter_data["rank_longsword"],
                "stats": {
                    "win_rate": stats_result.win_rate,
                    "total_matches": stats_result.total_matches if stats_result else 0,
                    "wins": stats_result.wins if stats_result else 0,
                    "total_events": stats_result.total_events if stats_result else 0,
                },
                "weapons_usage": [
                    {"weapon": row.weapon, "matches": row.matches} for row in weapons_result
                ],
                "tournament_attendance": [
                    {
                        "tournament_name": row.tournament_name,
                        "country_code": row.country_code.lower() if row.country_code else None,
                        "event_country": row.event_country,
                        "years": row.years,
                        "total_events": row.total_events,
                        "total_matches": row.total_matches,
                        "win_rate": row.win_rate,
                        "avg_fighters": row.avg_fighters,
                        "medals": row.medals if row.medals else [],
                    }
                    for row in tournaments_result
                ],
                "recent_matches": [
                    {
                        "event_name": row.event_name,
                        "tournament_name": row.tournament_name,
                        "opponent_name": row.opponent_name,
                        "result": row.result,
                        "weapon": row.weapon,
                        "event_date": str(row.event_date),
                        "win_chance": float(row.win_chance) if row.win_chance is not None else None
                    }
                    for row in matches_result
                ],
                "achievements": [
                    {
                        "achievement_name": row.achievement_name,
                        "achievement_description": row.achievement_description,
                        "achievement_icon": row.achievement_icon,
                        "achievement_tier": row.achievement_tier,
                        "percentile": row.percentile,
                        "achieved": row.achieved,
                    }
                    for row in achievements_result
                ],
            }
            fighters.append(fighter)

        return FighterResponse(
            success=True,
            message="Fighters retrieved successfully",
            error=None,
            sql_query=None,  # Removed queries from response
            sql_params=None,  # Removed params from response
            data=fighters,
            total=total,
            page=skip // limit + 1,
            size=limit,
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        return FighterResponse(
            success=False,
            message="Error executing database query",
            error=str(e),
            sql_query=None,  # Removed query from error response
            sql_params=None,  # Removed params from error response
            data=[],
            total=0,
            page=1,
            size=limit,
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return FighterResponse(
            success=False,
            message="Unexpected error occurred",
            error=str(e),
            sql_query=None,  # Removed query from error response
            sql_params=None,  # Removed params from error response
            data=[],
            total=0,
            page=1,
            size=limit,
        )
