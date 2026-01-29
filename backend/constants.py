# backend/constants.py
"""Application constants - single source of truth for configuration values."""

VENUES = [
    {"id": "beach", "name": "Beach", "icon": "beach_access"},
    {"id": "gym", "name": "Indoor Gym", "icon": "fitness_center"},
    {"id": "park", "name": "Park", "icon": "park"},
]

TIME_SLOTS = [
    "09:00", "10:00", "11:00", "12:00", "13:00",
    "14:00", "15:00", "16:00", "17:00"
]

DAYS = ["saturday", "sunday"]

MAX_PLAYERS_DEFAULT = 12
MAX_PLAYERS_MIN = 4
MAX_PLAYERS_MAX = 30

GAME_TITLE_DEFAULT = "Volleyball Game"
GAME_TITLE_MAX_LENGTH = 50

PLAYER_NAME_MAX_LENGTH = 30

# Predefined player roster
PLAYER_ROSTER = [
    "David", "Jasmine", "Mike", "Travis", "Luis",
    "Andy", "May", "Gerry", "Justice", "Olivia",
    "Ruben", "Alex", "Guest 1", "Guest 2"
]
