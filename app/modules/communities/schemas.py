from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict


class CommunityBase(BaseModel):
    name: str
    centroid_latitude: float
    centroid_longitude: float
    polygon: Dict[str, Any]
    entry_points: List[Dict[str, Any]]
    avg_walk_time_min: float = 3.0
    batch_window_sec: int = 120
    max_batch_size: int = 4


class CommunityCreate(CommunityBase):
    id: str


class CommunityUpdate(BaseModel):
    name: Optional[str] = None
    centroid_latitude: Optional[float] = None
    centroid_longitude: Optional[float] = None
    polygon: Optional[Dict[str, Any]] = None
    entry_points: Optional[List[Dict[str, Any]]] = None
    avg_walk_time_min: Optional[float] = None
    batch_window_sec: Optional[int] = None
    max_batch_size: Optional[int] = None


class CommunityResponse(CommunityBase):
    id: str

    model_config = ConfigDict(
        from_attributes=True
    )