# VB Scheduler v2 - Seamless UX Redesign

## Overview

Redesign VB Scheduler with Netflix/Instagram-like seamless UX. The app should feel effortless - players should be able to update availability in under 5 seconds on return visits.

## Core UX Philosophy

### Guiding Principles

1. **5-Second Rule** - Returning players update availability in under 5 seconds
2. **Remember Everything** - Device knows who you are, no re-identification
3. **Presets Over Precision** - "Anytime" / "Mornings" / "Evenings" beats manual selection
4. **Silent Persistence** - Auto-save everything, no submit buttons
5. **Color = Meaning** - Green (available), Red (unavailable), Gray (unset)

### What We're Removing

- Save/Submit buttons (auto-save instead)
- "I'm In" / "I'm Out" day-level buttons (replaced by presets + drag-to-paint)
- Name selection for returning players on same device
- Editable game title on player view (host-only)

### What We're Adding

- Tab navigation (Home | My Times)
- Drag-to-paint time selection
- Availability presets (Anytime, Mornings, Afternoons, Evenings)
- Auto-save with toast confirmation
- Host-only game editing
- Seamless returning player experience

---

## Section 1: Tab Navigation

### Design

```
┌─────────────────────────────────┐
│  🏐 VB Scheduler                │
├────────────────┬────────────────┤
│     Home       │    My Times    │
│    ━━━━━━      │                │
└────────────────┴────────────────┘
```

### Tabs

| Tab | Page | Icon | Description |
|-----|------|------|-------------|
| **Home** | landing.html | `home` | Game management, heatmap, roster |
| **My Times** | playeravail.html | `schedule` | Personal availability selection |

### Behavior

- Fixed at top below header
- Active tab: primary color underline + bold text
- Inactive tab: gray text
- Game context persists via `?game={id}` URL parameter
- Both pages share identical nav component

### Implementation

Add to both `landing.html` and `playeravail.html`:

```html
<nav class="flex border-b border-gray-200 dark:border-gray-700">
    <a href="/landing.html?game=${gameId}"
       class="flex-1 py-3 text-center font-medium ${isHome ? 'text-primary border-b-2 border-primary' : 'text-gray-500'}">
        <span class="material-symbols-outlined align-middle mr-1">home</span>
        Home
    </a>
    <a href="/playeravail.html?game=${gameId}"
       class="flex-1 py-3 text-center font-medium ${isMyTimes ? 'text-primary border-b-2 border-primary' : 'text-gray-500'}">
        <span class="material-symbols-outlined align-middle mr-1">schedule</span>
        My Times
    </a>
</nav>
```

---

## Section 2: Player Flow

### First-Time Player (via shared link)

1. **Land on page** → See game title (read-only), date, and host name
2. **Quick identity** → Single text field: "What's your name?" with roster autocomplete
3. **Time selection** → Two paths presented side-by-side:
   - **Presets**: "Anytime" | "Mornings Only" | "Afternoons Only" | "Evenings Only"
   - **Fine-tune**: Grid appears with preset already applied, drag-to-paint to adjust
4. **Done** → Toast: "Got it, [Name]!" — No submit button, auto-saves on each change
5. **Device remembers** → localStorage stores `{ gameId, playerId, playerName }`

### Returning Player (same device)

1. **Land on page** → Instant recognition: "Welcome back, [Name]!"
2. **See current selections** → Grid shows their availability pre-filled (green = available)
3. **Modify** → Drag-to-paint changes, toast confirms each save
4. **That's it** → No login, no selection, no friction

### Returning Player (different device)

1. **Land on page** → "Who are you?" with roster of existing players for this game
2. **Tap name** → "Is this you?" confirmation (prevents accidental overwrites)
3. **Continue** → Same as returning player flow above

### Drag-to-Paint Interaction

- **Mouse down on cell** → Starts paint mode, toggles that cell
- **Drag across cells** → All cells in path get same state as first toggled cell
- **Mouse up** → Ends paint, triggers auto-save
- **Touch support** → Same behavior for mobile swipe gestures
- **Visual feedback** → Cells highlight as you drag, subtle pulse on save

---

## Section 3: Host Flow

### Creating a New Game

1. **Land on landing page** → Clean form: Game name, venue dropdown, date picker
2. **Minimal required fields** → Just name and date (venue defaults to "TBD")
3. **Create** → Instant game creation, device marked as host via localStorage
4. **Share modal appears** → Copy link button + QR code for in-person sharing
5. **Device remembers** → `isHost_${gameId}: true` stored locally

### Host Dashboard (landing.html)

- **Game title** → Editable inline (pencil icon appears on hover/tap)
- **Player roster** → Shows who's signed up with their status summary
- **Heatmap** → Visual grid showing availability density
- **Best times** → Auto-highlighted slots where most players align
- **Actions** → Share link, view full availability, delete game

### Host-Only Capabilities

- Edit game title (inline edit with auto-save)
- Delete game (confirmation required)
- See organizer view of heatmap
- Access to all player availability details

### Player View vs Host View

| Element | Host | Player |
|---------|------|--------|
| Game title | Editable (pencil icon) | Read-only |
| Delete game | Yes (trash icon) | No |
| Player list | Full details | Summary only |
| Heatmap | Full access | Their own + summary |

---

## Section 4: Technical Implementation

### localStorage Schema

```javascript
// Per-game host marker
`isHost_${gameId}`: "true"

// Per-game player identity
`player_${gameId}`: "playerId"
`playerName_${gameId}`: "Travis"

// Game history (array of recent games)
`gameHistory`: [{ id, title, venue, gameDate, createdAt, isHost }]

// Current active game
`currentGameId`: "abc123"
```

### Drag-to-Paint Implementation

```javascript
let isPainting = false;
let paintState = null; // 'available' or 'unavailable' or null (toggle off)

function initDragToPaint() {
    const grid = document.getElementById('time-slots-container');

    grid.addEventListener('pointerdown', (e) => {
        const btn = e.target.closest('.slot-btn');
        if (!btn) return;

        isPainting = true;
        paintState = toggleSlot(btn); // Returns new state
        btn.setPointerCapture(e.pointerId);
    });

    grid.addEventListener('pointermove', (e) => {
        if (!isPainting) return;
        const el = document.elementFromPoint(e.clientX, e.clientY);
        const btn = el?.closest('.slot-btn');
        if (btn) {
            setSlotState(btn, paintState);
        }
    });

    grid.addEventListener('pointerup', () => {
        if (isPainting) {
            isPainting = false;
            queueSave();
        }
    });
}
```

### Auto-Save with Debounce

```javascript
let saveTimeout;

function queueSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(async () => {
        await saveAvailability();
        showToast('Saved');
    }, 500);
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-20 left-1/2 -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm';
    toast.innerHTML = `<span class="material-symbols-outlined text-green-400 text-sm align-middle mr-1">check</span>${message}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}
```

### Preset Buttons

```javascript
const PRESETS = {
    anytime: { slots: 'all', label: 'Anytime' },
    morning: { slots: ['08:00', '09:00', '10:00', '11:00'], label: 'Mornings' },
    afternoon: { slots: ['12:00', '13:00', '14:00', '15:00', '16:00'], label: 'Afternoons' },
    evening: { slots: ['17:00', '18:00', '19:00', '20:00', '21:00'], label: 'Evenings' }
};

function applyPreset(presetKey) {
    const preset = PRESETS[presetKey];
    const allSlots = document.querySelectorAll('.slot-btn');

    allSlots.forEach(btn => {
        const slot = btn.dataset.slot;
        const shouldBeAvailable = preset.slots === 'all' || preset.slots.includes(slot);
        setSlotState(btn, shouldBeAvailable ? 'available' : 'unavailable');
    });

    queueSave();
}
```

---

## Section 5: Files to Modify

| File | Changes |
|------|---------|
| `static/landing.html` | Add tab nav, host detection, inline title edit |
| `static/playeravail.html` | Add tab nav, drag-to-paint, presets, auto-save, read-only title |
| `backend/main.py` | No changes needed (existing API sufficient) |

### No Backend Changes Required

The existing API supports all v2 features:
- `POST /api/games/{id}/availability` - Upsert handles all save patterns
- `GET /api/games/{id}` - Returns game details
- `GET /api/games/{id}/players` - Returns player list for roster
- `PUT /api/games/{id}` - Updates game (for host title edit)

---

## Implementation Order

1. **Tab Navigation** - Add to both pages, wire up navigation
2. **Host Detection** - Mark device as host on game creation, check on load
3. **Drag-to-Paint** - Implement pointer events for time grid
4. **Presets** - Add preset buttons above time grid
5. **Auto-Save** - Replace manual save with debounced auto-save
6. **Toast Feedback** - Add subtle confirmation toasts
7. **Read-Only Title** - Hide edit controls for non-hosts on playeravail
8. **Polish** - Returning player greeting, visual refinements

---

## Success Criteria

- [ ] Returning player can update availability in <5 seconds
- [ ] No "Save" or "Submit" buttons anywhere
- [ ] Host can edit game title, players cannot
- [ ] Drag-to-paint works on desktop and mobile
- [ ] Presets apply instantly with visual feedback
- [ ] Tab navigation works seamlessly between pages
- [ ] Toast confirms every save action
