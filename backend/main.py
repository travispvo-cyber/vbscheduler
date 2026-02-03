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


@app.get("/api/organizers/{organizer_id}/player-history")
def get_player_history(organizer_id: str, q: str = ""):
    """Get player name suggestions for autocomplete."""
    with get_db() as conn:
        cursor = conn.cursor()
        if q:
            cursor.execute("""
                SELECT player_name FROM player_history
                WHERE organizer_id = %s AND player_name ILIKE %s
                ORDER BY last_used DESC
                LIMIT 20
            """, (organizer_id, f"%{q}%"))
        else:
            cursor.execute("""
                SELECT player_name FROM player_history
                WHERE organizer_id = %s
                ORDER BY last_used DESC
                LIMIT 20
            """, (organizer_id,))
        rows = cursor.fetchall()
        return [row["player_name"] for row in rows]


# ============ GAMES ============

@app.post("/api/games", response_model=GameResponse)
def create_game(game: GameCreate, x_organizer_token: Optional[str] = Header(None)):
    game_id = generate_game_id()

    with get_db() as conn:
        cursor = conn.cursor()

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
def add_player(game_id: str, player: PlayerCreate, x_organizer_token: Optional[str] = Header(None)):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id, organizer_id FROM games WHERE id = %s", (game_id,))
        game = cursor.fetchone()
        if not game:
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

        # Record to player history for the game's organizer
        if game["organizer_id"]:
            cursor.execute("""
                INSERT INTO player_history (organizer_id, player_name, last_used)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (organizer_id, player_name)
                DO UPDATE SET last_used = CURRENT_TIMESTAMP
            """, (game["organizer_id"], player.name))

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
