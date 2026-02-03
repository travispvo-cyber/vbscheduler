# VBScheduler UI Improvements Design

**Date:** 2026-02-02
**Branch:** feature/ui-improvements
**Status:** Approved

## Problem Statement

User feedback identified several UX issues:

1. **Date confusion** - Players see all days of the week when the game is only for one day (e.g., Sunday), causing confusion about which day to select
2. **Limited heatmap visibility** - Only 3-4 player names visible on heatmap; no way to see full list
3. **Orphaned guest entries** - Guests using incognito can't return to edit their submissions; organizers have no way to fix incorrect entries
4. **No player autocomplete** - Organizers must re-type player names for each game

## Scope

This design covers UI/UX improvements only. SMS notifications are deferred to a future release.

---

## Solution Design

### 1. Game Creation: Day-of-Week Selection

**Change:** Add day-of-week selection when creating a game.

**UI:**
```
Game Name: [Sunday VB 1/26       ]

Day of the week:
○ Sun  ○ Mon  ○ Tue  ○ Wed
○ Thu  ○ Fri  ○ Sat
```

**Behavior:**
- Organizer enters date in game title naturally (e.g., "Sunday VB 1/26")
- Organizer selects which day of the week this game is for
- Selection stored in database with game record
- Player availability page filters to only show the selected day

**Database change:**
- Add `day_of_week` column to `games` table (integer 0-6, where 0=Sunday)

### 2. Player Availability: Date Filtering

**Change:** Only display time slots for the game's selected day.

**Current behavior:** Shows full week of time slots regardless of game context.

**New behavior:** If game has `day_of_week = 0` (Sunday), only Sunday time slots appear.

**Implementation:**
- Read `day_of_week` from game record when loading availability page
- Filter time slot display to only show that day
- No changes to how players select times within that day

### 3. Heatmap: Player Tooltip

**Change:** Show all available players on hover.

**Behavior:**
- Hover over any time slot on heatmap
- Tooltip appears showing count + full list of names
- Example: "6 available: Travis, Mike, Sarah, Alex, Jordan, Chris"

**Implementation:**
- CSS tooltip (no JavaScript library needed)
- Position tooltip near cursor
- Mobile: tap-and-hold to trigger

### 4. Organizer Player Management

**Change:** New management view for organizers to control players.

**Location:** New tab on organizer page alongside heatmap.

**UI:**
```
[Heatmap]  [Manage Players]

+ Add Player  [Search or type name    ]

Players (6)
┌────────────────────────────────────┐
│ Travis ✓        [Edit] [Delete]    │
│ Mike ✓          [Edit] [Delete]    │
│ Guest 1 ✓       [Edit] [Delete]    │
│ Sarah  ⏳        [Edit] [Delete]    │
└────────────────────────────────────┘
✓ = submitted  ⏳ = pending
```

**Actions:**

| Action | Description |
|--------|-------------|
| Add Player | Create player entry, optionally set availability on their behalf |
| Edit | Change player name or modify their availability |
| Delete | Remove player and their availability from game |

**Autocomplete:**
- "Add Player" input has searchable dropdown
- Populated from organizer's player history (names from past games)
- Type to filter, or enter new name

### 5. Player History (Autocomplete Source)

**Change:** Store player names per organizer for autocomplete.

**Database:**
- New `player_history` table: `organizer_id`, `player_name`, `last_used`
- Populated when players join games
- Queried for autocomplete suggestions

---

## API Changes

### New Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/api/games/{id}/players/{player_id}` | Edit player name |
| DELETE | `/api/games/{id}/players/{player_id}` | Remove player |
| PUT | `/api/games/{id}/players/{player_id}/availability` | Organizer edits player's availability |
| GET | `/api/organizers/{id}/player-history` | Get autocomplete suggestions |

### Modified Endpoints

| Method | Endpoint | Change |
|--------|----------|--------|
| POST | `/api/games` | Accept `day_of_week` field |
| GET | `/api/games/{id}` | Return `day_of_week` in response |
| POST | `/api/games/{id}/players` | Allow organizer to set initial availability |

---

## Database Changes

### games table

Add column:
```sql
day_of_week INTEGER NOT NULL DEFAULT 0  -- 0=Sunday, 1=Monday, ..., 6=Saturday
```

### player_history table (new)

```sql
CREATE TABLE player_history (
    id SERIAL PRIMARY KEY,
    organizer_id INTEGER NOT NULL REFERENCES organizers(id),
    player_name VARCHAR(100) NOT NULL,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organizer_id, player_name)
);
```

---

## Frontend Changes

### landing.html (Game Creation)

- Add day-of-week radio button group
- Include selected day in POST request to create game

### playeravail.html (Player Availability)

- Fetch game's `day_of_week` on load
- Filter time slot grid to only show that day
- Update header to clarify which day is being shown

### Organizer Page (Heatmap + Management)

- Add tab navigation: "Heatmap" | "Manage Players"
- Heatmap: Add CSS tooltip on time slot hover
- Manage Players tab:
  - Player list with status indicators
  - Edit/Delete buttons per player
  - Add Player input with autocomplete dropdown

---

## Out of Scope

- SMS notifications (manual reminders, game announcements) - deferred to future release
- Multi-day game selection (single day per game is sufficient)
- Player accounts/authentication (guests remain anonymous)

---

## Implementation Order

1. Database migrations (add `day_of_week`, create `player_history`)
2. API changes (new endpoints, modified endpoints)
3. Game creation UI (day-of-week selection)
4. Player availability filtering (show only selected day)
5. Heatmap tooltip
6. Organizer player management tab
7. Player autocomplete
