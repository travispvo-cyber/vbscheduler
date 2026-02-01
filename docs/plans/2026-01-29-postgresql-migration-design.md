# VB Scheduler: PostgreSQL Migration & Public Games Design

**Date:** 2026-01-29
**Status:** Approved

## Problem

SQLite database resets on Render deploys, breaking invite links and losing game data. Current landing page only shows games from localStorage, not useful for new visitors.

## Solution

Migrate to Render PostgreSQL for reliable persistence. Add organizer identity system. Display all public upcoming games on landing page.

---

## Database Schema

### organizers (new)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key, generated client-side |
| name | TEXT | Display name, editable |
| created_at | TIMESTAMP | Default now() |

### games (modified)
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT | Primary key, URL-safe token (e.g., `jK3xDf_p`) |
| organizer_id | UUID | FK to organizers |
| title | TEXT | Game title |
| venue | TEXT | Venue name |
| game_date | DATE | Game date |
| start_time | TEXT | HH:MM format |
| end_time | TEXT | HH:MM format |
| max_players | INTEGER | Venue max |
| min_players | INTEGER | Venue min |
| selected_days | JSONB | Array of days |
| organizer_pin | TEXT | Optional edit PIN |
| created_at | TIMESTAMP | Default now() |

### players (unchanged structure)
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | Primary key |
| game_id | TEXT | FK to games |
| name | TEXT | Player name |
| avatar_url | TEXT | Optional avatar |
| created_at | TIMESTAMP | Default now() |

### availability (unchanged structure)
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | Primary key |
| game_id | TEXT | FK to games |
| player_id | INTEGER | FK to players |
| day | TEXT | Day name |
| time_slot | TEXT | HH:MM format |
| status | TEXT | available/unavailable |
| updated_at | TIMESTAMP | Default now() |

---

## API Changes

### New Endpoints
- `POST /api/organizers` — Create organizer record
- `GET /api/organizers/{id}` — Get organizer profile
- `PUT /api/organizers/{id}` — Update organizer name
- `GET /api/organizers/{id}/games` — List organizer's games

### Modified Endpoints
- `POST /api/games` — Requires `X-Organizer-Token` header
- `GET /api/games` — Returns all upcoming public games with organizer info
- `PUT /api/games/{id}` — Auth via token match OR PIN
- `DELETE /api/games/{id}` — Auth via token match OR PIN

### Auth Header
```
X-Organizer-Token: <uuid>
```

---

## Frontend Changes

### Organizer Identity Flow
1. Check localStorage for `organizer_token`
2. On "Create Game" click, generate UUID if missing
3. Store token in localStorage
4. Send token via header on game create/edit/delete

### Landing Page
- Fetch all upcoming games from `GET /api/games`
- Display game cards with organizer attribution
- Filter tabs: "All Games" / "My Games"
- Show player response counts and best time summary

### Game Card Display
- Title, venue, date/time
- "Created by {name}" (clickable)
- Response count: "8/12 responded"
- Best time hint

---

## Migration Strategy

1. Create Render PostgreSQL database
2. Add `DATABASE_URL` env var
3. Update dependencies (add psycopg2-binary)
4. Refactor database.py for PostgreSQL
5. Update SQL syntax in queries
6. Update frontend with organizer token logic
7. Update landing page UI
8. Deploy

**Note:** Existing data will not be migrated. Fresh start.

---

## Environment Notes

- Render Pro subscription active
- PostgreSQL connection via `DATABASE_URL` env var
