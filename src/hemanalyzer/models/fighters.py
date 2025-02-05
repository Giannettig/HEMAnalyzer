from typing import Dict, List, Optional

from pydantic import BaseModel


class WeaponUsage(BaseModel):
    weapon: str
    matches: int

class Stats(BaseModel):
    win_rate: str
    total_matches: int
    total_events: int
    wins: int

class RecentMatch(BaseModel):
    event_name: str
    event_date: str
    tournament_name: str
    opponent_name: str
    win_chance: float
    result: str
    weapon: str

class Medal(BaseModel):
    tournament: str
    year: int
    type: str

class TournamentAttendance(BaseModel):
    tournament_name: str
    country_code: Optional[str]
    event_country: str
    years: List[int]
    total_matches: int
    win_rate: float
    avg_fighters: int
    medals: List[Medal]

class Achievement(BaseModel):
    achievement_name: str
    achievement_description: str
    achievement_icon: str
    achievement_tier: str
    percentile: float
    achieved: bool

class FighterBase(BaseModel):
    fighter_id: int
    fighter_name: str
    fighter_club_name: Optional[str]
    fighter_nationality: Optional[str]
    country_code: Optional[str]
    rank_longsword: Optional[float]

class Fighter(BaseModel):
    fighter_id: int
    fighter_name: str
    fighter_nationality: Optional[str]
    fighter_club_name: Optional[str]
    country_code: Optional[str]
    rank_longsword: Optional[float]
    stats: Stats
    weapons_usage: List[WeaponUsage]
    tournament_attendance: List[TournamentAttendance]
    recent_matches: List[RecentMatch]
    achievements: List[Achievement]

class FighterResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str]
    sql_query: Optional[Dict[str, str]]
    sql_params: Optional[Dict]
    data: List[Fighter]
    total: int
    page: int
    size: int
