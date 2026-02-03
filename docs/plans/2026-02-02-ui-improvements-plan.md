# UI Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve VBScheduler UI with day-of-week selection, heatmap tooltips, and organizer player management.

**Architecture:** Extend existing day selection from Saturday/Sunday to all 7 days. Add CSS tooltips to heatmap. Create new "Manage Players" tab on organizer view with full CRUD capabilities. Store player name history per organizer for autocomplete.

**Tech Stack:** FastAPI, PostgreSQL, vanilla HTML/JS, Tailwind CSS

---

## Task 1: Expand Day Constants

**Files:**
- Modify: `backend/constants.py:18`

**Step 1: Update DAYS constant**

```python
DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
```

**Step 2: Verify change**

Run: `python -m py_compile backend/constants.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add backend/constants.py
git commit -m "feat: expand DAYS constant to all 7 days"
```

---

## Task 2: Update Day Validation in Models

**Files:**
- Modify: `backend/models.py:28-35`
- Modify: `backend/models.py:73`

**Step 1: Update GameCreate validator**

Replace the `validate_days` method:

```python
    @field_validator('selected_days')
    @classmethod
    def validate_days(cls, v):
        valid_days = {'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'}
        for day in v:
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day '{day}'. Must be a valid day of the week")
        return [d.lower() for d in v]
```

**Step 2: Update AvailabilityCreate day pattern**

Replace line 73:

```python
    day: str = Field(..., pattern=r"^(sunday|monday|tuesday|wednesday|thursday|friday|saturday)$")
```

**Step 3: Verify syntax**

Run: `python -m py_compile backend/models.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add backend/models.py
git commit -m "feat: allow all 7 days in game and availability models"
```

---

## Task 3: Add Player History Table

**Files:**
- Modify: `backend/database.py:84-86`

**Step 1: Add player_history table creation**

Insert before `conn.commit()` at line 86:

```python
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
```

**Step 2: Verify syntax**

Run: `python -m py_compile backend/database.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add backend/database.py
git commit -m "feat: add player_history table for autocomplete"
```

---

## Task 4: Add Player History API Endpoint

**Files:**
- Modify: `backend/main.py` (after line 123, after get_organizer_games)

**Step 1: Add GET endpoint for player history**

Insert after the `get_organizer_games` function:

```python
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
```

**Step 2: Verify syntax**

Run: `python -m py_compile backend/main.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add player history endpoint for autocomplete"
```

---

## Task 5: Record Player Names to History

**Files:**
- Modify: `backend/main.py:270-289` (add_player function)

**Step 1: Update add_player to record history**

Replace the `add_player` function:

```python
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
```

**Step 2: Verify syntax**

Run: `python -m py_compile backend/main.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: record player names to history on registration"
```

---

## Task 6: Add Organizer Auth to Player Endpoints

**Files:**
- Modify: `backend/main.py:301-322` (update_player function)
- Modify: `backend/main.py:325-332` (delete_player function)

**Step 1: Update update_player with organizer auth**

Replace the `update_player` function:

```python
@app.put("/api/games/{game_id}/players/{player_id}", response_model=PlayerResponse)
def update_player(game_id: str, player_id: int, player: PlayerCreate, x_organizer_token: Optional[str] = Header(None)):
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify game exists and check organizer auth
        cursor.execute("SELECT organizer_id FROM games WHERE id = %s", (game_id,))
        game = cursor.fetchone()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        is_organizer = x_organizer_token and game["organizer_id"] == x_organizer_token
        if not is_organizer:
            raise HTTPException(status_code=403, detail="Only the organizer can edit players")

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
```

**Step 2: Update delete_player with organizer auth**

Replace the `delete_player` function:

```python
@app.delete("/api/games/{game_id}/players/{player_id}")
def delete_player(game_id: str, player_id: int, x_organizer_token: Optional[str] = Header(None)):
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify game exists and check organizer auth
        cursor.execute("SELECT organizer_id FROM games WHERE id = %s", (game_id,))
        game = cursor.fetchone()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        is_organizer = x_organizer_token and game["organizer_id"] == x_organizer_token
        if not is_organizer:
            raise HTTPException(status_code=403, detail="Only the organizer can delete players")

        cursor.execute("DELETE FROM players WHERE id = %s AND game_id = %s", (player_id, game_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Player not found")
        return {"message": "Player deleted"}
```

**Step 3: Verify syntax**

Run: `python -m py_compile backend/main.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: add organizer auth to player edit/delete endpoints"
```

---

## Task 7: Add Organizer Availability Edit Endpoint

**Files:**
- Modify: `backend/main.py` (after delete_player, around line 350)

**Step 1: Add PUT endpoint for organizer to edit player availability**

Insert after `delete_player`:

```python
@app.put("/api/games/{game_id}/players/{player_id}/availability")
def update_player_availability(
    game_id: str,
    player_id: int,
    availability: AvailabilityBulkCreate,
    x_organizer_token: Optional[str] = Header(None)
):
    """Organizer can update a player's availability."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT organizer_id FROM games WHERE id = %s", (game_id,))
        game = cursor.fetchone()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        is_organizer = x_organizer_token and game["organizer_id"] == x_organizer_token
        if not is_organizer:
            raise HTTPException(status_code=403, detail="Only the organizer can edit player availability")

        cursor.execute("SELECT id FROM players WHERE id = %s AND game_id = %s", (player_id, game_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        for time_slot, status in availability.slots.items():
            cursor.execute("""
                INSERT INTO availability (game_id, player_id, day, time_slot, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(game_id, player_id, day, time_slot)
                DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
            """, (game_id, player_id, availability.day, time_slot, status))

        return {"message": "Availability updated"}
```

**Step 2: Verify syntax**

Run: `python -m py_compile backend/main.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add endpoint for organizer to edit player availability"
```

---

## Task 8: Update Game Creation UI - Day Selection

**Files:**
- Modify: `static/landing.html:1014-1033`

**Step 1: Replace Saturday/Sunday checkboxes with 7-day radio buttons**

Replace the "Select Days" section:

```html
        <!-- Day Selection (Radio Buttons) -->
        <div class="px-4 py-4">
            <p class="text-[#111418] dark:text-white text-base font-medium leading-normal pb-3">Day of the Week</p>
            <div class="grid grid-cols-4 gap-2">
                <label class="cursor-pointer">
                    <input type="radio" name="day-of-week" value="sunday" class="peer sr-only" />
                    <div class="flex items-center justify-center h-10 rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#617589] peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:text-primary font-semibold text-sm transition-all">
                        Sun
                    </div>
                </label>
                <label class="cursor-pointer">
                    <input type="radio" name="day-of-week" value="monday" class="peer sr-only" />
                    <div class="flex items-center justify-center h-10 rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#617589] peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:text-primary font-semibold text-sm transition-all">
                        Mon
                    </div>
                </label>
                <label class="cursor-pointer">
                    <input type="radio" name="day-of-week" value="tuesday" class="peer sr-only" />
                    <div class="flex items-center justify-center h-10 rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#617589] peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:text-primary font-semibold text-sm transition-all">
                        Tue
                    </div>
                </label>
                <label class="cursor-pointer">
                    <input type="radio" name="day-of-week" value="wednesday" class="peer sr-only" />
                    <div class="flex items-center justify-center h-10 rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#617589] peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:text-primary font-semibold text-sm transition-all">
                        Wed
                    </div>
                </label>
                <label class="cursor-pointer">
                    <input type="radio" name="day-of-week" value="thursday" class="peer sr-only" />
                    <div class="flex items-center justify-center h-10 rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#617589] peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:text-primary font-semibold text-sm transition-all">
                        Thu
                    </div>
                </label>
                <label class="cursor-pointer">
                    <input type="radio" name="day-of-week" value="friday" class="peer sr-only" />
                    <div class="flex items-center justify-center h-10 rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#617589] peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:text-primary font-semibold text-sm transition-all">
                        Fri
                    </div>
                </label>
                <label class="cursor-pointer">
                    <input type="radio" name="day-of-week" value="saturday" class="peer sr-only" />
                    <div class="flex items-center justify-center h-10 rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#617589] peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:text-primary font-semibold text-sm transition-all">
                        Sat
                    </div>
                </label>
            </div>
        </div>
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: replace day checkboxes with 7-day radio buttons"
```

---

## Task 9: Update createGame JavaScript Function

**Files:**
- Modify: `static/landing.html:219-275` (createGame function)

**Step 1: Update createGame to use radio button selection**

Replace the `createGame` function:

```javascript
        async function createGame() {
            const title = document.getElementById('game-title').value || 'Volleyball Game';
            const venueId = document.getElementById('venue-select').value;

            const venueObj = window.appConfig?.venues?.find(v => v.id === venueId);
            const venueName = venueObj ? venueObj.name : venueId;
            const minPlayers = venueObj?.min_players || 4;
            const maxPlayers = venueObj?.max_players || 12;

            // Get selected day from radio buttons
            const selectedDayRadio = document.querySelector('input[name="day-of-week"]:checked');
            if (!selectedDayRadio) {
                showError('Please select a day of the week');
                return;
            }
            const selectedDay = selectedDayRadio.value;

            const today = new Date();
            const dayOfWeek = today.getDay();
            const dayMap = { sunday: 0, monday: 1, tuesday: 2, wednesday: 3, thursday: 4, friday: 5, saturday: 6 };
            const targetDayNum = dayMap[selectedDay];
            const daysUntilTarget = (targetDayNum - dayOfWeek + 7) % 7 || 7;
            const gameDate = new Date(today);
            gameDate.setDate(today.getDate() + daysUntilTarget);
            const gameDateStr = gameDate.toISOString().split('T')[0];

            try {
                const organizerToken = await ensureOrganizer('Organizer');

                const res = await fetch(`${API_BASE}/games`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Organizer-Token': organizerToken
                    },
                    body: JSON.stringify({
                        title: title,
                        venue: venueName,
                        game_date: gameDateStr,
                        min_players: minPlayers,
                        max_players: maxPlayers,
                        selected_days: [selectedDay]
                    })
                });
                currentGame = await res.json();
                localStorage.setItem('currentGameId', currentGame.id);
                setAsHost(currentGame.id);
                addToGameHistory(currentGame.id, title, venueName, gameDateStr, true);
                displayGame();
                renderGameHistory();
                loadRecentGames();
                showShareLink();
            } catch (e) {
                console.error('Error creating game:', e);
                showError('Failed to create game');
            }
        }
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: update createGame to use single day radio selection"
```

---

## Task 10: Update displayGame for Single Day

**Files:**
- Modify: `static/landing.html:322-374` (displayGame function)

**Step 1: Update displayGame to handle single day selection**

Replace the day-related section in `displayGame`:

```javascript
        function displayGame() {
            if (!currentGame) return;

            const titleInput = document.getElementById('game-title');
            titleInput.value = currentGame.title || '';

            const isHost = isHostOfGame(currentGame.id);
            if (isHost) {
                titleInput.disabled = false;
                titleInput.classList.remove('bg-gray-100', 'dark:bg-gray-800', 'cursor-not-allowed', 'opacity-70');
            } else {
                titleInput.disabled = true;
                titleInput.classList.add('bg-gray-100', 'dark:bg-gray-800', 'cursor-not-allowed', 'opacity-70');
            }

            const venueSelect = document.getElementById('venue-select');
            if (window.appConfig?.venues) {
                const venueObj = window.appConfig.venues.find(v => v.name === currentGame.venue);
                if (venueObj) {
                    venueSelect.value = venueObj.id;
                }
            }
            updateVenueInfo();

            // Update day radio button based on game's selected_days
            const selectedDays = currentGame.selected_days || ['sunday'];
            const selectedDay = selectedDays[0]; // Single day
            const radioBtn = document.querySelector(`input[name="day-of-week"][value="${selectedDay}"]`);
            if (radioBtn) {
                radioBtn.checked = true;
            }

            // Hide heatmap day tabs - only one day now
            const satTab = document.getElementById('heatmap-sat-tab');
            const sunTab = document.getElementById('heatmap-sun-tab');
            if (satTab) satTab.classList.add('hidden');
            if (sunTab) sunTab.classList.add('hidden');

            // Set heatmap day to the selected day
            currentHeatmapDay = selectedDay;

            document.getElementById('create-game-btn').classList.add('hidden');
            document.getElementById('share-link-btn').classList.remove('hidden');
            document.getElementById('share-link-btn').classList.add('flex');

            updateTabNav();
        }
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: update displayGame for single day selection"
```

---

## Task 11: Update saveGameSettings

**Files:**
- Modify: `static/landing.html:277-320` (saveGameSettings function)

**Step 1: Update saveGameSettings to use radio button**

Replace the `saveGameSettings` function:

```javascript
        async function saveGameSettings() {
            if (!currentGame || !isHostOfGame(currentGame.id)) return;

            const title = document.getElementById('game-title').value || 'Volleyball Game';
            const venueId = document.getElementById('venue-select').value;
            const venueObj = window.appConfig?.venues?.find(v => v.id === venueId);
            const venueName = venueObj ? venueObj.name : venueId;
            const minPlayers = venueObj?.min_players || 4;
            const maxPlayers = venueObj?.max_players || 12;

            const selectedDayRadio = document.querySelector('input[name="day-of-week"]:checked');
            if (!selectedDayRadio) {
                showError('Please select a day of the week');
                return;
            }
            const selectedDay = selectedDayRadio.value;

            try {
                const res = await fetch(`${API_BASE}/games/${currentGame.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        ...getAuthHeaders()
                    },
                    body: JSON.stringify({
                        title: title,
                        venue: venueName,
                        game_date: currentGame.game_date,
                        min_players: minPlayers,
                        max_players: maxPlayers,
                        selected_days: [selectedDay]
                    })
                });
                currentGame = await res.json();
                showToast('Saved');
                displayGame();
            } catch (e) {
                console.error('Error saving game:', e);
                showError('Failed to save changes');
            }
        }
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: update saveGameSettings for single day radio"
```

---

## Task 12: Update Event Listeners for Day Selection

**Files:**
- Modify: `static/landing.html:929-937` (DOMContentLoaded event listeners)

**Step 1: Replace checkbox listeners with radio listener**

Replace the auto-save event listeners:

```javascript
        document.addEventListener('DOMContentLoaded', () => {
            loadConfig();
            init();

            // Auto-save when host changes settings
            document.querySelectorAll('input[name="day-of-week"]').forEach(radio => {
                radio.addEventListener('change', saveGameSettings);
            });
            document.getElementById('game-title').addEventListener('blur', saveGameSettings);
            document.getElementById('venue-select').addEventListener('change', saveGameSettings);
        });
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: update event listeners for day radio buttons"
```

---

## Task 13: Add Heatmap Tooltip CSS

**Files:**
- Modify: `static/landing.html:55-63` (add after existing styles)

**Step 1: Add tooltip CSS styles**

Insert after the `@keyframes toast-fade-in` rule:

```css
        /* Heatmap tooltip */
        .heatmap-slot {
            position: relative;
        }
        .heatmap-slot .tooltip {
            visibility: hidden;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #1f2937;
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            white-space: nowrap;
            z-index: 100;
            margin-bottom: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .heatmap-slot .tooltip::after {
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-top-color: #1f2937;
        }
        .heatmap-slot:hover .tooltip {
            visibility: visible;
        }
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: add CSS styles for heatmap tooltip"
```

---

## Task 14: Update Heatmap Rendering with Tooltip

**Files:**
- Modify: `static/landing.html:444-558` (renderHeatmap function)

**Step 1: Update renderHeatmap to include tooltip**

Find the HTML generation section (around line 544) and update the slot rendering to include tooltip:

Replace this line:
```javascript
                             title="${playerNames}">
```

With tooltip div structure:

```javascript
        function renderHeatmap(heatmapData, totalPlayers) {
            const container = document.getElementById('heatmap-slots');
            if (!container) return;

            const minPlayers = currentGame?.min_players || 4;
            const dayData = heatmapData.find(d => d.day === currentHeatmapDay);

            const slotLookup = {};
            if (dayData) {
                dayData.slots.forEach(s => {
                    slotLookup[s.time_slot] = s;
                });
            }

            let bestSlot = null;
            let bestCount = 0;
            if (dayData) {
                dayData.slots.forEach(slot => {
                    if (slot.available_count > bestCount) {
                        bestCount = slot.available_count;
                        bestSlot = slot;
                    }
                });
            }

            let html = '';
            timeSlots.forEach((slot, idx) => {
                const hour = parseInt(slot.split(':')[0]);
                const displayTime = formatTime(hour);

                const slotData = slotLookup[slot] || { available_count: 0, total_count: 0, available_players: [] };
                const availCount = slotData.available_count;

                const progressRatio = minPlayers > 0 ? availCount / minPlayers : 0;
                const isBestSlot = bestSlot && bestSlot.time_slot === slot && bestCount > 0;
                const meetsRequirement = availCount >= minPlayers;

                let barColor, borderColor, textColor;

                if (meetsRequirement) {
                    barColor = isBestSlot ? 'bg-emerald-500' : 'bg-emerald-400';
                    borderColor = isBestSlot ? 'border-yellow-400' : 'border-emerald-600';
                    textColor = 'text-white';
                } else if (progressRatio >= 0.75) {
                    barColor = 'bg-blue-500';
                    borderColor = 'border-blue-600';
                    textColor = 'text-white';
                } else if (progressRatio >= 0.5) {
                    barColor = 'bg-blue-400';
                    borderColor = 'border-blue-500';
                    textColor = 'text-white';
                } else if (progressRatio >= 0.25) {
                    barColor = 'bg-blue-300';
                    borderColor = 'border-blue-400';
                    textColor = 'text-blue-800';
                } else if (progressRatio > 0) {
                    barColor = 'bg-blue-200';
                    borderColor = 'border-blue-300';
                    textColor = 'text-blue-700';
                } else {
                    barColor = 'bg-slate-100 dark:bg-slate-800';
                    borderColor = 'border-slate-200 dark:border-slate-700';
                    textColor = 'text-slate-400';
                }

                if (isBestSlot && bestCount > 0) {
                    borderColor = 'border-yellow-400';
                }

                const playerNames = slotData.available_players || [];
                const playerList = playerNames.length > 0 ? playerNames.join(', ') : 'No one available';
                const rowBg = isBestSlot ? 'bg-emerald-50/50 dark:bg-emerald-900/10' : '';
                const timeStyle = isBestSlot
                    ? 'font-bold text-emerald-600 dark:text-emerald-400'
                    : 'font-medium text-slate-600 dark:text-slate-400';

                const statusIcon = meetsRequirement
                    ? '<span class="material-symbols-outlined text-xs text-white ml-1">check_circle</span>'
                    : '';

                html += `
                <div class="grid grid-cols-12 items-center ${rowBg} ${idx < timeSlots.length - 1 ? 'border-b border-slate-100 dark:border-slate-800' : ''}">
                    <div class="col-span-3 p-3 text-sm ${timeStyle}">${displayTime}</div>
                    <div class="col-span-9 p-2 pr-4">
                        <div class="heatmap-slot w-full h-9 rounded-lg ${barColor} flex items-center justify-between px-3 border-l-4 ${borderColor} ${isBestSlot ? 'shadow-md ring-2 ring-yellow-400/30' : ''} cursor-pointer">
                            <span class="text-xs font-bold ${textColor}">${availCount}/${minPlayers}${statusIcon}</span>
                            <span class="text-[10px] ${textColor} opacity-75 truncate ml-2 max-w-[120px]">${availCount > 0 ? playerList : ''}</span>
                            <div class="tooltip">${availCount} available: ${playerList}</div>
                        </div>
                    </div>
                </div>`;
            });

            container.innerHTML = html;

            // Update suggested time banner (unchanged)
            const suggestedEl = document.getElementById('suggested-time');
            const suggestedTimeDisplay = document.getElementById('suggested-time-display');
            const playerCountEl = document.getElementById('suggested-player-count');
            const bannerEl = document.querySelector('#heatmap-section .bg-gradient-to-br');

            if (bestSlot && bestCount > 0) {
                const displayTime = formatTime(parseInt(bestSlot.time_slot.split(':')[0]));
                const meetsMin = bestCount >= minPlayers;

                if (suggestedTimeDisplay) suggestedTimeDisplay.textContent = displayTime;
                if (playerCountEl) {
                    playerCountEl.textContent = meetsMin
                        ? `${bestCount} players ready - Let's play!`
                        : `${bestCount}/${minPlayers} players (need ${minPlayers - bestCount} more)`;
                }
                if (suggestedEl) {
                    const dayLabel = currentHeatmapDay.charAt(0).toUpperCase() + currentHeatmapDay.slice(1);
                    suggestedEl.textContent = `${dayLabel} @ ${displayTime} — ${bestCount} players`;
                }

                if (bannerEl) {
                    if (meetsMin) {
                        bannerEl.className = 'bg-gradient-to-br from-emerald-500 to-emerald-700 p-5 rounded-2xl shadow-lg border-2 border-yellow-400/30 relative overflow-hidden';
                    } else {
                        bannerEl.className = 'bg-gradient-to-br from-primary to-blue-700 p-5 rounded-2xl shadow-lg border-2 border-yellow-400/30 relative overflow-hidden';
                    }
                }
            } else {
                if (suggestedTimeDisplay) suggestedTimeDisplay.textContent = '--:--';
                if (playerCountEl) playerCountEl.textContent = 'Waiting for responses...';
                if (suggestedEl) suggestedEl.textContent = 'Waiting for player responses...';
            }
        }
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: add tooltip to heatmap showing all available players"
```

---

## Task 15: Update Player Availability Page - Day Filtering

**Files:**
- Modify: `static/playeravail.html:206-256` (displayGame function)

**Step 1: Update displayGame to show only selected day**

Replace the `displayGame` function:

```javascript
        function displayGame() {
            if (!currentGame) return;
            const gameDate = parseLocalDate(currentGame.game_date);

            // Get selected day from game (now single day)
            const selectedDays = currentGame.selected_days || ['sunday'];
            const selectedDay = selectedDays[0];

            // Capitalize day name for display
            const dayLabel = selectedDay.charAt(0).toUpperCase() + selectedDay.slice(1);
            const dateStr = gameDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

            document.getElementById('game-title').textContent = currentGame.title || 'Volleyball Game';
            document.getElementById('game-venue').textContent = `${currentGame.venue} · ${dateStr}`;

            // Hide both day sections initially
            const satSection = document.getElementById('saturday-section');
            const sunSection = document.getElementById('sunday-section');
            if (satSection) satSection.classList.add('hidden');
            if (sunSection) sunSection.classList.add('hidden');

            // Show only the selected day section (for backward compat with sat/sun)
            if (selectedDay === 'saturday' && satSection) {
                satSection.classList.remove('hidden');
            } else if (selectedDay === 'sunday' && sunSection) {
                sunSection.classList.remove('hidden');
            }

            // Hide day tabs in time slots - only one day
            const satTab = document.getElementById('sat-tab');
            const sunTab = document.getElementById('sun-tab');
            if (satTab) satTab.classList.add('hidden');
            if (sunTab) sunTab.classList.add('hidden');

            // Set current day to selected day
            currentDay = selectedDay;

            updateTabNav();
        }
```

**Step 2: Commit**

```bash
git add static/playeravail.html
git commit -m "feat: filter player availability to show only selected day"
```

---

## Task 16: Add Manage Players Tab HTML

**Files:**
- Modify: `static/landing.html` (after heatmap section, around line 1122)

**Step 1: Add Manage Players section**

Insert after the heatmap section closing div:

```html
        <!-- Manage Players Section (Organizer Only) -->
        <div id="manage-players-section" class="hidden pt-6">
            <div class="flex items-center justify-between px-4 pb-3">
                <h3 class="text-[#111418] dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">Manage Players</h3>
                <span class="text-xs text-gray-500 dark:text-gray-400">Organizer only</span>
            </div>

            <!-- Add Player Input -->
            <div class="px-4 pb-4">
                <div class="flex gap-2">
                    <div class="relative flex-1">
                        <input type="text" id="add-player-input" placeholder="Search or type name..."
                            class="w-full h-12 px-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-[#111418] dark:text-white focus:outline-0 focus:ring-2 focus:ring-primary/50"
                            autocomplete="off" />
                        <div id="player-suggestions" class="hidden absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 max-h-48 overflow-y-auto">
                            <!-- Suggestions populated dynamically -->
                        </div>
                    </div>
                    <button onclick="addPlayerFromInput()"
                        class="h-12 px-4 bg-primary text-white rounded-xl font-bold flex items-center gap-2 hover:bg-primary/90 transition-colors">
                        <span class="material-symbols-outlined text-sm">person_add</span>
                        Add
                    </button>
                </div>
            </div>

            <!-- Player List -->
            <div id="manage-players-list" class="px-4 space-y-2">
                <!-- Players populated dynamically -->
            </div>
        </div>
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: add Manage Players section HTML"
```

---

## Task 17: Add Player Management JavaScript

**Files:**
- Modify: `static/landing.html` (add before closing script tag, around line 979)

**Step 1: Add player management functions**

Insert before the closing `</script>` tag:

```javascript
        // ============ PLAYER MANAGEMENT ============

        let playerSuggestions = [];

        async function loadPlayerSuggestions(query = '') {
            const token = getOrganizerToken();
            if (!token) return;

            try {
                const res = await fetch(`${API_BASE}/organizers/${token}/player-history?q=${encodeURIComponent(query)}`);
                if (res.ok) {
                    playerSuggestions = await res.json();
                }
            } catch (e) {
                console.error('Error loading suggestions:', e);
            }
        }

        function showPlayerSuggestions() {
            const container = document.getElementById('player-suggestions');
            const input = document.getElementById('add-player-input');
            const query = input.value.toLowerCase();

            const filtered = playerSuggestions.filter(name =>
                name.toLowerCase().includes(query)
            ).slice(0, 8);

            if (filtered.length === 0 || !query) {
                container.classList.add('hidden');
                return;
            }

            container.innerHTML = filtered.map(name => `
                <div onclick="selectPlayerSuggestion('${name.replace(/'/g, "\\'")}')"
                     class="px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer text-sm">
                    ${name}
                </div>
            `).join('');
            container.classList.remove('hidden');
        }

        function selectPlayerSuggestion(name) {
            document.getElementById('add-player-input').value = name;
            document.getElementById('player-suggestions').classList.add('hidden');
        }

        async function addPlayerFromInput() {
            if (!currentGame) return;

            const input = document.getElementById('add-player-input');
            const name = input.value.trim();
            if (!name) {
                showError('Please enter a player name');
                return;
            }

            try {
                await apiCall(`${API_BASE}/games/${currentGame.id}/players`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ name })
                });
                input.value = '';
                showToast(`Added ${name}`);
                await loadPlayers();
                await loadPlayerSuggestions();
            } catch (e) {
                console.error('Error adding player:', e);
            }
        }

        async function editPlayer(playerId, currentName) {
            const newName = prompt('Edit player name:', currentName);
            if (!newName || newName === currentName) return;

            try {
                await apiCall(`${API_BASE}/games/${currentGame.id}/players/${playerId}`, {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ name: newName.trim() })
                });
                showToast('Player updated');
                await loadPlayers();
            } catch (e) {
                console.error('Error editing player:', e);
            }
        }

        async function deletePlayer(playerId, playerName) {
            if (!confirm(`Remove ${playerName} from this game?`)) return;

            try {
                await apiCall(`${API_BASE}/games/${currentGame.id}/players/${playerId}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });
                showToast(`Removed ${playerName}`);
                await loadPlayers();
                await loadHeatmap();
            } catch (e) {
                console.error('Error deleting player:', e);
            }
        }

        function renderManagePlayersList(players, availability) {
            const container = document.getElementById('manage-players-list');
            if (!container) return;

            // Group availability by player
            const playerAvail = {};
            availability.forEach(a => {
                if (!playerAvail[a.player_id]) playerAvail[a.player_id] = [];
                playerAvail[a.player_id].push(a);
            });

            container.innerHTML = players.map(player => {
                const avail = playerAvail[player.id] || [];
                const hasSubmitted = avail.length > 0;
                const statusIcon = hasSubmitted ? 'check_circle' : 'schedule';
                const statusColor = hasSubmitted ? 'text-green-500' : 'text-yellow-500';
                const statusText = hasSubmitted ? 'Submitted' : 'Pending';

                return `
                <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                    <div class="flex items-center gap-3">
                        <span class="material-symbols-outlined ${statusColor}">${statusIcon}</span>
                        <div>
                            <p class="font-medium text-sm text-[#111418] dark:text-white">${player.name}</p>
                            <p class="text-xs text-gray-500">${statusText}</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-1">
                        <button onclick="editPlayer(${player.id}, '${player.name.replace(/'/g, "\\'")}')"
                            class="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 transition-colors"
                            title="Edit">
                            <span class="material-symbols-outlined text-lg">edit</span>
                        </button>
                        <button onclick="deletePlayer(${player.id}, '${player.name.replace(/'/g, "\\'")}')"
                            class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-500 hover:text-red-500 transition-colors"
                            title="Delete">
                            <span class="material-symbols-outlined text-lg">delete</span>
                        </button>
                    </div>
                </div>`;
            }).join('');
        }

        // Setup autocomplete input listeners
        document.addEventListener('DOMContentLoaded', () => {
            const input = document.getElementById('add-player-input');
            if (input) {
                input.addEventListener('input', () => {
                    loadPlayerSuggestions(input.value);
                    showPlayerSuggestions();
                });
                input.addEventListener('focus', async () => {
                    await loadPlayerSuggestions(input.value);
                    showPlayerSuggestions();
                });
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        addPlayerFromInput();
                    }
                });
            }

            // Close suggestions on click outside
            document.addEventListener('click', (e) => {
                if (!e.target.closest('#add-player-input') && !e.target.closest('#player-suggestions')) {
                    document.getElementById('player-suggestions')?.classList.add('hidden');
                }
            });
        });
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: add player management JavaScript functions"
```

---

## Task 18: Show Manage Players for Organizers

**Files:**
- Modify: `static/landing.html:399-419` (loadPlayers function)

**Step 1: Update loadPlayers to show management section**

Replace the `loadPlayers` function:

```javascript
        async function loadPlayers() {
            if (!currentGame) return;
            try {
                const [playersRes, availRes] = await Promise.all([
                    fetch(`${API_BASE}/games/${currentGame.id}/players`),
                    fetch(`${API_BASE}/games/${currentGame.id}/availability`)
                ]);
                const players = await playersRes.json();
                const availability = await availRes.json();

                renderRoster(players, availability);

                // Show management section for organizers
                const isHost = isHostOfGame(currentGame.id);
                const manageSection = document.getElementById('manage-players-section');
                if (manageSection) {
                    if (isHost && players.length > 0) {
                        manageSection.classList.remove('hidden');
                        renderManagePlayersList(players, availability);
                    } else {
                        manageSection.classList.add('hidden');
                    }
                }

                // Show and load heatmap if we have players
                if (players.length > 0) {
                    document.getElementById('heatmap-section')?.classList.remove('hidden');
                    await loadHeatmap();
                }
            } catch (e) {
                console.error('Error loading players:', e);
            }
        }
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat: show Manage Players section for game organizers"
```

---

## Task 19: Final Verification

**Step 1: Verify all Python syntax**

Run: `python -m py_compile backend/main.py backend/models.py backend/database.py backend/constants.py`
Expected: No output (success)

**Step 2: Start dev server and test manually**

Run: `cd backend && python main.py`
Expected: Server starts on localhost:8000

**Step 3: Test the following user flows**

1. Create a game with Sunday selected
2. Share link - player sees only Sunday time slots
3. Hover over heatmap slot - tooltip shows all player names
4. As organizer, view Manage Players section
5. Edit a player name
6. Delete a player
7. Add a player with autocomplete

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete UI improvements - day selection, tooltips, player management"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Expand DAYS constant to 7 days |
| 2 | Update model validators for all days |
| 3 | Add player_history table |
| 4 | Add player history API endpoint |
| 5 | Record player names to history |
| 6 | Add organizer auth to player endpoints |
| 7 | Add organizer availability edit endpoint |
| 8 | Update game creation UI with day radios |
| 9 | Update createGame JS function |
| 10 | Update displayGame for single day |
| 11 | Update saveGameSettings |
| 12 | Update event listeners |
| 13 | Add heatmap tooltip CSS |
| 14 | Update heatmap rendering with tooltip |
| 15 | Update player availability page filtering |
| 16 | Add Manage Players HTML |
| 17 | Add player management JS |
| 18 | Show Manage Players for organizers |
| 19 | Final verification |
