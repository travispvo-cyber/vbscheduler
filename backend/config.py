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
