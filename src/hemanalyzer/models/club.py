from typing import List, Optional

from pydantic import BaseModel


class Club(BaseModel):
    club_id: int
    club_name: str
    club_code: Optional[str] = None
    club_country: Optional[str] = None
    club_state: Optional[str] = None
    club_city: Optional[str] = None
    club_members: Optional[int] = None
    parent_club: Optional[str] = None
    club_url: Optional[str] = None
    fighter_ids: List[int] = []


class ClubList(BaseModel):
    items: List[Club]
    total: int
    page: int
    size: int
