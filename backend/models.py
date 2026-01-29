from pydantic import BaseModel
from typing import Optional
from datetime import date


class GameCreate(BaseModel):
    title: str
    venue: str
    game_date: str  # YYYY-MM-DD format
    start_time: str = "09:00"
    end_time: str = "17:00"
    max_players: int = 12
    organizer_name: Optional[str] = None


class GameResponse(BaseModel):
    id: str
    title: str
    venue: str
    game_date: str
    start_time: str
    end_time: str
    max_players: int
    created_at: str
    organizer_name: Optional[str] = None


class PlayerCreate(BaseModel):
    name: str
    avatar_url: Optional[str] = None


class PlayerResponse(BaseModel):
    id: int
    game_id: str
    name: str
    avatar_url: Optional[str] = None
    created_at: str


class AvailabilityCreate(BaseModel):
    player_id: int
    day: str  # "saturday" or "sunday"
    time_slot: str  # "09:00", "10:00", etc.
    status: str  # "available" or "unavailable"


class AvailabilityBulkCreate(BaseModel):
    player_id: int
    day: str
    slots: dict[str, str]  # {"09:00": "available", "10:00": "unavailable", ...}


class AvailabilityResponse(BaseModel):
    id: int
    game_id: str
    player_id: int
    player_name: str
    day: str
    time_slot: str
    status: str
    updated_at: str


class HeatmapSlot(BaseModel):
    time_slot: str
    available_count: int
    total_count: int
    available_players: list[str]


class HeatmapResponse(BaseModel):
    day: str
    slots: list[HeatmapSlot]
