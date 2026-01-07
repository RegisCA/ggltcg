# GGLTCG - Custom Trading Card Game

## Project Summary

2-player trading card game with Python/FastAPI backend, React/TypeScript frontend, and Google Gemini AI opponent.

## Quick Commands

```bash
# Backend (from project root)
source .venv/bin/activate && cd backend && python run_server.py
# → http://localhost:8000

# Frontend (new terminal, from project root)
cd frontend && npm run dev
# → http://localhost:5173

# Tests
cd backend && pytest tests/
```

## Project Layout

| Path | Description |
|------|-------------|
| `backend/` | Python FastAPI game engine, AI system |
| `frontend/` | React TypeScript UI |
| `backend/data/cards.csv` | Card definitions (source of truth) |
| `docs/rules/QUICK_REFERENCE.md` | Game rules (read this for mechanics) |

## Critical Rules

1. **IDs not names** - Use `card.id` for lookups, NEVER `card.name`
2. **Methods not assignment** - Use `card.apply_damage(3)`, NEVER `card.stamina -= 3`
3. **GameEngine for logic** - `engine.play_card()`, not `game_state.play_card()`
4. **Data-driven effects** - Card effects defined in `cards.csv`
5. **Verify game mechanics** - Read `docs/rules/QUICK_REFERENCE.md`, don't assume

## Turn Numbering

Turns alternate: P1(T1) → P2(T2) → P1(T3) → P2(T4)...
- Odd turns = Player 1 active
- Even turns = Player 2 active

## Context Files

- `AGENTS.md` - Root context (read first)
- `backend/AGENTS.md` - Backend patterns
- `frontend/AGENTS.md` - Frontend patterns

## Git Workflow

Two accounts: `regisca-bot` (automated PRs), `RegisCA` (manual work).
See `.github/instructions/bot-workflow.instructions.md` when creating PRs.

Commits to `main` → auto-deploy to Render (backend) + Vercel (frontend).
