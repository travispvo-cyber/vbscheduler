# VB Scheduler - Development Guide

## Project Overview

Volleyball scheduler app for coordinating games with friends. FastAPI backend, SQLite database, vanilla HTML/JS frontend.

**Stack:** Python 3.11, FastAPI, PostgreSQL (Render), Tailwind CSS

**Hosting:** Render Pro subscription

## Development Workflow

```sh
# 1. Setup (first time)
cd backend && pip install -r requirements.txt

# 2. Run locally
cd backend && python main.py
# Or: cd backend && uvicorn main:app --reload

# 3. Test API
curl http://localhost:8000/api/health

# 4. Before committing
# - Test all endpoints manually
# - Verify static pages load
# - Check for Python syntax errors
python -m py_compile backend/*.py
```

## Project Structure

```
vbscheduler/
├── backend/           # FastAPI application
│   ├── main.py        # Routes and app setup
│   ├── models.py      # Pydantic schemas
│   ├── database.py    # SQLite connection
│   └── config.py      # Environment config
├── static/            # Frontend HTML files
├── data/              # SQLite database (gitignored)
└── .claude/agents/    # Custom agents
```

## Custom Agents

Use these agents for specific tasks:

| Agent | When to Use |
|-------|-------------|
| `@build-validator` | Before deploying - validates build |
| `@code-architect` | Planning new features or refactoring |
| `@code-simplifier` | After implementing - reduce complexity |
| `@oncall-guide` | Debugging production issues |
| `@verify-app` | Testing full user flows |

## API Endpoints

```
POST   /api/games                    Create game
GET    /api/games/{id}               Get game details
POST   /api/games/{id}/players       Add player
GET    /api/games/{id}/players       List players
POST   /api/games/{id}/availability  Submit availability
GET    /api/games/{id}/availability  Get all availability
GET    /api/games/{id}/heatmap       Get availability heatmap
GET    /api/health                   Health check
```

## Key Files to Know

- `backend/main.py:41-91` - Game CRUD endpoints
- `backend/main.py:96-130` - Player endpoints
- `backend/main.py:134-212` - Availability & heatmap
- `backend/database.py:24-70` - Schema definitions
- `static/landing.html:88-126` - Game creation JS
- `static/playeravail.html:233-267` - Availability submission JS

## Environment Variables

Copy `.env.example` to `.env`:
```
PORT=8000
DEBUG=true
CORS_ORIGINS=*
```

## Common Mistakes to Avoid

- **Don't** hardcode localhost URLs in HTML - use relative `/api` paths
- **Don't** commit `.env` or `*.db` files
- **Don't** forget to run `init_db()` on startup
- **Do** use `secrets.token_urlsafe()` for game IDs
- **Do** handle player name uniqueness per game

## Deployment (Render)

```
Build: pip install -r backend/requirements.txt
Start: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

Database: Render PostgreSQL (connection via `DATABASE_URL` env var)
