# Frontend Development Kickoff

## 🎉 Backend Complete!

The GGLTCG backend is **100% complete** and ready for frontend integration. All game logic, card effects, and AI opponent functionality are working and tested.

## Backend API Overview

### Base URL

```
http://localhost:8000
```

### Available Endpoints

#### Game Management

```http
POST /games
```

Creates a new game with two players.

**Request Body:**

```json
{
  "player1": {
    "player_id": "human",
    "name": "Player 1",
    "deck": ["Ka", "Knight", "Wizard"]
  },
  "player2": {
    "player_id": "ai",
    "name": "AI Opponent",
    "deck": ["Demideca", "Beary", "Archer"]
  }
}
```

**Response:** Full game state JSON

```http
GET /games/{game_id}
```

Get current game state.

**Response:** Full game state with all player zones, turn info, phase

```http
DELETE /games/{game_id}
```

Delete a game session.

#### Player Actions

```http
POST /games/{game_id}/play-card
```

Play a card from hand.

**Request Body:**

```json
{
  "player_id": "human",
  "card_name": "Ka"
}
```

```http
POST /games/{game_id}/tussle
```

Initiate a tussle (combat).

**Request Body:**

```json
{
  "player_id": "human",
  "attacker_name": "Ka",
  "defender_name": "Wizard"  // or null for direct attack
}
```

```http
POST /games/{game_id}/end-turn
```

End the current player's turn.

**Request Body:**

```json
{
  "player_id": "human"
}
```

```http
POST /games/{game_id}/ai-turn
```

Let the AI take its turn (AI will select and execute multiple actions until turn end).

**Request Body:**

```json
{
  "ai_player_id": "ai"
}
```

```http
GET /games/{game_id}/valid-actions
```

Get list of all valid actions for a player.

**Query Parameters:**

- `player_id`: ID of the player

**Response:**

```json
{
  "valid_actions": [
    {
      "action_type": "play_card",
      "card_name": "Ka",
      "cost_cc": 2,
      "description": "Play Ka (Cost: 2 CC)"
    },
    {
      "action_type": "tussle",
      "card_name": "Ka",
      "cost_cc": 2,
      "target_options": ["direct_attack"],
      "description": "Ka direct attack (Cost: 2 CC)"
    },
    {
      "action_type": "end_turn",
      "description": "End your turn"
    }
  ]
}
```

### Game State Structure

The game state JSON includes:

```typescript
{
  game_id: string;
  turn_number: number;
  phase: "START" | "MAIN" | "END";
  active_player_id: string;
  first_player_id: string;
  players: {
    [playerId: string]: {
      player_id: string;
      name: string;
      cc: number;  // Command Counters (0-7)
      hand: Card[];  // Cards in hand
      in_play: Card[];  // Cards on field
      sleep_zone: Card[];  // Defeated/sleeped cards
      direct_attacks_this_turn: number;
      cards_played_this_turn: number;
    }
  };
  game_log: string[];  // Event history
  winner: string | null;
}
```

### Card Structure

```typescript
{
  name: string;  // "Ka", "Knight", etc.
  card_type: "TOY" | "ACTION";
  cost: number;
  
  // Toy-specific fields (null for Actions)
  speed: number | null;
  strength: number | null;
  stamina: number | null;
  current_stamina: number | null;
  
  // Game state
  zone: "HAND" | "IN_PLAY" | "SLEEP";
  owner: string;  // player_id
  controller: string;  // player_id
}
```

## Recommended Tech Stack

### Core Framework

- **Vite** - Fast build tool and dev server
- **React 18** - UI framework
- **TypeScript** - Type safety

### Styling

- **Tailwind CSS** - Utility-first CSS framework
- **Headless UI** (optional) - Unstyled accessible components

### State Management

- **React Query (TanStack Query)** - Server state and API calls
- **Zustand** (optional) - Client state if needed

### HTTP Client

- **Axios** or native **fetch** for API calls

## Suggested Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── game/
│   │   │   ├── GameBoard.tsx
│   │   │   ├── PlayerZone.tsx
│   │   │   ├── CardDisplay.tsx
│   │   │   ├── ActionPanel.tsx
│   │   │   └── GameLog.tsx
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Modal.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       └── Footer.tsx
│   ├── api/
│   │   ├── client.ts  // Axios setup
│   │   └── game.ts    // Game API methods
│   ├── types/
│   │   ├── game.ts    // GameState, Player, Card types
│   │   └── api.ts     // API request/response types
│   ├── hooks/
│   │   ├── useGame.ts
│   │   ├── useGameActions.ts
│   │   └── useValidActions.ts
│   ├── utils/
│   │   ├── gameHelpers.ts
│   │   └── cardHelpers.ts
│   ├── App.tsx
│   └── main.tsx
├── public/
│   └── assets/
│       └── cards/  // Card images
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── vite.config.ts
```

## Key Components to Build

### 1. GameBoard (Main Container)

- Displays both players' zones
- Shows turn number, phase, active player
- Handles game flow

### 2. PlayerZone

- Shows player's cards in 3 zones: Hand, In Play, Sleep
- Displays player name and CC counter
- Highlights active player

### 3. CardDisplay

- Renders individual card with stats
- Different styling for Toys vs Actions
- Shows current stamina vs max stamina for Toys
- Click handlers for selection

### 4. ActionPanel

- Shows available actions from `/valid-actions`
- Buttons for: Play Card, Tussle, End Turn, AI Turn
- Disables invalid actions
- Shows action costs

### 5. GameLog

- Scrollable list of game events
- Shows turn-by-turn actions
- Highlights important events (tussles, sleeps, victory)

### 6. ResourceDisplay

- CC counter with visual bar (0-7)
- Shows CC cost for hovered actions
- Turn number and phase indicator

## Development Workflow

### 1. Setup

```bash
# Create Vite project
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Install dependencies
npm install axios @tanstack/react-query
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 2. Configure Tailwind

```typescript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### 3. Create API Client

```typescript
// src/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### 4. Define Types

```typescript
// src/types/game.ts
export interface Card {
  name: string;
  card_type: 'TOY' | 'ACTION';
  cost: number;
  speed: number | null;
  strength: number | null;
  stamina: number | null;
  current_stamina: number | null;
  zone: 'HAND' | 'IN_PLAY' | 'SLEEP';
  owner: string;
  controller: string;
}

export interface Player {
  player_id: string;
  name: string;
  cc: number;
  hand: Card[];
  in_play: Card[];
  sleep_zone: Card[];
  direct_attacks_this_turn: number;
  cards_played_this_turn: number;
}

export interface GameState {
  game_id: string;
  turn_number: number;
  phase: 'START' | 'MAIN' | 'END';
  active_player_id: string;
  first_player_id: string;
  players: Record<string, Player>;
  game_log: string[];
  winner: string | null;
}
```

### 5. Build Step-by-Step

1. Create basic GameBoard layout
2. Add PlayerZone components for both players
3. Implement CardDisplay with hover states
4. Add ActionPanel with valid actions
5. Integrate API calls with React Query
6. Add game flow logic (turn management)
7. Implement AI turn button
8. Add animations and polish

## Testing Strategy

### Development Testing

1. Start backend server: `cd backend && python run_server.py`
2. Start frontend dev server: `cd frontend && npm run dev`
3. Test against live API at `localhost:8000`

### Key Test Scenarios

- Create new game
- Play cards from hand
- Initiate tussles
- Direct attacks
- End turn
- AI takes turn
- Victory condition
- Error handling

## Next Steps

1. **Setup Vite + React + TypeScript project**
2. **Configure Tailwind CSS**
3. **Create type definitions** from API responses
4. **Build API client** with error handling
5. **Create basic layout** (GameBoard, PlayerZone)
6. **Implement card rendering**
7. **Add action buttons** and integrate API
8. **Test full game flow** with AI opponent
9. **Add animations** and visual polish
10. **Deploy** to Vercel/Netlify

## Resources

- **API Docs**: `http://localhost:8000/docs` (FastAPI auto-generated)
- **Game Rules**: `/docs/rules/GGLTCG Rules v1_1.md`
- **Card Data**: `/backend/data/cards.csv`
- **Backend Code**: `/backend/src/` for reference

## Pro Tips

1. **Use React Query** for API state - it handles caching, refetching, and error states
2. **Poll game state** while AI is thinking to show real-time updates
3. **Disable actions** when not active player or invalid
4. **Show costs** before confirming expensive actions
5. **Animate** card movements between zones for better UX
6. **Add sound effects** for tussles, card plays, victory
7. **Mobile-first** design - game should work on phones
8. **Dark mode** support with Tailwind

---

**Ready to build!** The backend is solid, tested, and waiting for a beautiful React UI. 🚀
