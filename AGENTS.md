# GGLTCG Project Context

This is a custom trading card game - verify mechanics against authoritative sources, don't assume.

## Authoritative Sources

| Source | Content |
|--------|---------|
| `docs/rules/QUICK_REFERENCE.md` | Game rules, turn sequence, CC mechanics, zones |
| `backend/data/cards.csv` | Card stats, costs, and effect definitions |
| `docs/rules/GGLTCG Rules v1_1.md` | Detailed rules for edge cases |

## Architecture Principles

**ID-Based Lookups**: Use `game_state.find_card_by_id(card_id)`, never name-based searches. Multiple cards can share names.

**Method-Based State**: Use `card.apply_damage(3)`, `player.gain_cc(4)`. Direct assignment bypasses game logic.

**GameEngine/GameState Split**: GameEngine contains logic, GameState is pure serializable data.

**Data-Driven Effects**: Card effects in `cards.csv`, parsed by EffectRegistry. Complex effects (Copy, Transform) still need code.

## AI System (V4)

Dual-request architecture: Request 1 generates action sequences, Request 2 selects the best.
- Sequence Generator: `backend/src/game_engine/ai/prompts/sequence_generator.py`
- Strategic Selector: `backend/src/game_engine/ai/prompts/strategic_selector.py`
- Status: V4 in development, see `docs/plans/AI_V4_REMEDIATION_PLAN.md`

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
| Frontend | TypeScript, React 18, TanStack Query, Vite |
| AI | Google Gemini 1.5 Flash |
| Database | SQLite (local/simulation), PostgreSQL (production) |
| Deploy | Render (backend), Vercel (frontend) - auto-deploy from main |
