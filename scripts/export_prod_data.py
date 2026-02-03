#!/usr/bin/env python3
"""
Export production game data for local testing.

Usage:
    Set PROD_DATABASE_URL env var or pass as argument:

    python scripts/export_prod_data.py "postgresql://user:pass@host:5432/db"

    Or set env var:
    PROD_DATABASE_URL="postgresql://..." python scripts/export_prod_data.py

Output:
    Creates data/seed_data.json with all games, players, and availability.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection(database_url: str):
    """Create database connection from URL."""
    parsed = urlparse(database_url)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        cursor_factory=RealDictCursor
    )


def export_data(database_url: str) -> dict:
    """Export all relevant data from database."""
    conn = get_connection(database_url)
    cursor = conn.cursor()

    data = {
        "exported_at": datetime.now().isoformat(),
        "organizers": [],
        "games": [],
        "players": [],
        "availability": []
    }

    # Export organizers
    cursor.execute("SELECT * FROM organizers ORDER BY created_at DESC")
    data["organizers"] = [dict(row) for row in cursor.fetchall()]
    print(f"Exported {len(data['organizers'])} organizers")

    # Export games (last 30 days)
    cursor.execute("""
        SELECT * FROM games
        WHERE game_date >= CURRENT_DATE - INTERVAL '30 days'
        ORDER BY game_date DESC
    """)
    data["games"] = [dict(row) for row in cursor.fetchall()]
    print(f"Exported {len(data['games'])} games")

    # Get game IDs for filtering players/availability
    game_ids = [g["id"] for g in data["games"]]

    if game_ids:
        # Export players for these games
        cursor.execute("""
            SELECT * FROM players
            WHERE game_id = ANY(%s)
            ORDER BY created_at
        """, (game_ids,))
        data["players"] = [dict(row) for row in cursor.fetchall()]
        print(f"Exported {len(data['players'])} players")

        # Export availability for these games
        cursor.execute("""
            SELECT * FROM availability
            WHERE game_id = ANY(%s)
            ORDER BY game_id, player_id, day, time_slot
        """, (game_ids,))
        data["availability"] = [dict(row) for row in cursor.fetchall()]
        print(f"Exported {len(data['availability'])} availability records")

    conn.close()

    # Convert datetime objects to strings for JSON
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__str__'):
            return str(obj)
        return obj

    for table in ["organizers", "games", "players", "availability"]:
        for row in data[table]:
            for key, value in row.items():
                row[key] = serialize(value)

    return data


def main():
    # Get database URL from argument or env var
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    else:
        database_url = os.getenv("PROD_DATABASE_URL")

    if not database_url:
        print("Error: No database URL provided")
        print("Usage: python scripts/export_prod_data.py 'postgresql://...'")
        print("   Or: PROD_DATABASE_URL='...' python scripts/export_prod_data.py")
        sys.exit(1)

    print("Connecting to production database...")
    data = export_data(database_url)

    # Save to file
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "seed_data.json"

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nData exported to: {output_file}")
    print(f"Total records: {sum(len(data[t]) for t in ['organizers', 'games', 'players', 'availability'])}")


if __name__ == "__main__":
    main()
