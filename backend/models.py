from pydantic import BaseModel, Field, field_validator
from typing import Optional
from constants import (
    GAME_TITLE_DEFAULT, GAME_TITLE_MAX_LENGTH,
    PLAYER_NAME_MAX_LENGTH, MAX_PLAYERS_MIN, MAX_PLAYERS_MAX, MAX_PLAYERS_DEFAULT
)


class GameCreate(BaseModel):
    title: str = Field(default=GAME_TITLE_DEFAULT, max_length=GAME_TITLE_MAX_LENGTH)
    venue: str = Field(..., min_length=1, max_length=50)
    game_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(default="17:00", pattern=r"^\d{2}:\d{2}$")
    max_players: int = Field(default=MAX_PLAYERS_DEFAULT, ge=MAX_PLAYERS_MIN, le=MAX_PLAYERS_MAX)
    min_players: int = Field(default=MAX_PLAYERS_MIN, ge=MAX_PLAYERS_MIN, le=MAX_PLAYERS_MAX)
    selected_days: list[str] = Field(default=["saturday", "sunday"])
    organizer_name: Optional[str] = Field(default=None, max_length=PLAYER_NAME_MAX_LENGTH)
    organizer_pin: Optional[str] = Field(default=None, min_length=4, max_length=6, pattern=r"^\d{4,6}$")

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        if not v or not v.strip():
            return GAME_TITLE_DEFAULT
        return v.strip()

    @field_validator('selected_days')
    @classmethod
    def validate_days(cls, v):
        valid_days = {'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'}
        for day in v:
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day '{day}'. Must be a valid day of the week")
        return [d.lower() for d in v]


class GameResponse(BaseModel):
    id: str
    title: str
    venue: str
    game_date: str
    start_time: str
    end_time: str
    max_players: int
    min_players: Optional[int] = 4
    selected_days: Optional[list[str]] = ["saturday", "sunday"]
    organizer_id: Optional[str] = None
    organizer_name: Optional[str] = None
    created_at: str


class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=PLAYER_NAME_MAX_LENGTH)
    avatar_url: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_cleaned(cls, v):
        return v.strip()


class PlayerResponse(BaseModel):
    id: int
    game_id: str
    name: str
    avatar_url: Optional[str]
    created_at: str


class AvailabilityCreate(BaseModel):
    player_id: int
    day: str = Field(..., pattern=r"^(sunday|monday|tuesday|wednesday|thursday|friday|saturday)$")
    time_slot: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    status: str = Field(..., pattern=r"^(available|unavailable)$")


class AvailabilityBulkCreate(BaseModel):
    player_id: int
    day: str = Field(..., pattern=r"^(sunday|monday|tuesday|wednesday|thursday|friday|saturday)$")
    slots: dict[str, str]

    @field_validator('slots')
    @classmethod
    def validate_slots(cls, v):
        for time_slot, status in v.items():
            if not status in ('available', 'unavailable'):
                raise ValueError(f"Invalid status '{status}' for slot {time_slot}")
        return v


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


class OrganizerAuth(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, pattern=r"^\d{4,6}$")


class OrganizerCreate(BaseModel):
    id: str  # UUID as string
    name: str = Field(..., min_length=1, max_length=50)


class OrganizerResponse(BaseModel):
    id: str
    name: str
    created_at: str


class OrganizerUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
