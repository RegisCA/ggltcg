# Session Handoff — 2026-03-07

Branch: `feature/llm-provider-poc`
PR: [#313](https://github.com/RegisCA/ggltcg/pull/313) — open, in progress

## Render Deployment Notes (set before merging PR #313)

Three new environment variables must be set in the Render dashboard for the backend service:

| Variable | Value | Notes |
|----------|-------|-------|
| `AI_PROVIDER` | `groq` | Switches from Gemini to Groq (no rate-limit issues) |
| `GROQ_API_KEY` | `<your key>` | From https://console.groq.com/keys |
| `AI_PLANNER_MODE` | `single` | One-request planning; recommended for Groq |

`GOOGLE_API_KEY` can stay in place as fallback; it will be ignored while `AI_PROVIDER=groq`.

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
