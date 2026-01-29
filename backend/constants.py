# backend/constants.py
"""Application constants - single source of truth for configuration values."""

# Venues with player requirements
# Indoor T4: requires exactly 12 players
# Powder Keg (beach): requires 4, allows up to 8
VENUES = [
    {"id": "indoor", "name": "Indoor T4", "icon": "fitness_center", "min_players": 12, "max_players": 12},
    {"id": "beach", "name": "Powder Keg", "icon": "beach_access", "min_players": 4, "max_players": 8},
]

TIME_SLOTS = [
    "09:00", "10:00", "11:00", "12:00", "13:00",
    "14:00", "15:00", "16:00", "17:00", "18:00",
    "19:00", "20:00", "21:00", "22:00"
]

DAYS = ["saturday", "sunday"]

MAX_PLAYERS_DEFAULT = 12
MAX_PLAYERS_MIN = 4
MAX_PLAYERS_MAX = 12

GAME_TITLE_DEFAULT = "Volleyball Game"
GAME_TITLE_MAX_LENGTH = 50

PLAYER_NAME_MAX_LENGTH = 30

# Predefined player roster
PLAYER_ROSTER = [
    "David", "Jasmine", "Mike", "Travis", "Luis",
    "Andy", "May", "Gerry", "Justice", "Olivia",
    "Ruben", "Alex", "Guest 1", "Guest 2"
]
