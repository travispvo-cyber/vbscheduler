# PostgreSQL Migration & Public Games Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate from SQLite to Render PostgreSQL, add organizer identity system, display all public upcoming games on landing page.

**Architecture:** Replace sqlite3 with psycopg2 for PostgreSQL. Add `organizers` table linked to games. Frontend generates/stores organizer UUID in localStorage, sends via header. Landing page fetches all public games from API.

**Tech Stack:** Python 3.11, FastAPI, PostgreSQL (Render), psycopg2-binary, Vanilla JS

---

## Task 1: Update Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add PostgreSQL driver**

```txt
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
python-multipart>=0.0.6
python-dotenv>=1.0.0
psycopg2-binary>=2.9.9
```

**Step 2: Verify syntax**

Run: `cd vbscheduler/backend && python -c "import psycopg2; print('OK')"` (after pip install)

**Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add psycopg2-binary for PostgreSQL support"
```

---

## Task 2: Update Config for PostgreSQL

**Files:**
- Modify: `backend/config.py`

**Step 1: Update config to parse DATABASE_URL**

Replace entire file with:

```python
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load .env file from project root
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

# Server settings
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Database - parse DATABASE_URL for PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "")

def get_db_config():
    """Parse DATABASE_URL into connection parameters."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required")

    parsed = urlparse(DATABASE_URL)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path[1:],  # Remove leading /
        "user": parsed.username,
        "password": parsed.password,
    }

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Paths
ROOT_DIR = Path(__file__).parent.parent
STATIC_DIR = ROOT_DIR / "static"
```

**Step 2: Commit**

```bash
git add backend/config.py
git commit -m "feat: update config to parse DATABASE_URL for PostgreSQL"
```

---

## Task 3: Rewrite Database Layer for PostgreSQL

**Files:**
- Modify: `backend/database.py`

**Step 1: Replace SQLite with PostgreSQL connection**

Replace entire file with:

```python
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config import get_db_config

@contextmanager
def get_db():
    """Get a database connection with automatic commit/rollback."""
    config = get_db_config()
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        database=config["database"],
        user=config["user"],
        password=config["password"],
        cursor_factory=RealDictCursor
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Organizers table (new)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizers (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Games table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                organizer_id UUID REFERENCES organizers(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                venue TEXT NOT NULL,
                game_date DATE NOT NULL,
                start_time TEXT DEFAULT '09:00',
                end_time TEXT DEFAULT '17:00',
                max_players INTEGER DEFAULT 12,
                min_players INTEGER DEFAULT 4,
                selected_days JSONB DEFAULT '["saturday", "sunday"]',
                organizer_pin TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                avatar_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, name)
            )
        """)

        # Availability table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS availability (
                id SERIAL PRIMARY KEY,
                game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                day TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('available', 'unavailable')),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, player_id, day, time_slot)
            )
        """)

        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
```

**Step 2: Commit**

```bash
git add backend/database.py
git commit -m "feat: rewrite database layer for PostgreSQL with organizers table"
```

---

## Task 4: Add Organizer Models

**Files:**
- Modify: `backend/models.py`

**Step 1: Add organizer models at end of file**

Add after `OrganizerAuth` class:

```python

class OrganizerCreate(BaseModel):
    id: str  # UUID as string
    name: str = Field(..., min_length=1, max_length=50)


class OrganizerResponse(BaseModel):
    id: str
    name: str
    created_at: str


class OrganizerUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
```

**Step 2: Update GameResponse to include organizer info**

Replace `GameResponse` class with:

```python
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
```

**Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: add organizer models and update GameResponse"
```

---

## Task 5: Update Main.py - Fix SQL Syntax for PostgreSQL

**Files:**
- Modify: `backend/main.py`

**Step 1: Update imports**

Replace the json import line:

```python
import json
```

With:

```python
import json
from psycopg2.extras import Json
```

**Step 2: Update all SQL queries to use %s instead of ?**

This is a multi-part edit. Replace each query one by one.

In `create_game()` function, replace:
```python
        cursor.execute("""
            INSERT INTO games (id, title, venue, game_date, start_time, end_time, max_players, min_players, selected_days, organizer_name, organizer_pin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, game.title, game.venue, game.game_date, game.start_time, game.end_time, game.max_players, game.min_players, selected_days_json, game.organizer_name, game.organizer_pin))
```

With:
```python
        cursor.execute("""
            INSERT INTO games (id, title, venue, game_date, start_time, end_time, max_players, min_players, selected_days, organizer_pin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (game_id, game.title, game.venue, game.game_date, game.start_time, game.end_time, game.max_players, game.min_players, Json(game.selected_days), game.organizer_pin))
```

**Step 3: Continue updating all other queries**

See Task 6 for the complete main.py rewrite (cleaner than piecemeal edits).

**Step 4: Commit after Task 6**

---

## Task 6: Complete Main.py Rewrite

**Files:**
- Modify: `backend/main.py`

**Step 1: Replace entire main.py**

This is the complete updated file with:
- PostgreSQL syntax (%s params)
- Organizer endpoints
- X-Organizer-Token header handling
- Updated game queries to join organizer name

```python
import json
import secrets
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg2.extras import Json
from config import STATIC_DIR, CORS_ORIGINS, PORT, HOST, DEBUG
from database import get_db, init_db
from models import (
    GameCreate, GameResponse,
    PlayerCreate, PlayerResponse,
    AvailabilityBulkCreate, AvailabilityResponse,
    HeatmapSlot, HeatmapResponse,
    OrganizerAuth, OrganizerCreate, OrganizerResponse, OrganizerUpdate
)
from constants import VENUES, TIME_SLOTS, DAYS, MAX_PLAYERS_DEFAULT, MAX_PLAYERS_MIN, MAX_PLAYERS_MAX, PLAYER_ROSTER

app = FastAPI(
    title="VB Scheduler API",
    version="2.0.0",
    docs_url="/api/docs" if DEBUG else None,
    redoc_url="/api/redoc" if DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "status_code": exc.status_code, "message": exc.detail, "path": str(request.url.path)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": True, "status_code": 500, "message": "Internal server error", "path": str(request.url.path)}
    )


@app.on_event("startup")
def startup():
    init_db()


def generate_game_id() -> str:
    return secrets.token_urlsafe(6)


# ============ ORGANIZERS ============

@app.post("/api/organizers", response_model=OrganizerResponse)
def create_organizer(organizer: OrganizerCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if already exists
        cursor.execute("SELECT * FROM organizers WHERE id = %s", (organizer.id,))
        existing = cursor.fetchone()
        if existing:
            return OrganizerResponse(**dict(existing))

        cursor.execute(
            "INSERT INTO organizers (id, name) VALUES (%s, %s) RETURNING *",
            (organizer.id, organizer.name)
        )
        row = cursor.fetchone()
        return OrganizerResponse(**dict(row))


@app.get("/api/organizers/{organizer_id}", response_model=OrganizerResponse)
def get_organizer(organizer_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizers WHERE id = %s", (organizer_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Organizer not found")
        return OrganizerResponse(**dict(row))


@app.put("/api/organizers/{organizer_id}", response_model=OrganizerResponse)
def update_organizer(organizer_id: str, update: OrganizerUpdate, x_organizer_token: Optional[str] = Header(None)):
    if x_organizer_token != organizer_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this organizer")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE organizers SET name = %s WHERE id = %s RETURNING *",
            (update.name, organizer_id)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Organizer not found")
        return OrganizerResponse(**dict(row))


@app.get("/api/organizers/{organizer_id}/games", response_model=list[GameResponse])
def get_organizer_games(organizer_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.*, o.name as organizer_name
            FROM games g
            LEFT JOIN organizers o ON g.organizer_id = o.id
            WHERE g.organizer_id = %s
            ORDER BY g.game_date DESC
        """, (organizer_id,))
        rows = cursor.fetchall()
        return [GameResponse(**dict(row)) for row in rows]


# ============ GAMES ============

@app.post("/api/games", response_model=GameResponse)
def create_game(game: GameCreate, x_organizer_token: Optional[str] = Header(None)):
    game_id = generate_game_id()

    with get_db() as conn:
        cursor = conn.cursor()

        # If organizer token provided, ensure organizer exists
        organizer_id = None
        organizer_name = None
        if x_organizer_token:
            cursor.execute("SELECT id, name FROM organizers WHERE id = %s", (x_organizer_token,))
            org = cursor.fetchone()
            if org:
                organizer_id = org["id"]
                organizer_name = org["name"]

        cursor.execute("""
            INSERT INTO games (id, organizer_id, title, venue, game_date, start_time, end_time, max_players, min_players, selected_days, organizer_pin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (game_id, organizer_id, game.title, game.venue, game.game_date, game.start_time, game.end_time, game.max_players, game.min_players, Json(game.selected_days), game.organizer_pin))

        row = cursor.fetchone()
        data = dict(row)
        data.pop('organizer_pin', None)
        data['organizer_name'] = organizer_name
        return GameResponse(**data)


@app.get("/api/games", response_model=list[GameResponse])
def list_games(days: int = 14, limit: int = 20):
    """List all upcoming public games."""
    from datetime import datetime, timedelta
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.*, o.name as organizer_name
            FROM games g
            LEFT JOIN organizers o ON g.organizer_id = o.id
            WHERE g.game_date >= %s
            ORDER BY g.game_date ASC, g.created_at DESC
            LIMIT %s
        """, (cutoff_date, limit))
        rows = cursor.fetchall()

        results = []
        for row in rows:
            data = dict(row)
            data.pop('organizer_pin', None)
            results.append(GameResponse(**data))
        return results


@app.get("/api/games/{game_id}", response_model=GameResponse)
def get_game(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.*, o.name as organizer_name
            FROM games g
            LEFT JOIN organizers o ON g.organizer_id = o.id
            WHERE g.id = %s
        """, (game_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found")
        data = dict(row)
        data.pop('organizer_pin', None)
        return GameResponse(**data)


@app.put("/api/games/{game_id}", response_model=GameResponse)
def update_game(game_id: str, game: GameCreate, x_organizer_token: Optional[str] = Header(None)):
    with get_db() as conn:
        cursor = conn.cursor()

        # Check authorization: must be organizer OR provide correct PIN
        cursor.execute("SELECT organizer_id, organizer_pin FROM games WHERE id = %s", (game_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Game not found")

        is_organizer = x_organizer_token and existing["organizer_id"] == x_organizer_token
        pin_matches = game.organizer_pin and existing["organizer_pin"] == game.organizer_pin

        if not is_organizer and not pin_matches and existing["organizer_pin"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this game")

        cursor.execute("""
            UPDATE games SET title=%s, venue=%s, game_date=%s, start_time=%s, end_time=%s, max_players=%s, min_players=%s, selected_days=%s, organizer_pin=%s
            WHERE id = %s
            RETURNING *
        """, (game.title, game.venue, game.game_date, game.start_time, game.end_time, game.max_players, game.min_players, Json(game.selected_days), game.organizer_pin, game_id))

        row = cursor.fetchone()

        # Get organizer name
        cursor.execute("SELECT name FROM organizers WHERE id = %s", (row["organizer_id"],))
        org = cursor.fetchone()

        data = dict(row)
        data.pop('organizer_pin', None)
        data['organizer_name'] = org["name"] if org else None
        return GameResponse(**data)


@app.delete("/api/games/{game_id}")
def delete_game(game_id: str, x_organizer_token: Optional[str] = Header(None)):
    with get_db() as conn:
        cursor = conn.cursor()

        # Check authorization
        cursor.execute("SELECT organizer_id FROM games WHERE id = %s", (game_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Game not found")

        is_organizer = x_organizer_token and existing["organizer_id"] == x_organizer_token
        if not is_organizer:
            raise HTTPException(status_code=403, detail="Not authorized to delete this game")

        cursor.execute("DELETE FROM games WHERE id = %s", (game_id,))
        return {"message": "Game deleted"}


@app.post("/api/games/{game_id}/verify-pin")
def verify_organizer_pin(game_id: str, auth: OrganizerAuth):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT organizer_pin FROM games WHERE id = %s", (game_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found")

        if not row["organizer_pin"]:
            return {"verified": True, "message": "No PIN required"}

        if row["organizer_pin"] != auth.pin:
            raise HTTPException(status_code=401, detail="Invalid PIN")

        return {"verified": True}


# ============ PLAYERS ============

@app.post("/api/games/{game_id}/players", response_model=PlayerResponse)
def add_player(game_id: str, player: PlayerCreate):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM games WHERE id = %s", (game_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Game not found")

        cursor.execute("SELECT * FROM players WHERE game_id = %s AND name = %s", (game_id, player.name))
        existing = cursor.fetchone()
        if existing:
            return PlayerResponse(**dict(existing))

        cursor.execute(
            "INSERT INTO players (game_id, name, avatar_url) VALUES (%s, %s, %s) RETURNING *",
            (game_id, player.name, player.avatar_url)
        )
        row = cursor.fetchone()
        return PlayerResponse(**dict(row))


@app.get("/api/games/{game_id}/players", response_model=list[PlayerResponse])
def get_players(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE game_id = %s ORDER BY created_at", (game_id,))
        rows = cursor.fetchall()
        return [PlayerResponse(**dict(row)) for row in rows]


@app.put("/api/games/{game_id}/players/{player_id}", response_model=PlayerResponse)
def update_player(game_id: str, player_id: int, player: PlayerCreate):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM players WHERE id = %s AND game_id = %s", (player_id, game_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        cursor.execute(
            "SELECT id FROM players WHERE game_id = %s AND name = %s AND id != %s",
            (game_id, player.name, player_id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Name already taken")

        cursor.execute(
            "UPDATE players SET name = %s, avatar_url = %s WHERE id = %s RETURNING *",
            (player.name, player.avatar_url, player_id)
        )
        row = cursor.fetchone()
        return PlayerResponse(**dict(row))


@app.delete("/api/games/{game_id}/players/{player_id}")
def delete_player(game_id: str, player_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM players WHERE id = %s AND game_id = %s", (player_id, game_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Player not found")
        return {"message": "Player deleted"}


# ============ AVAILABILITY ============

@app.post("/api/games/{game_id}/availability")
def submit_availability(game_id: str, availability: AvailabilityBulkCreate):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM games WHERE id = %s", (game_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Game not found")

        cursor.execute("SELECT id FROM players WHERE id = %s", (availability.player_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        for time_slot, status in availability.slots.items():
            cursor.execute("""
                INSERT INTO availability (game_id, player_id, day, time_slot, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(game_id, player_id, day, time_slot)
                DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
            """, (game_id, availability.player_id, availability.day, time_slot, status))

        return {"message": "Availability saved"}


@app.get("/api/games/{game_id}/availability", response_model=list[AvailabilityResponse])
def get_availability(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, p.name as player_name
            FROM availability a
            JOIN players p ON a.player_id = p.id
            WHERE a.game_id = %s
            ORDER BY a.day, a.time_slot, p.name
        """, (game_id,))
        rows = cursor.fetchall()
        return [AvailabilityResponse(**dict(row)) for row in rows]


@app.get("/api/games/{game_id}/heatmap", response_model=list[HeatmapResponse])
def get_heatmap(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                a.day,
                a.time_slot,
                COUNT(CASE WHEN a.status = 'available' THEN 1 END) as available_count,
                COUNT(*) as total_count,
                STRING_AGG(CASE WHEN a.status = 'available' THEN p.name END, ',') as available_players
            FROM availability a
            JOIN players p ON a.player_id = p.id
            WHERE a.game_id = %s
            GROUP BY a.day, a.time_slot
            ORDER BY a.day, a.time_slot
        """, (game_id,))

        rows = cursor.fetchall()

        heatmap = {}
        for row in rows:
            day = row["day"]
            if day not in heatmap:
                heatmap[day] = []

            available_players = row["available_players"].split(",") if row["available_players"] else []
            heatmap[day].append(HeatmapSlot(
                time_slot=row["time_slot"],
                available_count=row["available_count"],
                total_count=row["total_count"],
                available_players=available_players
            ))

        return [HeatmapResponse(day=day, slots=slots) for day, slots in heatmap.items()]


# ============ CONFIGURATION ============

@app.get("/api/config")
def get_config():
    return {
        "venues": VENUES,
        "time_slots": TIME_SLOTS,
        "days": DAYS,
        "max_players": {"default": MAX_PLAYERS_DEFAULT, "min": MAX_PLAYERS_MIN, "max": MAX_PLAYERS_MAX},
        "player_roster": PLAYER_ROSTER
    }


# ============ HEALTH CHECK ============

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# ============ STATIC FILES ============

@app.get("/")
def serve_landing():
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/landing.html")
def serve_landing_html():
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/playeravail.html")
def serve_playeravail():
    return FileResponse(STATIC_DIR / "playeravail.html")


@app.get("/playermode.html")
def serve_playermode():
    return FileResponse(STATIC_DIR / "playermode.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=DEBUG)
```

**Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: rewrite main.py for PostgreSQL with organizer endpoints"
```

---

## Task 7: Update Frontend - Add Organizer Token Logic

**Files:**
- Modify: `static/landing.html`

**Step 1: Add organizer token helper functions**

Find the `</script>` tag at the end of the script section (around line 904) and add these functions BEFORE it:

```javascript
        // ============ ORGANIZER IDENTITY ============

        function getOrganizerToken() {
            return localStorage.getItem('organizer_token');
        }

        function generateOrganizerToken() {
            // Generate UUID v4
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        async function ensureOrganizer(name = 'Organizer') {
            let token = getOrganizerToken();
            if (!token) {
                token = generateOrganizerToken();
                localStorage.setItem('organizer_token', token);
            }

            // Create/get organizer record on server
            try {
                await fetch(`${API_BASE}/organizers`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: token, name: name })
                });
            } catch (e) {
                console.error('Failed to create organizer:', e);
            }

            return token;
        }

        function getAuthHeaders() {
            const token = getOrganizerToken();
            return token ? { 'X-Organizer-Token': token } : {};
        }
```

**Step 2: Update createGame() to use organizer token**

Replace the `createGame()` function with:

```javascript
        async function createGame() {
            const title = document.getElementById('game-title').value || 'Volleyball Game';
            const venueId = document.getElementById('venue-select').value;

            const venueObj = window.appConfig?.venues?.find(v => v.id === venueId);
            const venueName = venueObj ? venueObj.name : venueId;
            const minPlayers = venueObj?.min_players || 4;
            const maxPlayers = venueObj?.max_players || 12;

            const selectedDays = [];
            if (document.getElementById('day-saturday')?.checked) selectedDays.push('saturday');
            if (document.getElementById('day-sunday')?.checked) selectedDays.push('sunday');

            if (selectedDays.length === 0) {
                showError('Please select at least one day');
                return;
            }

            const today = new Date();
            const dayOfWeek = today.getDay();
            const daysUntilSat = (6 - dayOfWeek + 7) % 7 || 7;
            const gameDate = new Date(today);
            gameDate.setDate(today.getDate() + daysUntilSat);
            const gameDateStr = gameDate.toISOString().split('T')[0];

            try {
                // Ensure organizer exists before creating game
                const organizerToken = await ensureOrganizer('Organizer');

                const res = await fetch(`${API_BASE}/games`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Organizer-Token': organizerToken
                    },
                    body: JSON.stringify({
                        title: title,
                        venue: venueName,
                        game_date: gameDateStr,
                        min_players: minPlayers,
                        max_players: maxPlayers,
                        selected_days: selectedDays
                    })
                });
                currentGame = await res.json();
                localStorage.setItem('currentGameId', currentGame.id);
                setAsHost(currentGame.id);
                addToGameHistory(currentGame.id, title, venueName, gameDateStr, true);
                displayGame();
                renderGameHistory();
                loadRecentGames();
                showShareLink();
            } catch (e) {
                console.error('Error creating game:', e);
                showError('Failed to create game');
            }
        }
```

**Step 3: Update deleteGame() to use auth header**

Replace the `deleteGame()` function with:

```javascript
        async function deleteGame(gameId) {
            try {
                const res = await fetch(`${API_BASE}/games/${gameId}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });

                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.message || 'Failed to delete game');
                }

                removeFromGameHistory(gameId);

                if (currentGame?.id === gameId) {
                    currentGame = null;
                    document.getElementById('game-title').value = '';
                    document.getElementById('roster-list').innerHTML = '<p class="text-center text-gray-500 py-8">Create a game to see the roster</p>';
                    document.getElementById('slot-counter').textContent = '0/12 Slots';
                    document.getElementById('heatmap-section')?.classList.add('hidden');
                    document.getElementById('create-game-btn').classList.remove('hidden');
                    document.getElementById('share-link-btn').classList.add('hidden');
                }

                renderGameHistory();
                loadRecentGames();
                showToast('Game deleted');

            } catch (e) {
                console.error('Error deleting game:', e);
                showError(e.message || 'Failed to delete game');
            }
        }
```

**Step 4: Update saveGameSettings() to use auth header**

Replace the `saveGameSettings()` function with:

```javascript
        async function saveGameSettings() {
            if (!currentGame || !isHostOfGame(currentGame.id)) return;

            const title = document.getElementById('game-title').value || 'Volleyball Game';
            const venueId = document.getElementById('venue-select').value;
            const venueObj = window.appConfig?.venues?.find(v => v.id === venueId);
            const venueName = venueObj ? venueObj.name : venueId;
            const minPlayers = venueObj?.min_players || 4;
            const maxPlayers = venueObj?.max_players || 12;

            const selectedDays = [];
            if (document.getElementById('day-saturday')?.checked) selectedDays.push('saturday');
            if (document.getElementById('day-sunday')?.checked) selectedDays.push('sunday');

            if (selectedDays.length === 0) {
                showError('Please select at least one day');
                document.getElementById('day-saturday').checked = true;
                return;
            }

            try {
                const res = await fetch(`${API_BASE}/games/${currentGame.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        ...getAuthHeaders()
                    },
                    body: JSON.stringify({
                        title: title,
                        venue: venueName,
                        game_date: currentGame.game_date,
                        min_players: minPlayers,
                        max_players: maxPlayers,
                        selected_days: selectedDays
                    })
                });
                currentGame = await res.json();
                showToast('Saved');
                displayGame();
            } catch (e) {
                console.error('Error saving game:', e);
                showError('Failed to save changes');
            }
        }
```

**Step 5: Commit**

```bash
git add static/landing.html
git commit -m "feat: add organizer token logic to landing page"
```

---

## Task 8: Update Landing Page - Show Organizer Name on Game Cards

**Files:**
- Modify: `static/landing.html`

**Step 1: Update loadRecentGames() to show organizer**

Replace the `loadRecentGames()` function with:

```javascript
        async function loadRecentGames() {
            const container = document.getElementById('recent-games-list');
            const section = document.getElementById('recent-games-section');
            if (!container) return;

            try {
                const res = await fetch(`${API_BASE}/games?days=14&limit=10`);
                if (!res.ok) throw new Error('Failed to load games');
                const games = await res.json();

                if (games.length === 0) {
                    section?.classList.add('hidden');
                    return;
                }

                section?.classList.remove('hidden');

                const history = getGameHistory();
                const visitedIds = new Set(history.map(g => g.id));
                const myToken = getOrganizerToken();

                container.innerHTML = games.map(game => {
                    const isVisited = visitedIds.has(game.id);
                    const isCurrentGame = currentGame?.id === game.id;
                    const isMine = game.organizer_id === myToken;
                    const gameDate = parseLocalDate(game.game_date);
                    const dateStr = gameDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
                    const organizerDisplay = game.organizer_name ? `by ${game.organizer_name}` : '';

                    return `
                    <div onclick="loadGame('${game.id}')"
                         class="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all
                                ${isCurrentGame ? 'bg-primary/10 border-2 border-primary' : 'bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800'}">
                        <div class="w-10 h-10 rounded-lg ${isCurrentGame ? 'bg-primary/20' : 'bg-gray-200 dark:bg-gray-700'} flex items-center justify-center">
                            <span class="material-symbols-outlined text-${isCurrentGame ? 'primary' : 'gray-400'} text-lg">sports_volleyball</span>
                        </div>
                        <div class="flex-1 min-w-0">
                            <p class="text-[#111418] dark:text-white text-sm font-semibold truncate">${game.title}</p>
                            <p class="text-gray-500 dark:text-gray-400 text-xs">${game.venue} · ${dateStr}</p>
                            ${organizerDisplay ? `<p class="text-gray-400 dark:text-gray-500 text-xs">${organizerDisplay}</p>` : ''}
                        </div>
                        <div class="flex items-center gap-1">
                            ${isMine ? '<span class="material-symbols-outlined text-primary text-sm" title="Your game">person</span>' : ''}
                            ${isVisited ? '<span class="material-symbols-outlined text-green-500 text-sm">check_circle</span>' : ''}
                        </div>
                    </div>`;
                }).join('');

            } catch (e) {
                console.error('Error loading recent games:', e);
                container.innerHTML = '<p class="text-center text-gray-400 py-4 text-sm">Could not load games</p>';
            }
        }
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: display organizer name on game cards"
```

---

## Task 9: Add "My Games" Filter Tab

**Files:**
- Modify: `static/landing.html`

**Step 1: Update the Recent Games section header**

Find this HTML block (around line 1049-1057):

```html
        <!-- Recent Games Section -->
        <div id="recent-games-section" class="pt-6">
            <div class="flex items-center justify-between px-4 pb-3">
                <h3 class="text-[#111418] dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">Recent Games</h3>
                <span class="text-xs text-gray-500 dark:text-gray-400">Last 14 days</span>
            </div>
```

Replace with:

```html
        <!-- Recent Games Section -->
        <div id="recent-games-section" class="pt-6">
            <div class="flex items-center justify-between px-4 pb-3">
                <div class="flex gap-2">
                    <button id="filter-all-btn" onclick="setGameFilter('all')" class="px-3 py-1 rounded-full text-xs font-bold bg-primary text-white">All Games</button>
                    <button id="filter-mine-btn" onclick="setGameFilter('mine')" class="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-500">My Games</button>
                </div>
                <span class="text-xs text-gray-500 dark:text-gray-400">Last 14 days</span>
            </div>
```

**Step 2: Add filter state and function**

Add after the `currentHeatmapDay` variable declaration:

```javascript
        let currentGameFilter = 'all';

        function setGameFilter(filter) {
            currentGameFilter = filter;

            // Update button styles
            const allBtn = document.getElementById('filter-all-btn');
            const mineBtn = document.getElementById('filter-mine-btn');

            if (filter === 'all') {
                allBtn.className = 'px-3 py-1 rounded-full text-xs font-bold bg-primary text-white';
                mineBtn.className = 'px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-500';
            } else {
                allBtn.className = 'px-3 py-1 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-500';
                mineBtn.className = 'px-3 py-1 rounded-full text-xs font-bold bg-primary text-white';
            }

            loadRecentGames();
        }
```

**Step 3: Update loadRecentGames() to respect filter**

In the `loadRecentGames()` function, after getting games from API, add filtering:

After this line:
```javascript
                const games = await res.json();
```

Add:
```javascript
                // Filter games if "My Games" selected
                const myToken = getOrganizerToken();
                const filteredGames = currentGameFilter === 'mine'
                    ? games.filter(g => g.organizer_id === myToken)
                    : games;

                if (filteredGames.length === 0) {
                    if (currentGameFilter === 'mine') {
                        container.innerHTML = '<p class="text-center text-gray-400 py-4 text-sm">You haven\'t created any games yet</p>';
                        section?.classList.remove('hidden');
                    } else {
                        section?.classList.add('hidden');
                    }
                    return;
                }
```

And change the `games.map()` to `filteredGames.map()` in the rendering section.

**Step 4: Commit**

```bash
git add static/landing.html
git commit -m "feat: add All Games / My Games filter tabs"
```

---

## Task 10: Update .env.example

**Files:**
- Modify: `vbscheduler/.env.example` (create if doesn't exist)

**Step 1: Add DATABASE_URL example**

```
PORT=8000
DEBUG=true
CORS_ORIGINS=*
DATABASE_URL=postgresql://user:password@host:5432/database
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add DATABASE_URL to .env.example"
```

---

## Task 11: Update render.yaml - Remove SQLite Disk

**Files:**
- Modify: `render.yaml`

**Step 1: Remove disk configuration (no longer needed with PostgreSQL)**

Replace entire file with:

```yaml
services:
  - type: web
    name: vbscheduler
    runtime: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: DEBUG
        value: "false"
      - key: CORS_ORIGINS
        value: "*"
      - key: DATABASE_URL
        fromDatabase:
          name: vbscheduler-db
          property: connectionString

databases:
  - name: vbscheduler-db
    plan: free
```

**Step 2: Commit**

```bash
git add render.yaml
git commit -m "feat: configure Render PostgreSQL database in render.yaml"
```

---

## Task 12: Test Locally with PostgreSQL

**Step 1: Set up local PostgreSQL (or use Render database URL)**

Create `.env` in vbscheduler root:

```
PORT=8000
DEBUG=true
CORS_ORIGINS=*
DATABASE_URL=postgresql://your_user:your_pass@localhost:5432/vbscheduler
```

Or use your Render database URL for testing against production DB.

**Step 2: Install dependencies**

Run: `cd vbscheduler/backend && pip install -r requirements.txt`

**Step 3: Start server**

Run: `cd vbscheduler/backend && python main.py`

**Step 4: Test endpoints**

```bash
# Health check
curl http://localhost:8000/api/health

# Create organizer
curl -X POST http://localhost:8000/api/organizers \
  -H "Content-Type: application/json" \
  -d '{"id": "test-uuid-1234", "name": "Test User"}'

# Create game with organizer
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -H "X-Organizer-Token: test-uuid-1234" \
  -d '{"title": "Test Game", "venue": "Indoor T4", "game_date": "2026-02-01", "min_players": 12, "max_players": 12, "selected_days": ["saturday"]}'

# List games
curl http://localhost:8000/api/games
```

**Step 5: Test frontend**

Open http://localhost:8000 in browser:
1. Click "Create Game" - should work and show share link
2. Check console for errors
3. Verify game appears in "Recent Games" with organizer name
4. Test "My Games" filter

---

## Task 13: Deploy to Render

**Step 1: Commit all changes**

```bash
git add -A
git commit -m "feat: complete PostgreSQL migration with organizer identity"
```

**Step 2: Push to trigger deploy**

```bash
git push origin main
```

**Step 3: Verify in Render dashboard**

1. Check that PostgreSQL database was created
2. Check that DATABASE_URL env var is set on web service
3. Check deploy logs for errors
4. Test production URL

---

## Task 14: Final Verification

**Step 1: Test full flow on production**

1. Open production URL
2. Create a game - verify organizer token generated
3. Copy invite link, open in incognito - verify game visible
4. Add player, submit availability
5. Return to main page - verify game shows in list with organizer name
6. Test "My Games" filter
7. Close browser, reopen - verify your games still show as yours

**Step 2: Announce to users**

Previous invite links will no longer work. Share new links.

---

## Summary of Files Changed

| File | Action |
|------|--------|
| `backend/requirements.txt` | Add psycopg2-binary |
| `backend/config.py` | Parse DATABASE_URL |
| `backend/database.py` | Rewrite for PostgreSQL + organizers table |
| `backend/models.py` | Add Organizer models, update GameResponse |
| `backend/main.py` | PostgreSQL syntax, organizer endpoints, auth headers |
| `static/landing.html` | Organizer token logic, game filter tabs, organizer display |
| `.env.example` | Add DATABASE_URL |
| `render.yaml` | Remove disk, add database config |
