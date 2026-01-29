import sqlite3
from contextlib import contextmanager
from config import DATA_DIR

DB_PATH = DATA_DIR / "volleyball.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

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

        # Players table (per game, no accounts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                name TEXT NOT NULL,
                avatar_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                UNIQUE(game_id, name)
            )
        """)

        # Availability table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                player_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('available', 'unavailable')),
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
                UNIQUE(game_id, player_id, day, time_slot)
            )
        """)

        # Migration: Add organizer_pin if not exists
        try:
            cursor.execute("ALTER TABLE games ADD COLUMN organizer_pin TEXT")
        except:
            pass  # Column already exists

        # Migration: Add selected_days column (JSON array of days)
        try:
            cursor.execute("ALTER TABLE games ADD COLUMN selected_days TEXT DEFAULT '[\"saturday\", \"sunday\"]'")
        except:
            pass  # Column already exists

        # Migration: Add min_players column (venue-specific minimum)
        try:
            cursor.execute("ALTER TABLE games ADD COLUMN min_players INTEGER DEFAULT 4")
        except:
            pass  # Column already exists

        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
