# Frontend Context

**Purpose**: Frontend-specific context for GitHub Copilot agents  
**Parent**: See root `AGENTS.md` for project-wide context  
**Last Updated**: January 6, 2026

---

## 🔴 Check Frontend Facts First

### API Contracts (HIGH RISK)

**Problem**: Frontend sends card names instead of IDs to API

**Solution**: All API requests use card IDs, NEVER card names

```typescript
// ✅ CORRECT
interface PlayCardRequest {
  player_id: string;
  card_id: string;        // NOT card_name
  target_ids?: string[];  // NOT target_card_names
}

// ❌ WRONG
interface PlayCardRequest {
  player_id: string;
  card_name: string;      // Backend will reject this
}
```

### Spacing Values (CAUSES INCONSISTENCY)

**Problem**: Agents hardcode spacing values instead of using design tokens

**Solution**: ALWAYS use CSS custom properties

| ✅ CORRECT | ❌ WRONG |
|------------|----------|
| `var(--spacing-component-md)` | `16px` |
| `var(--spacing-component-sm)` | `12px` |
| `className="panel-padding"` | `style={{ padding: '16px' }}` |

---

## Design System

### Spacing Tokens

Defined in `frontend/src/index.css`:

```css
@theme {
  --spacing-component-xs: 8px;   /* Tight spacing within components */
  --spacing-component-sm: 12px;  /* Standard component padding */
  --spacing-component-md: 16px;  /* Default content spacing */
  --spacing-component-lg: 24px;  /* Section separation */
  --spacing-component-xl: 32px;  /* Major layout spacing */
}
```

### Utility Classes

```css
.panel-padding   /* padding: var(--spacing-component-md) */
.modal-padding   /* padding: var(--spacing-component-lg) */
.card-padding    /* padding: var(--spacing-component-sm) */
.content-spacing /* gap: var(--spacing-component-md) */
```

### Usage Examples

```tsx
// ✅ CORRECT - design tokens
<div style={{ padding: 'var(--spacing-component-md)' }}>
  <div style={{ gap: 'var(--spacing-component-sm)' }}>
    Content
  </div>
</div>

// ✅ CORRECT - utility classes
<div className="panel-padding">
  <div className="content-spacing">
    Content
  </div>
</div>

// ❌ WRONG - hardcoded values
<div style={{ padding: '16px' }}>
<div style={{ gap: '12px' }}>
```

**Exceptions**: NONE. All spacing uses design tokens.

---

## Typography

**Single font family**: Lato (loaded via Google Fonts in `index.html`)

**Two weights only**:
- 400 (normal) - Body text
- 700 (bold) - Headings, titles, card names, emphasis

```tsx
// ✅ CORRECT
<h1 className="text-3xl font-bold">Game Title</h1>
<p className="text-base font-normal">Body text</p>

// ❌ WRONG - never add custom fonts
<div style={{ fontFamily: "'Bangers', sans-serif" }}>
```

**Exceptions**: NONE. Visual hierarchy from weight and size, not font family.

---

## React Patterns

### Component Structure

```typescript
interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
  isSelected?: boolean;
}

export const CardDisplay: React.FC<CardDisplayProps> = ({
  card,
  onClick,
  isSelected = false
}) => {
  return (...);
};
```

### React Query for API State

```typescript
const { data: gameState } = useQuery({
  queryKey: ['game', gameId],
  queryFn: () => gameService.getGameState(gameId),
  refetchInterval: 1000  // Poll for updates
});
```

### Card Factory Functions

**File**: `frontend/src/utils/cardFactory.ts`

```typescript
import { createCardFromApiData, createTestCard } from '../utils/cardFactory';

// ✅ CORRECT - use factory functions
const card = createCardFromApiData(apiResponse, 'preview');

// ❌ WRONG - manual Card object creation (misses required fields)
const card: Card = { id: `preview-${data.name}`, name: data.name, ... };
```

---

## API Response Types

```typescript
interface GameStateResponse {
  game_id: string;
  turn: number;
  phase: "Start" | "Main" | "End";
  active_player_id: string;
  players: Record<string, PlayerState>;
  play_by_play: PlayByPlayEntry[];
}
```

### Route Consistency

- Frontend route: `/games/{game_id}/activate-ability`
- Backend route: Must match exactly
- Use `/docs` endpoint for OpenAPI reference

---

## Layout Patterns

### GameBoard Layout (Desktop)

```tsx
// 2-column grid: game zones | messages+actions
<div className="grid" style={{ 
  gap: 'var(--spacing-component-sm)', 
  gridTemplateColumns: '1fr 350px' 
}}>
  <div className="space-y-3">
    {/* Left: Opponent zones, player zones, hand */}
  </div>
  <div className="space-y-3">
    {/* Right: Messages + Actions (350px fixed) */}
  </div>
</div>
```

### Zone Organization

- Each player's zones: InPlay + Sleep side-by-side
- Clear divider between opponent and player zones
- Hand full-width below player's zones only
- Messages + Actions always visible on right

---

## Local Development

```bash
cd /Users/regis/Projects/ggltcg/frontend
npm install
npm run dev
# Frontend: http://localhost:5173
```

**Backend required**: Frontend expects API at http://localhost:8000

---

## Key Files

| File | Purpose |
|------|---------|
| `src/index.css` | Design tokens, utility classes |
| `src/utils/cardFactory.ts` | Card creation helpers |
| `src/services/gameService.ts` | API client |
| `src/components/GameBoard/` | Main game UI |
| `src/types/` | TypeScript interfaces |
