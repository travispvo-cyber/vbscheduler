import secrets
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from config import STATIC_DIR, CORS_ORIGINS, PORT, HOST, DEBUG
from database import get_db, init_db
from models import (
    GameCreate, GameResponse,
    PlayerCreate, PlayerResponse,
    AvailabilityCreate, AvailabilityBulkCreate, AvailabilityResponse,
    HeatmapSlot, HeatmapResponse,
    OrganizerAuth
)
from constants import VENUES, TIME_SLOTS, DAYS, MAX_PLAYERS_DEFAULT, MAX_PLAYERS_MIN, MAX_PLAYERS_MAX, PLAYER_ROSTER

app = FastAPI(
    title="VB Scheduler API",
    version="1.0.0",
    docs_url="/api/docs" if DEBUG else None,
    redoc_url="/api/redoc" if DEBUG else None,
)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("startup")
def startup():
    init_db()


def generate_game_id() -> str:
    return secrets.token_urlsafe(6)


# ============ GAMES ============

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


@app.get("/api/games/{game_id}", response_model=GameResponse)
def get_game(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found")
        data = dict(row)
        data.pop('organizer_pin', None)
        return GameResponse(**data)


@app.put("/api/games/{game_id}", response_model=GameResponse)
def update_game(game_id: str, game: GameCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE games SET title=?, venue=?, game_date=?, start_time=?, end_time=?, max_players=?, organizer_name=?, organizer_pin=?
            WHERE id = ?
        """, (game.title, game.venue, game.game_date, game.start_time, game.end_time, game.max_players, game.organizer_name, game.organizer_pin, game_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Game not found")

        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        data = dict(row)
        data.pop('organizer_pin', None)
        return GameResponse(**data)


@app.delete("/api/games/{game_id}")
def delete_game(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Game not found")
        return {"message": "Game deleted"}


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


# ============ PLAYERS ============

@app.post("/api/games/{game_id}/players", response_model=PlayerResponse)
def add_player(game_id: str, player: PlayerCreate):
    with get_db() as conn:
        cursor = conn.cursor()

        # Check game exists
        cursor.execute("SELECT id FROM games WHERE id = ?", (game_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Game not found")

        # Check if player already exists for this game
        cursor.execute("SELECT * FROM players WHERE game_id = ? AND name = ?", (game_id, player.name))
        existing = cursor.fetchone()
        if existing:
            return PlayerResponse(**dict(existing))

        # Add new player
        cursor.execute("""
            INSERT INTO players (game_id, name, avatar_url)
            VALUES (?, ?, ?)
        """, (game_id, player.name, player.avatar_url))

        cursor.execute("SELECT * FROM players WHERE id = ?", (cursor.lastrowid,))
        row = cursor.fetchone()
        return PlayerResponse(**dict(row))


@app.get("/api/games/{game_id}/players", response_model=list[PlayerResponse])
def get_players(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE game_id = ? ORDER BY created_at", (game_id,))
        rows = cursor.fetchall()
        return [PlayerResponse(**dict(row)) for row in rows]


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


@app.delete("/api/games/{game_id}/players/{player_id}")
def delete_player(game_id: str, player_id: int):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM players WHERE id = ? AND game_id = ?", (player_id, game_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Player not found")

        return {"message": "Player deleted"}


# ============ AVAILABILITY ============

@app.post("/api/games/{game_id}/availability")
def submit_availability(game_id: str, availability: AvailabilityBulkCreate):
    with get_db() as conn:
        cursor = conn.cursor()

        # Check game and player exist
        cursor.execute("SELECT id FROM games WHERE id = ?", (game_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Game not found")

        cursor.execute("SELECT id FROM players WHERE id = ?", (availability.player_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        # Upsert availability for each time slot
        for time_slot, status in availability.slots.items():
            cursor.execute("""
                INSERT INTO availability (game_id, player_id, day, time_slot, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(game_id, player_id, day, time_slot)
                DO UPDATE SET status = ?, updated_at = CURRENT_TIMESTAMP
            """, (game_id, availability.player_id, availability.day, time_slot, status, status))

        return {"message": "Availability saved"}


@app.get("/api/games/{game_id}/availability", response_model=list[AvailabilityResponse])
def get_availability(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, p.name as player_name
            FROM availability a
            JOIN players p ON a.player_id = p.id
            WHERE a.game_id = ?
            ORDER BY a.day, a.time_slot, p.name
        """, (game_id,))
        rows = cursor.fetchall()
        return [AvailabilityResponse(**dict(row)) for row in rows]


@app.get("/api/games/{game_id}/heatmap", response_model=list[HeatmapResponse])
def get_heatmap(game_id: str):
    with get_db() as conn:
        cursor = conn.cursor()

        # Get all time slots with counts
        cursor.execute("""
            SELECT
                a.day,
                a.time_slot,
                COUNT(CASE WHEN a.status = 'available' THEN 1 END) as available_count,
                COUNT(*) as total_count,
                GROUP_CONCAT(CASE WHEN a.status = 'available' THEN p.name END) as available_players
            FROM availability a
            JOIN players p ON a.player_id = p.id
            WHERE a.game_id = ?
            GROUP BY a.day, a.time_slot
            ORDER BY a.day, a.time_slot
        """, (game_id,))

        rows = cursor.fetchall()

        # Group by day
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
    """Return application configuration for frontend."""
    return {
        "venues": VENUES,
        "time_slots": TIME_SLOTS,
        "days": DAYS,
        "max_players": {
            "default": MAX_PLAYERS_DEFAULT,
            "min": MAX_PLAYERS_MIN,
            "max": MAX_PLAYERS_MAX
        },
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
