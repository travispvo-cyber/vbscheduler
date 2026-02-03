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

        # Player history for autocomplete
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_history (
                id SERIAL PRIMARY KEY,
                organizer_id UUID NOT NULL REFERENCES organizers(id) ON DELETE CASCADE,
                player_name VARCHAR(100) NOT NULL,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(organizer_id, player_name)
            )
        """)

        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
