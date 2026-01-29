# VBScheduler Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance vbscheduler with configuration API, player management, input validation, and basic organizer authentication.

**Architecture:** Add a `/api/config` endpoint for dynamic settings, extend player/game CRUD operations, implement PIN-based organizer auth stored per-game, and standardize error responses across all endpoints.

**Tech Stack:** Python 3.11, FastAPI, SQLite, Pydantic, vanilla JavaScript

---

## Task 1: Fix Render Deployment Path

**Files:**
- Modify: `backend/config.py:20-23`

**Step 1: Read current config to understand path setup**

The config.py uses `DATA_DIR = ROOT_DIR / "data"` but Render mounts at `/opt/render/project/src/data`. We need to detect Render environment.

**Step 2: Update config.py to handle Render paths**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

# Server settings
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/volleyball.db")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Paths
ROOT_DIR = Path(__file__).parent.parent
STATIC_DIR = ROOT_DIR / "static"

# Data directory - use RENDER_DATA_DIR if on Render, otherwise local data/
if os.getenv("RENDER"):
    DATA_DIR = Path("/opt/render/project/src/data")
else:
    DATA_DIR = ROOT_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
```

**Step 3: Verify locally**

Run: `cd backend && python -c "from config import DATA_DIR; print(DATA_DIR)"`
Expected: `c:\Projects\vbscheduler\data` (local path)

**Step 4: Commit**

```bash
git add backend/config.py
git commit -m "fix: use RENDER env var for data directory detection"
```

---

## Task 2: Add Configuration Endpoint

**Files:**
- Modify: `backend/main.py:217` (before static file routes)
- Create: `backend/constants.py`

**Step 1: Create constants file**

```python
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
```

**Step 2: Run syntax check**

Run: `python -m py_compile backend/constants.py`
Expected: No output (success)

**Step 3: Add config endpoint to main.py**

Add import at top of main.py:
```python
from constants import VENUES, TIME_SLOTS, DAYS, MAX_PLAYERS_DEFAULT, MAX_PLAYERS_MIN, MAX_PLAYERS_MAX
```

Add endpoint before static files section:
```python
# ============ CONFIGURATION ============

@app.get("/api/config")
def get_config():
    """Return application configuration for frontend."""
    return {
        "venues": VENUES,
        "time_slots": TIME_SLOTS,
        "days": DAYS,
        "max_players": {
            "default": MAX_PLAYERS_DEFAULT,
            "min": MAX_PLAYERS_MIN,
            "max": MAX_PLAYERS_MAX
        }
    }
```

**Step 4: Test endpoint**

Run: `cd backend && python main.py &`
Run: `curl http://localhost:8000/api/config`
Expected: JSON with venues, time_slots, days, max_players

**Step 5: Commit**

```bash
git add backend/constants.py backend/main.py
git commit -m "feat: add /api/config endpoint for dynamic configuration"
```

---

## Task 3: Update Frontend to Use Config API

**Files:**
- Modify: `static/landing.html:91-95` (venue dropdown)
- Modify: `static/playermode.html:161` (time slots)

**Step 1: Update landing.html venue population**

Replace hardcoded venue options with dynamic fetch. Find the `<select id="venue">` and replace with:

```html
<select id="venue" class="w-full px-4 py-3 rounded-xl bg-gray-800 border border-gray-700 text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none">
    <option value="">Loading venues...</option>
</select>
```

Add to the `<script>` section, in the DOMContentLoaded handler:
```javascript
// Fetch config and populate venues
async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE}/config`);
        const config = await res.json();

        const venueSelect = document.getElementById('venue');
        venueSelect.innerHTML = config.venues.map(v =>
            `<option value="${v.id}">${v.name}</option>`
        ).join('');

        // Store config for later use
        window.appConfig = config;
    } catch (err) {
        console.error('Failed to load config:', err);
    }
}
loadConfig();
```

**Step 2: Update playermode.html time slots**

Find the `generateTimeSlots()` function and update:

```javascript
async function generateTimeSlots() {
    // Fetch config if not cached
    if (!window.appConfig) {
        try {
            const res = await fetch(`${API_BASE}/config`);
            window.appConfig = await res.json();
        } catch (err) {
            console.error('Failed to load config:', err);
            // Fallback to hardcoded
            window.appConfig = { time_slots: ['09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00'] };
        }
    }

    const container = document.getElementById('timeSlots');
    container.innerHTML = window.appConfig.time_slots.map(time => `
        <div class="grid grid-cols-12 gap-2 items-center h-11" data-time="${time}">
            <div class="col-span-2 text-sm text-gray-400">${formatTime(time)}</div>
            <button class="col-span-4 h-9 rounded-lg border border-gray-700 bg-gray-800 flex items-center justify-center status-btn"
                    data-status="none" onclick="cycleStatus(this, '${time}')">
                <span class="material-icons text-gray-500">help_outline</span>
            </button>
            <div class="col-span-6 h-9 rounded-lg bg-gray-800 flex items-center px-2 heatmap-cell" data-time="${time}">
                <span class="text-xs text-gray-500">-</span>
            </div>
        </div>
    `).join('');
}
```

**Step 3: Test in browser**

Open: `http://localhost:8000/`
Expected: Venue dropdown populated from API

Open: `http://localhost:8000/playermode.html?game=test`
Expected: Time slots generated from API config

**Step 4: Commit**

```bash
git add static/landing.html static/playermode.html
git commit -m "feat: use /api/config for dynamic venues and time slots"
```

---

## Task 4: Add Input Validation to Models

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/constants.py` (add to imports in models)

**Step 1: Update models.py with validation**

```python
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
    organizer_name: Optional[str] = Field(default=None, max_length=PLAYER_NAME_MAX_LENGTH)

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        if not v or not v.strip():
            return GAME_TITLE_DEFAULT
        return v.strip()


class GameResponse(BaseModel):
    id: str
    title: str
    venue: str
    game_date: str
    start_time: str
    end_time: str
    max_players: int
    organizer_name: Optional[str]
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
    day: str = Field(..., pattern=r"^(saturday|sunday)$")
    time_slot: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    status: str = Field(..., pattern=r"^(available|unavailable)$")


class AvailabilityBulkCreate(BaseModel):
    player_id: int
    day: str = Field(..., pattern=r"^(saturday|sunday)$")
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
```

**Step 2: Run syntax check**

Run: `python -m py_compile backend/models.py`
Expected: No output (success)

**Step 3: Test validation**

Run: `cd backend && python main.py &`
Run: `curl -X POST http://localhost:8000/api/games -H "Content-Type: application/json" -d '{"title":"","venue":"beach","game_date":"2024-02-01"}'`
Expected: Returns game with default title "Volleyball Game"

Run: `curl -X POST http://localhost:8000/api/games -H "Content-Type: application/json" -d '{"title":"Test","venue":"beach","game_date":"invalid"}'`
Expected: 422 Validation Error

**Step 4: Commit**

```bash
git add backend/models.py
git commit -m "feat: add input validation with Pydantic validators"
```

---

## Task 5: Add Player Edit/Delete Endpoints

**Files:**
- Modify: `backend/main.py:94-130` (player section)

**Step 1: Add update player endpoint**

Add after `get_players` endpoint:

```python
@app.put("/api/games/{game_id}/players/{player_id}", response_model=PlayerResponse)
def update_player(game_id: str, player_id: int, player: PlayerCreate):
    with get_db() as conn:
        cursor = conn.cursor()

        # Check player exists and belongs to game
        cursor.execute("SELECT * FROM players WHERE id = ? AND game_id = ?", (player_id, game_id))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Player not found")

        # Check name not already taken by another player in same game
        cursor.execute(
            "SELECT id FROM players WHERE game_id = ? AND name = ? AND id != ?",
            (game_id, player.name, player_id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Name already taken")

        cursor.execute(
            "UPDATE players SET name = ?, avatar_url = ? WHERE id = ?",
            (player.name, player.avatar_url, player_id)
        )

        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        return PlayerResponse(**dict(row))
```

**Step 2: Add delete player endpoint**

```python
@app.delete("/api/games/{game_id}/players/{player_id}")
def delete_player(game_id: str, player_id: int):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM players WHERE id = ? AND game_id = ?", (player_id, game_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Player not found")

        return {"message": "Player deleted"}
```

**Step 3: Test endpoints**

Create a game and player first:
```bash
GAME=$(curl -s -X POST http://localhost:8000/api/games -H "Content-Type: application/json" -d '{"title":"Test","venue":"beach","game_date":"2024-02-01"}' | jq -r '.id')
curl -X POST http://localhost:8000/api/games/$GAME/players -H "Content-Type: application/json" -d '{"name":"John"}'
```

Test update:
```bash
curl -X PUT http://localhost:8000/api/games/$GAME/players/1 -H "Content-Type: application/json" -d '{"name":"John Updated"}'
```
Expected: Returns updated player

Test delete:
```bash
curl -X DELETE http://localhost:8000/api/games/$GAME/players/1
```
Expected: `{"message":"Player deleted"}`

**Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: add player update and delete endpoints"
```

---

## Task 6: Add Organizer PIN Authentication

**Files:**
- Modify: `backend/database.py` (add pin column)
- Modify: `backend/models.py` (add pin field)
- Modify: `backend/main.py` (add pin verification)

**Step 1: Update database schema**

Add `organizer_pin` column to games table in `database.py`:

```python
# Games table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        venue TEXT NOT NULL,
        game_date TEXT NOT NULL,
        start_time TEXT DEFAULT '09:00',
        end_time TEXT DEFAULT '17:00',
        max_players INTEGER DEFAULT 12,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        organizer_name TEXT,
        organizer_pin TEXT
    )
""")
```

**Step 2: Add migration for existing databases**

Add at end of `init_db()`:
```python
# Migration: Add organizer_pin if not exists
try:
    cursor.execute("ALTER TABLE games ADD COLUMN organizer_pin TEXT")
except:
    pass  # Column already exists
```

**Step 3: Update models.py**

Add to `GameCreate`:
```python
organizer_pin: Optional[str] = Field(default=None, min_length=4, max_length=6, pattern=r"^\d{4,6}$")
```

Add new model:
```python
class OrganizerAuth(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, pattern=r"^\d{4,6}$")
```

**Step 4: Update create_game in main.py**

```python
@app.post("/api/games", response_model=GameResponse)
def create_game(game: GameCreate):
    game_id = generate_game_id()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO games (id, title, venue, game_date, start_time, end_time, max_players, organizer_name, organizer_pin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, game.title, game.venue, game.game_date, game.start_time, game.end_time, game.max_players, game.organizer_name, game.organizer_pin))

        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        # Don't return pin in response
        data = dict(row)
        data.pop('organizer_pin', None)
        return GameResponse(**data)
```

**Step 5: Add PIN verification endpoint**

```python
@app.post("/api/games/{game_id}/verify-pin")
def verify_organizer_pin(game_id: str, auth: OrganizerAuth):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT organizer_pin FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found")

        if not row["organizer_pin"]:
            # No PIN set, allow access
            return {"verified": True, "message": "No PIN required"}

        if row["organizer_pin"] != auth.pin:
            raise HTTPException(status_code=401, detail="Invalid PIN")

        return {"verified": True}
```

**Step 6: Test PIN flow**

Create game with PIN:
```bash
curl -X POST http://localhost:8000/api/games -H "Content-Type: application/json" -d '{"title":"Private Game","venue":"beach","game_date":"2024-02-01","organizer_pin":"1234"}'
```

Verify PIN:
```bash
curl -X POST http://localhost:8000/api/games/$GAME/verify-pin -H "Content-Type: application/json" -d '{"pin":"1234"}'
```
Expected: `{"verified": true}`

Wrong PIN:
```bash
curl -X POST http://localhost:8000/api/games/$GAME/verify-pin -H "Content-Type: application/json" -d '{"pin":"0000"}'
```
Expected: 401 Unauthorized

**Step 7: Commit**

```bash
git add backend/database.py backend/models.py backend/main.py
git commit -m "feat: add organizer PIN authentication for games"
```

---

## Task 7: Standardize Error Responses

**Files:**
- Modify: `backend/main.py` (add exception handler)

**Step 1: Add custom exception handler**

Add after app initialization:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error",
            "path": str(request.url.path)
        }
    )
```

**Step 2: Test error responses**

Run: `curl http://localhost:8000/api/games/nonexistent`
Expected:
```json
{
    "error": true,
    "status_code": 404,
    "message": "Game not found",
    "path": "/api/games/nonexistent"
}
```

**Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: standardize error response format"
```

---

## Task 8: Update Frontend Error Handling

**Files:**
- Modify: `static/landing.html`
- Modify: `static/playeravail.html`
- Modify: `static/playermode.html`

**Step 1: Create reusable error display function**

Add to all three HTML files in the `<script>` section:

```javascript
function showError(message) {
    // Remove existing error toasts
    document.querySelectorAll('.error-toast').forEach(el => el.remove());

    const toast = document.createElement('div');
    toast.className = 'error-toast fixed bottom-20 left-1/2 -translate-x-1/2 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 4000);
}

async function apiCall(url, options = {}) {
    try {
        const res = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.message || 'Request failed');
        }

        return data;
    } catch (err) {
        showError(err.message);
        throw err;
    }
}
```

**Step 2: Update API calls in landing.html**

Replace direct fetch calls with apiCall:
```javascript
// Before
const res = await fetch(`${API_BASE}/games`, { method: 'POST', ... });

// After
const data = await apiCall(`${API_BASE}/games`, { method: 'POST', body: JSON.stringify(gameData) });
```

**Step 3: Test error display**

Open browser console, trigger an error (e.g., invalid game ID)
Expected: Red toast appears at bottom with error message

**Step 4: Commit**

```bash
git add static/landing.html static/playeravail.html static/playermode.html
git commit -m "feat: add consistent error handling and display in frontend"
```

---

## Task 9: Final Integration Test

**Step 1: Start fresh server**

```bash
cd backend
rm -f ../data/volleyball.db
python main.py
```

**Step 2: Test complete flow**

```bash
# Create game with PIN
GAME=$(curl -s -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{"title":"Saturday Volleyball","venue":"beach","game_date":"2024-02-03","organizer_pin":"1234"}' \
  | jq -r '.id')
echo "Game ID: $GAME"

# Get config
curl http://localhost:8000/api/config

# Add players
curl -X POST http://localhost:8000/api/games/$GAME/players \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}'

curl -X POST http://localhost:8000/api/games/$GAME/players \
  -H "Content-Type: application/json" \
  -d '{"name":"Bob"}'

# Submit availability
curl -X POST http://localhost:8000/api/games/$GAME/availability \
  -H "Content-Type: application/json" \
  -d '{"player_id":1,"day":"saturday","slots":{"09:00":"available","10:00":"available"}}'

# Get heatmap
curl http://localhost:8000/api/games/$GAME/heatmap

# Verify PIN
curl -X POST http://localhost:8000/api/games/$GAME/verify-pin \
  -H "Content-Type: application/json" \
  -d '{"pin":"1234"}'

# Health check
curl http://localhost:8000/api/health
```

**Step 3: Test frontend pages**

Open in browser:
- `http://localhost:8000/` - Create game, see config-populated venues
- `http://localhost:8000/playeravail.html?game=$GAME` - Submit availability
- `http://localhost:8000/playermode.html?game=$GAME` - Detailed time slots

**Step 4: Final commit**

```bash
git add -A
git status  # Verify no unwanted files
git commit -m "test: verify full integration after improvements"
```

---

## Summary

| Task | Description | Files Modified |
|------|-------------|----------------|
| 1 | Fix Render deployment path | config.py |
| 2 | Add configuration endpoint | main.py, constants.py |
| 3 | Update frontend to use config | landing.html, playermode.html |
| 4 | Add input validation | models.py |
| 5 | Add player edit/delete | main.py |
| 6 | Add organizer PIN auth | database.py, models.py, main.py |
| 7 | Standardize error responses | main.py |
| 8 | Update frontend error handling | all HTML files |
| 9 | Integration testing | - |

**Total commits:** 9
**Estimated tasks:** 35+ individual steps
