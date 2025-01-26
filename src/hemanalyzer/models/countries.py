from typing import List, Optional

from pydantic import BaseModel


class Country(BaseModel):
    country_id: int
    country_name: str
    country_code: Optional[str] = None
    region: Optional[str] = None
    sub_region: Optional[str] = None
    active_fencers: Optional[int] = None
    community: Optional[int] = None
    community_label: Optional[str] = None


class CountryList(BaseModel):
    items: List[Country]
    total: int
    page: int
    size: int
