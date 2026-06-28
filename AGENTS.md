# GGLTCG Project Context

This is a custom trading card game - verify mechanics against authoritative sources, don't assume.

Remember that your context window is limited - especially the output size. So you should always work in discrete steps and leverage #runSubagent.

## Authoritative Sources

| Source | Content |
|--------|---------|
| `docs/rules/QUICK_REFERENCE.md` | Game rules, turn sequence, Charge mechanics, zones |
| `backend/data/cards.csv` | Card stats, costs, and effect definitions |
| `docs/rules/GGLTCG Rules v1_1.md` | Detailed rules for edge cases |

## Architecture Principles

**ID-Based Lookups**: Use `game_state.find_card_by_id(card_id)`, never name-based searches. Multiple cards can share names.

**Method-Based State**: Use `card.apply_damage(3)`, `player.gain_charge(4)`. Direct assignment bypasses game logic.

**GameEngine/GameState Split**: GameEngine contains logic, GameState is pure serializable data.

**Data-Driven Effects**: Card effects in `cards.csv`, parsed by EffectRegistry. Complex effects (Copy, Transform) still need code.

## AI System

Two planner modes. **Production runs `dual` (V4) on Gemini.** The live path selects the mode from **`AI_VERSION`** (`4` → dual, else → single), *not* `AI_PLANNER_MODE` — the latter is read only by `get_planner_mode()`, which `get_ai_player()` bypasses, so `AI_PLANNER_MODE` has no effect in the running app (unfinished migration).

- **dual (a.k.a. V4) — what prod runs** — Request 1 generates action sequences, Request 2 selects the best, with a server-side `TurnPlanValidator` in between.
  - Sequence Generator: `backend/src/game_engine/ai/prompts/sequence_generator.py`
  - Strategic Selector: `backend/src/game_engine/ai/prompts/strategic_selector.py`
- **single (bare-checkout default)** — one request plans the whole turn, with server-side plan pruning and Charge regrounding.

Provider abstraction (`backend/src/game_engine/ai/providers.py`) supports Gemini/Groq/OpenRouter via `AI_PROVIDER` / `AI_MODEL`, but the deployed game always uses Gemini — prompts are Gemini-tuned, so swapping providers degrades play.

See `docs/development/ai/AI_CURRENT_STATE.md` for the full reference.

## Testing

Tests must explicitly set `turn_number` and `active_player`. Turn parity: odd=P1, even=P2.

```python
# Correct - explicit and valid
setup, cards = create_game_with_cards(
    player1_hand=["Ka"],
    turn_number=1,           # Odd = P1 active
    active_player="player1",
)
```

## Git Workflow

Two GitHub accounts: `regisca-bot` for automated PRs, `RegisCA` for manual work.
Check `gh auth status` before commits. See `bot-workflow.instructions.md` for PR workflow.
Access to GitHub MCP tools is enabled.

## Subsystem Guides

- `backend/AGENTS.md` - Game engine, effects, testing patterns
- `frontend/AGENTS.md` - Design system, React patterns, API contracts

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.13, FastAPI, SQLAlchemy |
| Frontend | TypeScript, React 19, TanStack Query, Vite 7 |
| AI | Google Gemini (`gemini-flash-lite-latest`), V4 dual-request planning. Provider abstraction for Groq/OpenRouter exists but prod is Gemini-only. |
| Database | SQLite (local/simulation), PostgreSQL (production) |
| Deploy | Render (backend), Vercel (frontend) - auto-deploy from main |
