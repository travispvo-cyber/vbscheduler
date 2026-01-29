# Recent Games Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to browse and join recent games from the landing page without needing a direct invite link.

**Architecture:** Add `GET /api/games` endpoint that returns games from the last 14 days, sorted by date descending. Frontend displays these in a "Recent Games" section above "My Games", allowing tap-to-load.

**Tech Stack:** FastAPI backend, vanilla JS frontend, SQLite database

---

## Task 1: Add List Games API Endpoint

**Files:**
- Modify: `backend/main.py:73-95` (after create_game, before get_game)

**Step 1: Add the endpoint**

Add after `create_game()` function (around line 95):

```python
@app.get("/api/games", response_model=list[GameResponse])
def list_games(days: int = 14, limit: int = 20):
    """List recent games from the last N days."""
    from datetime import datetime, timedelta
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM games
            WHERE game_date >= ?
            ORDER BY game_date DESC, created_at DESC
            LIMIT ?
        """, (cutoff_date, limit))
        rows = cursor.fetchall()

        results = []
        for row in rows:
            data = dict(row)
            data.pop('organizer_pin', None)
            if data.get('selected_days'):
                data['selected_days'] = json.loads(data['selected_days'])
            results.append(GameResponse(**data))
        return results
```

**Step 2: Test the endpoint manually**

Run: `curl http://localhost:8000/api/games`
Expected: JSON array of recent games (or empty array if none)

**Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat(api): add GET /api/games endpoint for listing recent games"
```

---

## Task 2: Add Recent Games Section HTML

**Files:**
- Modify: `static/landing.html` (HTML section, around line 997)

**Step 1: Add HTML section before "My Games"**

Find the `<!-- My Games Section -->` comment and add this BEFORE it:

```html
<!-- Recent Games Section -->
<div id="recent-games-section" class="pt-6">
    <div class="flex items-center justify-between px-4 pb-3">
        <h3 class="text-[#111418] dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">Recent Games</h3>
        <span class="text-xs text-gray-500 dark:text-gray-400">Last 14 days</span>
    </div>
    <div id="recent-games-list" class="px-4 space-y-2">
        <p class="text-center text-gray-400 py-4 text-sm">Loading...</p>
    </div>
</div>
```

**Step 2: Verify HTML renders**

Open landing.html in browser, confirm "Recent Games" section appears above "My Games".

**Step 3: Commit**

```bash
git add static/landing.html
git commit -m "feat(ui): add Recent Games section HTML to landing page"
```

---

## Task 3: Add loadRecentGames() Function

**Files:**
- Modify: `static/landing.html` (JavaScript section, around line 665)

**Step 1: Add the function**

Add after `renderGameHistory()` function:

```javascript
async function loadRecentGames() {
    const container = document.getElementById('recent-games-list');
    const section = document.getElementById('recent-games-section');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE}/games?days=14&limit=10`);
        if (!res.ok) throw new Error('Failed to load games');
        const games = await res.json();

        if (games.length === 0) {
            section?.classList.add('hidden');
            return;
        }

        section?.classList.remove('hidden');

        // Get local history to check which ones we've visited
        const history = getGameHistory();
        const visitedIds = new Set(history.map(g => g.id));

        container.innerHTML = games.map(game => {
            const isVisited = visitedIds.has(game.id);
            const isCurrentGame = currentGame?.id === game.id;
            const gameDate = new Date(game.game_date);
            const dateStr = gameDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

            return `
            <div onclick="loadGame('${game.id}')"
                 class="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all
                        ${isCurrentGame ? 'bg-primary/10 border-2 border-primary' : 'bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800'}">
                <div class="flex-1 min-w-0">
                    <p class="text-[#111418] dark:text-white text-sm font-semibold truncate">${game.title}</p>
                    <p class="text-gray-500 dark:text-gray-400 text-xs">${game.venue} · ${dateStr}</p>
                </div>
                ${isVisited ? '<span class="material-symbols-outlined text-primary text-sm">check_circle</span>' : ''}
            </div>`;
        }).join('');

    } catch (e) {
        console.error('Error loading recent games:', e);
        container.innerHTML = '<p class="text-center text-gray-400 py-4 text-sm">Could not load games</p>';
    }
}
```

**Step 2: Commit**

```bash
git add static/landing.html
git commit -m "feat(ui): add loadRecentGames() function"
```

---

## Task 4: Call loadRecentGames() on Page Load

**Files:**
- Modify: `static/landing.html` (init function, around line 173)

**Step 1: Update init() to call loadRecentGames**

Find the `init()` function and add `loadRecentGames()` call:

```javascript
async function init() {
    const urlParams = new URLSearchParams(window.location.search);
    const gameId = urlParams.get('game') || localStorage.getItem('currentGameId');

    if (gameId) {
        await loadGame(gameId);
    }
    setupEventListeners();
    renderGameHistory();
    loadRecentGames();  // Add this line
}
```

**Step 2: Also refresh after game operations**

Update `loadGame()` to refresh recent games after loading (add at end of try block):

```javascript
loadRecentGames();
```

Update `deleteGame()` to refresh recent games after deletion:

```javascript
loadRecentGames();
```

**Step 3: Test the full flow**

1. Open landing page - should see "Recent Games" with any existing games
2. Create a new game - should appear in Recent Games
3. Tap a game in Recent Games - should load it
4. Delete a game - should disappear from Recent Games

**Step 4: Commit**

```bash
git add static/landing.html
git commit -m "feat(ui): integrate loadRecentGames into page lifecycle"
```

---

## Task 5: Final Polish and Commit

**Step 1: Test edge cases**

- Empty state: No games in last 14 days → section should be hidden
- Many games: Should limit to 10 most recent
- Current game highlight: Currently loaded game should have primary border

**Step 2: Final commit with all changes**

```bash
git add -A
git commit -m "feat: add Recent Games browsing to landing page

- GET /api/games endpoint returns games from last 14 days
- Recent Games section shows discoverable games
- Tap to load any game without needing invite link
- Visited games show checkmark indicator
- Current game highlighted with primary border"
```

---

## Verification Checklist

- [ ] `GET /api/games` returns recent games sorted by date
- [ ] Recent Games section appears on landing page
- [ ] Tapping a game loads it (same as entering via invite link)
- [ ] Visited games show checkmark
- [ ] Currently loaded game has highlight border
- [ ] Empty state hides the section
- [ ] Works on mobile (responsive)
