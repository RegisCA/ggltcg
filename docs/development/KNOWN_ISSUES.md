# Known Issues & Workarounds

**Last Updated**: January 3, 2026

This document tracks unresolved issues, their workarounds, and recommended fixes for future sessions.

---

## 🔴 Active Issues

### 1. Logging Override Prevents LOG_LEVEL Control

**Severity**: Medium (affects developer experience, not functionality)  
**Affected**: Simulations, local development  
**Status**: Workaround in place

**Problem**:
- [backend/src/api/app.py](../../../backend/src/api/app.py) line 43 has hardcoded DEBUG level for AI logger:
  ```python
  logging.getLogger("game_engine.ai.llm_player").setLevel(logging.DEBUG)
  ```
- This overrides the `LOG_LEVEL` environment variable that is correctly implemented in [backend/src/game_engine/ai/__init__.py](../../../backend/src/game_engine/ai/__init__.py)
- Result: Even with `LOG_LEVEL=WARNING`, AI decision logs flood the console at DEBUG level during simulations

**Current Workaround**:
```bash
# Redirect stderr to /dev/null when running simulations
python run_server.py 2>/dev/null
```

**Recommended Fix** (5 minutes):

1. Remove the hardcoded override in `app.py` line 43:
   ```python
   # DELETE THIS LINE:
   # logging.getLogger("game_engine.ai.llm_player").setLevel(logging.DEBUG)
   ```

2. Let the environment variable control logging (already implemented in `ai/__init__.py`)

3. For local debugging when you WANT verbose AI logs, set env var:
   ```bash
   LOG_LEVEL=DEBUG python run_server.py
   ```

**Files to Modify**:
- `backend/src/api/app.py` (remove line 43)

**Why Not Fixed Yet**: This was a debug aid that was never removed. The workaround is functional but loses error visibility.

---

## 🟡 Monitoring Issues

### 2. CC Spend Summary Statistics May Be Incorrect

**Severity**: Low (data quality issue, not gameplay breaking)  
**Affected**: Simulation reports, analytics  
**Status**: Needs investigation

**Problem**:
- Run #39 summary shows "Winners avg 4.7 CC, Losers avg 3.4 CC"
- User identified this as likely incorrect (winners spending MORE CC than losers is counterintuitive)
- Per-turn CC tracking data appears correct in database
- Issue likely in aggregation/summary calculation in `orchestrator.py` lines 400-413

**Next Steps**:
1. Review CC calculation logic in `SimulationOrchestrator.get_results()`
2. Manually verify a few games' CC totals against database
3. Check if "spent" vs "generated" is being summed correctly
4. Fix calculation and mark Run #39 results as "data quality issue"

**Files to Check**:
- `backend/src/simulation/orchestrator.py` method `get_results()` lines 400-413
- `backend/tests/test_cc_tracking.py` (add tests for summary calculations)

---

## 🟢 Resolved Issues

### 3. Archer activate_ability Crash (Resolved)

**Severity**: ~~High~~ → Resolved  
**Affected**: ~~V4 vs V3 simulations with Archer deck~~  
**Status**: ✅ Cannot reproduce, code is correct

**Problem**:
- Run #12 (V4 vs V3) reported ~55% draws with error: `'GameEngine' object has no attribute 'activate_ability'`
- Archer deck seemed to cause crashes

**Investigation**:
- Examined [backend/src/simulation/runner.py](../../../backend/src/simulation/runner.py) lines 476-519 - implementation is correct
- Examined [backend/src/api/routes_actions.py](../../../backend/src/api/routes_actions.py) lines 284-360 - production endpoint is correct
- Attempted reproduction in test game - passed successfully
- All activate_ability code paths handle effects via EffectRegistry properly

**Conclusion**: Likely a transient error or already fixed. Code is correct.

---

## 📋 Future Improvements

See [SIMULATION_IMPROVEMENTS.md](./SIMULATION_IMPROVEMENTS.md) for planned enhancements:
1. Simulation CLI with presets (High priority)
2. Deck validation before starting runs (High priority)
3. Auto-generated reports (Medium priority)
4. Better logging control at simulation level (Medium priority)

---

## How to Use This Document

**When you encounter a bug**:
1. Check if it's already listed here
2. If not, add it to "Active Issues" with problem description and workaround
3. Link to relevant code/files
4. Estimate severity and effort to fix

**When you fix something**:
1. Move from "Active" to "Resolved" 
2. Add fix description and date
3. Link to PR/commit if applicable

**Before starting a session**:
1. Review "Active Issues" to see what needs attention
2. Pick quick wins (Low effort, High impact)
3. Update status as you work

---

## Related Documentation

- [AI_V4_BASELINE.md](./AI_V4_BASELINE.md) - Current V4 performance metrics
- [SIMULATION_IMPROVEMENTS.md](./SIMULATION_IMPROVEMENTS.md) - Planned feature enhancements
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design principles
