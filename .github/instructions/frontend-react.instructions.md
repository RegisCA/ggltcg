---
applyTo: 'frontend/**/*.{ts,tsx}'
description: "React/TypeScript code standards and API contracts for GGLTCG frontend"
---

# Frontend React/TypeScript Standards

## TypeScript Style

### Interfaces for Props

```typescript
interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
  isSelected?: boolean;
}
```

### Functional Components

```typescript
export const CardDisplay: React.FC<CardDisplayProps> = ({
  card,
  onClick,
  isSelected = false
}) => {
  // Component logic
  return (...)
};
```

### React Query Hooks

```typescript
const { data: gameState } = useQuery({
  queryKey: ['game', gameId],
  queryFn: () => gameService.getGameState(gameId),
  refetchInterval: 1000  // Poll for updates
});
```

## API Contracts

**CRITICAL**: All API requests use card IDs, NEVER card names.

### Request Types

```typescript
interface PlayCardRequest {
  player_id: string;
  card_id: string;  // NOT card_name
  target_ids?: string[];  // NOT target_card_names
  alternative_cost_card_id?: string;  // NOT card name
}
```

### Response Format

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
- Use OpenAPI/Swagger for documentation

## Spacing Design System

**CRITICAL**: ALWAYS use spacing design tokens, NEVER hardcode spacing values.

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

- `.panel-padding` - Standard panel padding (md)
- `.modal-padding` - Modal content padding (lg)
- `.card-padding` - Card component padding (sm)
- `.content-spacing` - Content element gaps (md)

### ✅ CORRECT Usage

```tsx
// Use design tokens in inline styles
<div style={{ padding: 'var(--spacing-component-md)' }}>
  <div style={{ gap: 'var(--spacing-component-sm)' }}>
    Content
  </div>
</div>

// Use utility classes
<div className="panel-padding">
  <div className="content-spacing">
    Content
  </div>
</div>
```

### ❌ WRONG Usage

```tsx
// NEVER hardcode spacing values
<div style={{ padding: '16px' }}>  // BAD!
<div className="p-4">  // BAD! (Tailwind utility)
<div style={{ gap: '12px' }}>  // BAD!
```

**Exceptions**: NONE. All spacing must use design tokens.

### Responsive Spacing

```tsx
const spacing = isMobile 
  ? 'var(--spacing-component-xs)' 
  : 'var(--spacing-component-md)';

<div style={{ padding: spacing }}>
```

## Typography Design System

**CRITICAL**: Use single font family (Lato) with weight variations. NEVER add custom font families.

### Font Setup

- Single font: **Lato** (loaded via Google Fonts)
- Two weights: 400 (normal), 700 (bold)

### Typography Hierarchy

| Element | Weight | Tailwind Class |
|---------|--------|----------------|
| Body text | 400 | `font-normal` |
| Headings, titles | 700 | `font-bold` |
| Card names | 700 | `font-bold` |
| Emphasis | 700 | `font-bold` |

### ✅ CORRECT Usage

```tsx
// Use Tailwind classes (preferred)
<h1 className="text-3xl font-bold">Game Title</h1>
<p className="text-base font-normal">Body text here</p>

// Use CSS weight in inline styles when needed
<span style={{ fontWeight: 700, fontSize: '1.5rem' }}>Heading</span>

// Font is inherited from body - no need to specify fontFamily
<div className="font-bold">Bold text</div>
```

### ❌ WRONG Usage

```tsx
// NEVER specify fontFamily inline
<div style={{ fontFamily: "'Bangers', sans-serif" }}>  // BAD!
<div style={{ fontFamily: 'var(--font-card-name)' }}>  // BAD!

// NEVER add new Google Fonts without team discussion
```

**Exceptions**: NONE. All text uses Lato. Visual hierarchy comes from weight and size, not font family.

## Card Factory Utilities

**File**: `frontend/src/utils/cardFactory.ts`

Use factory functions to create Card objects consistently:

```typescript
import { 
  createCardFromApiData, 
  createTestCard, 
  createCardInZone,
  withEffectiveCost 
} from '../utils/cardFactory';

// Convert API response to Card type
const card = createCardFromApiData(apiResponse, 'preview');

// Create cards for testing/storybook
const testCard = createTestCard({
  name: 'Test Knight',
  card_type: 'Toy',
  cost: 2,
  speed: 3,
  strength: 3,
  stamina: 3,
});

// Create card in specific zone
const handCard = createCardInZone(apiData, 'hand', 'player1');
```

### ❌ WRONG: Manual Card Object Creation

```typescript
// BAD - Easy to miss required fields
const card: Card = {
  id: `preview-${data.name}`,
  name: data.name,
  // ... 15+ more fields
};
```

### ✅ CORRECT: Use Factory Functions

```typescript
// GOOD - Handles all required fields, uses sensible defaults
const card = createCardFromApiData(data, 'preview');
```

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

- Each player's zones displayed side-by-side (InPlay + Sleep)
- Clear visual divider between opponent and player zones
- Hand positioned full-width below player's zones only
- Messages + Actions always visible on right side

## Local Development

```bash
cd /Users/regis/Projects/ggltcg/frontend
npm install
npm run dev
# Frontend: http://localhost:5173
```
