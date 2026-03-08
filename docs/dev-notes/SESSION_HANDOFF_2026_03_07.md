# Session Handoff — 2026-03-07

Branch: `feature/llm-provider-poc`
PR: [#313](https://github.com/RegisCA/ggltcg/pull/313) — open, in progress

## Render Deployment Notes (set before merging PR #313)

Set these environment variables in the Render dashboard for the backend service:

| Variable | Value | Notes |
|----------|-------|-------|
| `AI_PROVIDER` | `gemini` | Use Gemini in production (same as local) |
| `GOOGLE_API_KEY` | `<your key>` | Already set; verify it's present |
| `AI_PLANNER_MODE` | `single` | One-request planning; recommended |

**Do NOT set** `AI_MODEL` on Render — let it default to `gemini-3.1-flash-lite-preview` (500 RPD free).
**Do NOT set** Groq vars on Render — Groq free tier is ~100K tokens/day ≈ 1-2 games/day, not viable for production.

### Why Gemini and not Groq for production

Groq free tier is 100K tokens/day ≈ 57K tokens/game ≈ 1-2 games/day. Not viable.
Gemini `gemini-3.1-flash-lite-preview` gives 500 RPD ≈ 50+ games/day on the free tier.

## Work Completed This Session

### Session 1 fixes (on branch, tests passing)

1. **Clean card guidance** (`card_guidance.yaml`): Updated trap text to explicitly warn that Clean is useless when no toys are in play.

2. **Dynamic context notes** (`planning_prompt_v3.py`): Replaced static `TURN_1_GUIDANCE` constant with `_generate_context_notes()` — a dynamic function that emits `⛔` warnings based on actual board state:
   - Rush banned on turn 1 (when Rush is in hand on turn 1)
   - Clean useless when no toys in play (any turn)
   - Twist/Drop have no target when no opponent toys in play

3. **Sequence generator fixes** (`sequence_generator.py`, V4 dual mode):
   - Rush excluded from "Max potential CC" calculation on game turn 1
   - Same `⛔` restriction hints injected into QUICK RULES section
   - Added explicit constraint: direct_attack/tussle attacker must be from YOUR TOYS IN PLAY (not hand)

4. **`end_turn` matching robustness** (`llm_player.py`, `execution_prompt.py`):
   - `_is_action_available`, `find_matching_action_index`, and plan-exhaustion fallback now use `"end turn" in desc` as a fallback for end_turn detection, fixing 4 pre-existing test failures in `test_cc_plan_grounding.py`.

---

## Open Bugs for Next Session

~~All bugs listed below were addressed in Session 2.~~

### ✅ Bug 1 — Sleep zone cards included in AI-generated sequences (FIXED)

**Files changed**:
- `sequence_generator.py`: Added `⛔ SLEEP ZONE ≠ HAND` restriction hint listing slept card IDs explicitly when player has cards in sleep zone.
- `validators/turn_plan_validator.py` (`DependencyValidator`): Now catches sleep-zone plays by both card ID (with specific `sleep_zone_play` error type) and card name fallback.

### ✅ Bug 2 — Plan ends with CC left when combat still available (FIXED)

**Files changed**:
- `llm_player.py` (`LLMPlayerV3`): Added `_midturn_replan_count`, `_maybe_replan()` method, and wired it into `select_action()` at plan-exhaustion point. Triggers when CC > 1 AND `tussle`/`direct_attack` is in `valid_actions`. Capped at 2 re-plans per turn.

### Session 2 also fixed

5. **`conftest.py`**: Now loads `backend/.env` via dotenv — LLM tests no longer skip when API keys are in the `.env` file.
6. **5 test files**: Updated stale skip reason from `"Valid GOOGLE_API_KEY not set"` to `"No valid AI provider API key found"`.
7. **`.env.example`**: `AI_PLANNER_MODE` is now un-commented with `single` as the recommended value.

---

## Test Commands

```bash
cd backend && source ../.venv/bin/activate
# All tests (LLM tests now run if .env has a valid key)
pytest tests/ -q --tb=short

# Unit tests only (no API calls)
pytest tests/ -q --tb=short -m "not integration"
```

---

## Session 3 (2026-03-08) — Provider fixes, doc updates

### Fixes committed (`c6ed3fb`, `39e99ec`)

8. **`providers.py`**: `GEMINI_MODEL` now takes priority over `AI_MODEL` for the Gemini provider.
   - Root cause: stale `AI_MODEL=llama-3.1-8b-instant` shell env var was winning because `.env` had no `AI_MODEL` entry.
   - Fix: swap lookup order to `GEMINI_MODEL → AI_MODEL → default` for the gemini branch.
9. **`AI_SETUP.md`**: Updated with correct Groq model (`llama-3.3-70b-versatile`), Gemini free tier reality (500 RPD ≈ 50 games/day), new `AI_PLANNER_MODE` section, and fixed troubleshooting.
10. **`.gitignore`**: Added `backend/scripts/_*.py` rule — personal debug scripts prefixed with `_` are now excluded from git.
11. **Deployment decision**: Gemini everywhere (local + Render). Groq commented out in `.env`. Render handoff notes updated (was incorrectly saying `AI_PROVIDER=groq`).

### Key env var gotcha (RECORD FOR FUTURE SESSIONS)

`load_dotenv(override=True)` only overrides env vars that are **present in `.env`**. If `.env` uses `GEMINI_MODEL` but a stale shell var sets `AI_MODEL`, the stale value wins because `.env` has no `AI_MODEL` entry to override it. The fix is in `providers.py` (priority order), not in `.env`.

### Open deferred issue

- **Game `b6bbaae7`**: AI leaves CC behind, not aggressive enough after valid combat available. This is prompt tuning / model quality, not a mechanics bug. Flag for a dedicated prompt-tuning session post-deploy.

### Current branch state

Branch: `feature/llm-provider-poc`, HEAD: `39e99ec`
PR #313: ready to merge. Merge, then set Render env vars (see table above).
