#!/usr/bin/env python3
"""
Import seed data into local database for testing.

Usage:
    python scripts/import_seed_data.py

Reads from data/seed_data.json and imports into local database.
Requires DATABASE_URL to be set in .env file.
"""

import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from database import get_db, init_db


def import_data():
    """Import seed data from JSON file."""
    seed_file = Path(__file__).parent.parent / "data" / "seed_data.json"

    if not seed_file.exists():
        print(f"Error: {seed_file} not found")
        print("Run export_prod_data.py first to create seed data")
        sys.exit(1)

    with open(seed_file) as f:
        data = json.load(f)

    print(f"Loading seed data from {seed_file}")
    print(f"  Organizers: {len(data.get('organizers', []))}")
    print(f"  Games: {len(data.get('games', []))}")
    print(f"  Players: {len(data.get('players', []))}")
    print(f"  Availability: {len(data.get('availability', []))}")

    # Initialize database schema
    print("\nInitializing database schema...")
    init_db()

    with get_db() as conn:
        cursor = conn.cursor()

        # Import organizers
        for org in data.get("organizers", []):
            cursor.execute("""
                INSERT INTO organizers (id, name, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
            """, (org["id"], org["name"], org.get("created_at")))
        print(f"Imported {len(data.get('organizers', []))} organizers")

        # Import games
        for game in data.get("games", []):
            cursor.execute("""
                INSERT INTO games (id, organizer_id, title, venue, game_date, start_time, end_time, max_players, min_players, selected_days, organizer_pin, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    venue = EXCLUDED.venue,
                    selected_days = EXCLUDED.selected_days
            """, (
                game["id"],
                game.get("organizer_id"),
                game["title"],
                game["venue"],
                game["game_date"],
                game.get("start_time", "09:00"),
                game.get("end_time", "17:00"),
                game.get("max_players", 12),
                game.get("min_players", 4),
                json.dumps(game.get("selected_days", ["saturday", "sunday"])),
                game.get("organizer_pin"),
                game.get("created_at")
            ))
        print(f"Imported {len(data.get('games', []))} games")

        # Import players
        for player in data.get("players", []):
            cursor.execute("""
                INSERT INTO players (id, game_id, name, avatar_url, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (game_id, name) DO NOTHING
            """, (
                player["id"],
                player["game_id"],
                player["name"],
                player.get("avatar_url"),
                player.get("created_at")
            ))
        print(f"Imported {len(data.get('players', []))} players")

        # Import availability
        for avail in data.get("availability", []):
            cursor.execute("""
                INSERT INTO availability (game_id, player_id, day, time_slot, status, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_id, player_id, day, time_slot)
                DO UPDATE SET status = EXCLUDED.status
            """, (
                avail["game_id"],
                avail["player_id"],
                avail["day"],
                avail["time_slot"],
                avail["status"],
                avail.get("updated_at")
            ))
        print(f"Imported {len(data.get('availability', []))} availability records")

    print("\nSeed data imported successfully!")


if __name__ == "__main__":
    import_data()
