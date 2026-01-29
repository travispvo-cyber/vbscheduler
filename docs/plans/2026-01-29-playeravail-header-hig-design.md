# playeravail.html Header Redesign - Apple HIG

**Date:** 2026-01-29
**Status:** Implemented

## Problem

The `playeravail.html` page had a header displaying "Set Game Details" with a back button that didn't make sense on clean site visits (no game context).

## Solution

Replace the old header with an Apple Human Interface Guidelines (HIG) compliant design that:
- Shows only the **Game Title** (centered)
- Shows the **venue and date** as secondary information
- Uses Apple's system fonts and neutral color palette
- Follows HIG principles: Clarity, Deference, and Depth

## Changes Made

### 1. Typography
- Removed Google Fonts (Lexend)
- Added Apple system font stack: `-apple-system, BlinkMacSystemFont, SF Pro Display, SF Pro Text, Helvetica Neue, Arial`
- Added font smoothing for crisp rendering

### 2. Color Palette (Apple HIG)
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#007AFF` | Apple Blue for interactive elements |
| `label` | `#1d1d1f` | Primary text color |
| `secondary-label` | `#86868b` | Secondary/muted text |
| `success-green` | `#34C759` | Apple Green |
| `error-red` | `#FF3B30` | Apple Red |

### 3. Header Structure
**Before:**
```
[<] Set Game Details    [Date Badge]
```

**After:**
```
        Game Title
    Venue · Date Info
─────────────────────────
 [Home]    [My Times*]
```

### 4. Key HIG Principles Applied
- **Clarity**: Single, clear title without competing elements
- **Deference**: Neutral backdrop lets content be the focus
- **Depth**: Visual hierarchy through typography weight only
- **Negative Space**: Generous padding (py-6) for breathing room

## Files Modified
- `static/playeravail.html`

## Testing
- Verify on clean site visit (no game context) - should show "Loading..."
- Verify with game loaded - should display actual game title
- Verify tab navigation still works
- Verify responsive on mobile viewports
