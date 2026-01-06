---
applyTo: 'frontend/**/*.{ts,tsx}'
description: "React/TypeScript code standards and API contracts for GGLTCG frontend"
---

# Frontend React/TypeScript Standards

**Full details**: See `frontend/FRONTEND_GUIDE.md` for comprehensive frontend patterns.

## ⚠️ Critical: API Contracts

All API requests use card **IDs**, NEVER card names.

```typescript
// ✅ CORRECT
interface PlayCardRequest {
  player_id: string;
  card_id: string;        // NOT card_name
  target_ids?: string[];  // NOT target_card_names
}
```

## Spacing Design System

**CRITICAL**: ALWAYS use spacing design tokens, NEVER hardcode values.

```tsx
// ✅ CORRECT
<div style={{ padding: 'var(--spacing-component-md)' }}>
<div className="panel-padding">

// ❌ WRONG
<div style={{ padding: '16px' }}>
```

### Tokens (defined in `index.css`)

| Token | Value | Use |
|-------|-------|-----|
| `--spacing-component-xs` | 8px | Tight spacing |
| `--spacing-component-sm` | 12px | Component padding |
| `--spacing-component-md` | 16px | Default spacing |
| `--spacing-component-lg` | 24px | Section separation |
| `--spacing-component-xl` | 32px | Major layout |

## Typography

**Single font**: Lato. **Two weights only**: 400 (normal), 700 (bold).

```tsx
// ✅ CORRECT
<h1 className="font-bold">Title</h1>
<p className="font-normal">Body</p>

// ❌ WRONG - never add custom fonts
<div style={{ fontFamily: "'Bangers', sans-serif" }}>
```

## Card Factory Functions

```typescript
import { createCardFromApiData } from '../utils/cardFactory';

// ✅ CORRECT - handles all required fields
const card = createCardFromApiData(apiResponse, 'preview');

// ❌ WRONG - easy to miss fields
const card: Card = { id: `preview-${data.name}`, ... };
```

## React Patterns

```typescript
// Interfaces for props
interface CardDisplayProps {
  card: Card;
  onClick?: () => void;
}

// Functional components
export const CardDisplay: React.FC<CardDisplayProps> = ({ card, onClick }) => {
  // ...
};

// React Query for API state
const { data } = useQuery({
  queryKey: ['game', gameId],
  queryFn: () => gameService.getGameState(gameId),
  refetchInterval: 1000
});
```

