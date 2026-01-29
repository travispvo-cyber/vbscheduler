# Web App Development Template

Use this template with `/superpowers:brainstorming` to one-shot a new web app.

---

## 1. Project Brief (Fill This Out)

```yaml
App Name: [your-app-name]
One-liner: [What does it do in one sentence?]

Core Problem:
  - [What pain point does this solve?]
  - [Who is the target user?]

Key Features (max 5):
  1. [Feature 1]
  2. [Feature 2]
  3. [Feature 3]

Tech Stack:
  Backend: FastAPI + SQLite (default) | [or specify]
  Frontend: Vanilla HTML/JS + Tailwind (default) | [or specify]
  Hosting: Render.com (default) | [or specify]

Design System:
  Style: Apple HIG (default) | Material | Custom
  Font: System fonts (default) | [or specify]
  Primary Color: #007AFF (default) | [or specify]
```

---

## 2. Data Model (Define Your Entities)

```yaml
Entities:
  - Name: [Entity1]
    Fields:
      - id: string (auto-generated)
      - [field_name]: [type] [constraints]
      - created_at: datetime
    Relationships: [belongs_to Entity2, has_many Entity3]

  - Name: [Entity2]
    Fields:
      - [...]
```

**Example (VB Scheduler):**
```yaml
Entities:
  - Name: Game
    Fields:
      - id: string (urlsafe token)
      - title: string (max 50)
      - venue: string
      - game_date: date
      - min_players: int
      - max_players: int
      - selected_days: list[string]
      - created_at: datetime

  - Name: Player
    Fields:
      - id: int (auto)
      - game_id: string (FK)
      - name: string (max 30)

  - Name: Availability
    Fields:
      - id: int (auto)
      - player_id: int (FK)
      - game_id: string (FK)
      - day: string (saturday|sunday)
      - time_slot: string (HH:MM)
      - status: string (available|unavailable)
```

---

## 3. API Endpoints (Define Your Routes)

```yaml
Endpoints:
  # CRUD for main entity
  - POST   /api/[entities]           Create
  - GET    /api/[entities]/{id}      Read
  - PUT    /api/[entities]/{id}      Update
  - DELETE /api/[entities]/{id}      Delete

  # Nested resources
  - POST   /api/[entities]/{id}/[sub]     Add sub-entity
  - GET    /api/[entities]/{id}/[sub]     List sub-entities

  # Special endpoints
  - GET    /api/config                    App configuration
  - GET    /api/health                    Health check
```

---

## 4. Pages/Views (Define Your Screens)

```yaml
Pages:
  - Name: Landing/Home
    URL: /landing.html
    Purpose: [Main entry point, create new, browse existing]
    Key Elements:
      - Hero header with app name
      - Create form
      - Recent items list
      - Bottom CTA

  - Name: Detail/Edit
    URL: /detail.html?id={id}
    Purpose: [View/edit single item]
    Key Elements:
      - Item title in header
      - Edit form or display
      - Related data
      - Action buttons
```

---

## 5. Configuration (Constants)

```yaml
Constants:
  # Dropdown options
  CATEGORIES: [list of options with id, name, metadata]

  # Time/date options
  TIME_SLOTS: [list of valid times]
  DAYS: [list of valid days]

  # Limits
  MAX_ITEMS: [number]
  TITLE_MAX_LENGTH: [number]

  # Predefined data
  PRESET_LIST: [list of preset options]
```

---

## 6. File Structure (Standard Layout)

```
your-app/
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── models.py        # Pydantic schemas
│   ├── database.py      # SQLite setup
│   ├── config.py        # Environment config
│   ├── constants.py     # App constants
│   └── requirements.txt
├── static/
│   ├── landing.html     # Main page
│   ├── detail.html      # Detail page
│   └── images/
│       └── favicon.png
├── data/                # SQLite DB (gitignored)
│   └── .gitkeep
├── docs/
│   └── plans/           # Design docs
├── .env.example
├── .gitignore
├── render.yaml          # Render deployment
├── requirements.txt     # Root requirements
└── CLAUDE.md            # Dev guide for Claude
```

---

## 7. Design Tokens (Apple HIG Default)

```javascript
// Tailwind config
colors: {
  "primary": "#007AFF",        // Apple Blue
  "background-light": "#ffffff",
  "background-dark": "#000000",
  "success-green": "#34C759",  // Apple Green
  "error-red": "#FF3B30",      // Apple Red
  "label": "#1d1d1f",          // Primary text
  "secondary-label": "#86868b" // Muted text
}

// Font stack
font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
             "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;

// Border radius
borderRadius: {
  "DEFAULT": "0.5rem",
  "lg": "0.75rem",
  "xl": "1rem",
  "full": "9999px"
}
```

---

## 8. Render Deployment (render.yaml)

```yaml
services:
  - type: web
    name: [your-app-name]
    runtime: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: DEBUG
        value: "false"
      - key: CORS_ORIGINS
        value: "*"
    disk:
      name: data
      mountPath: /opt/render/project/src/data
      sizeGB: 1
```

---

## 9. One-Shot Prompt Template

Copy this and fill in the brackets:

```
I want to build a web app called [APP_NAME].

## What it does
[ONE_SENTENCE_DESCRIPTION]

## Core features
1. [FEATURE_1]
2. [FEATURE_2]
3. [FEATURE_3]

## Data model
- [ENTITY_1]: [fields]
- [ENTITY_2]: [fields]

## Pages needed
1. [PAGE_1]: [purpose]
2. [PAGE_2]: [purpose]

## Tech preferences
- Backend: FastAPI + SQLite
- Frontend: Vanilla HTML/JS + Tailwind
- Design: Apple HIG style
- Deploy: Render.com with persistent disk

Please use /superpowers:brainstorming to refine, then implement.
```

---

## 10. Development Checklist

```
[ ] Define project brief
[ ] Run /superpowers:brainstorming to refine idea
[ ] Create file structure
[ ] Implement backend (models, database, routes)
[ ] Implement frontend (pages, JS logic)
[ ] Add constants/config
[ ] Test locally
[ ] Create render.yaml
[ ] Push to GitHub
[ ] Deploy to Render
[ ] Test production
```

---

## Quick Reference: Common Patterns

### Date Parsing (avoid timezone bugs)
```javascript
function parseLocalDate(dateStr) {
    if (!dateStr) return new Date();
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day);
}
```

### Toast Notifications
```javascript
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-24 left-1/2 -translate-x-1/2
        ${type === 'error' ? 'bg-red-600' : 'bg-gray-800'}
        text-white px-4 py-2 rounded-lg shadow-lg z-50`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), type === 'error' ? 4000 : 2000);
}
```

### LocalStorage for Client State
```javascript
// Save
localStorage.setItem(`key_${entityId}`, value);

// Load
const value = localStorage.getItem(`key_${entityId}`);

// Remove
localStorage.removeItem(`key_${entityId}`);
```

### API Call Wrapper
```javascript
async function apiCall(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Request failed');
    return data;
}
```
