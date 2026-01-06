# Documentation Restructuring Plan

**Created**: January 6, 2026  
**Status**: Action Required  
**Purpose**: Fix documentation chaos and recover lost work from January 6 session

---

## Executive Summary

### What Happened

On January 6, 2026, a local git reset discarded 15+ commits that:
1. Reorganized `docs/development/` into logical subdirectories (`ai/`, `sessions/`, `features/`)
2. Created key planning documents (AGENTS.md, COPILOT.md, INSTRUCTION_FILES_MIGRATION_PLAN.md)
3. Created the AI V4 Remediation Plan and Session Postmortem
4. Added QUICK_REFERENCE.md for game rules

These commits exist in git reflog at `e758c31` but were never merged to `origin/main`.

### Impact

- **PR #290** references files that no longer exist (`docs/development/ai/AI_V4_REMEDIATION_PLAN.md`, `docs/development/sessions/SESSION_POSTMORTEM_2026_01_05.md`)
- **Phase 0 of AI V4 Remediation** was completed but plan is missing
- **Instruction Files Migration** was started but plan and outputs are missing
- **Current docs** are a flat mess of 30+ files with no organization

### Recovery Required

| File | Source Commit | Priority |
|------|---------------|----------|
| `docs/development/ai/AI_V4_REMEDIATION_PLAN.md` | `e758c31` | **Critical** |
| `docs/development/sessions/SESSION_POSTMORTEM_2026_01_05.md` | `e758c31` | **Critical** |
| `docs/development/INSTRUCTION_FILES_MIGRATION_PLAN.md` | `e758c31` | **High** |
| `docs/rules/QUICK_REFERENCE.md` | `e758c31` | **High** |
| `AGENTS.md` | `e758c31` | **High** |
| `COPILOT.md` | `e758c31` | **High** |
| Directory reorganization (`ai/`, `sessions/`, `features/`) | `738d084` | Medium |

---

## Current State (Broken)

```
docs/
├── README.md                          # Index - needs update
├── TROUBLESHOOTING.md                 # Keep
├── deployment/                        # OK - 2 files
├── dev-notes/                         # 19 files - needs cleanup
├── development/                       # 30+ files - CHAOS
│   ├── archive/                       # Exists - 9 files
│   └── features/                      # Exists - empty subfolder
├── rules/                             # 1 file - needs QUICK_REFERENCE.md
├── setup/                             # OK - 1 file
└── ux-review/                         # OK - 3 files
```

### Problems

1. **Flat structure** - 30+ files in `development/` with no organization
2. **AI docs scattered** - V4 design, baseline, tracking all at top level
3. **Missing subdirectories** - `ai/`, `sessions/` were created but reverted
4. **No planning docs** - Remediation plan, migration plan both gone
5. **Stale docs** - Game analysis docs for old games cluttering active docs

---

## Proposed Structure (Target)

```
docs/
├── README.md                          # Updated index
├── TROUBLESHOOTING.md                 # Keep
├── deployment/
│   ├── DEPLOYMENT.md
│   └── DEPLOYMENT_QUICKSTART.md
├── development/
│   ├── README.md                      # Navigation index
│   ├── ARCHITECTURE.md                # Core architecture
│   ├── EFFECT_SYSTEM_ARCHITECTURE.md  # Effect system
│   ├── DATABASE_SCHEMA.md             # Database docs
│   ├── KNOWN_ISSUES.md                # Active issues
│   ├── ai/                            # AI-specific docs
│   │   ├── AI_V4_DESIGN.md            # V4 architecture
│   │   ├── AI_V4_REMEDIATION_PLAN.md  # Active plan (recover)
│   │   ├── AI_V4_BASELINE.md          # Baseline metrics
│   │   └── archive/                   # Old analysis docs
│   ├── features/                      # Feature implementations
│   │   ├── ADDING_NEW_CARDS.md
│   │   ├── SIMULATION_SYSTEM.md
│   │   ├── AUTH_IMPLEMENTATION.md
│   │   └── ...
│   ├── sessions/                      # Session notes & postmortems
│   │   └── SESSION_POSTMORTEM_2026_01_05.md
│   └── archive/                       # Completed/obsolete docs
├── plans/                             # NEW: Active plans
│   ├── AI_V4_REMEDIATION_PLAN.md      # Recover from e758c31
│   └── INSTRUCTION_FILES_MIGRATION_PLAN.md  # Recover from e758c31
├── rules/
│   ├── GGLTCG Rules v1_1.md           # Full rules
│   └── QUICK_REFERENCE.md             # Recover from e758c31
├── setup/
│   └── QUICKSTART.md
├── ux-review/
│   └── ...
└── dev-notes/                         # Archive - historical context
    └── ...
```

---

## Recovery Commands

### Step 1: Recover Critical Files

```bash
# From project root
cd /Users/regis/Projects/ggltcg

# Create target directories
mkdir -p docs/plans
mkdir -p docs/development/ai/archive
mkdir -p docs/development/sessions

# Recover AI V4 Remediation Plan
git show e758c31:docs/development/ai/AI_V4_REMEDIATION_PLAN.md > docs/plans/AI_V4_REMEDIATION_PLAN.md

# Recover Session Postmortem
git show e758c31:docs/development/sessions/SESSION_POSTMORTEM_2026_01_05.md > docs/development/sessions/SESSION_POSTMORTEM_2026_01_05.md

# Recover Instruction Files Migration Plan
git show e758c31:docs/development/INSTRUCTION_FILES_MIGRATION_PLAN.md > docs/plans/INSTRUCTION_FILES_MIGRATION_PLAN.md

# Recover QUICK_REFERENCE.md
git show e758c31:docs/rules/QUICK_REFERENCE.md > docs/rules/QUICK_REFERENCE.md

# Recover root context files
git show e758c31:AGENTS.md > AGENTS.md
git show e758c31:COPILOT.md > COPILOT.md
```

### Step 2: Move AI Docs to Subdirectory

```bash
# Move current AI docs to ai/ subdirectory
mv docs/development/AI_V4_BASELINE.md docs/development/ai/
mv docs/development/AI_V4_DESIGN.md docs/development/ai/
mv docs/development/AI_V4_DIAGNOSTIC_IMPROVEMENTS.md docs/development/ai/
mv docs/development/AI_V4_IMPROVEMENTS_TRACKING.md docs/development/ai/
mv docs/development/AI_V4_RESEARCH_SUMMARY.md docs/development/ai/
mv docs/development/TROUBLESHOOT_GEMINI_25.md docs/development/ai/

# Move old game analysis to archive
mv docs/development/AI_V4_GAME_ANALYSIS_*.md docs/development/ai/archive/
mv docs/development/AI_STRATEGY_ANALYSIS_*.md docs/development/ai/archive/
mv docs/development/AI_IMPROVEMENTS_2025-11-20.md docs/development/ai/archive/
```

### Step 3: Clean dev-notes

```bash
# Move to archive (these are historical, not actionable)
mv docs/dev-notes/AI_PROMPT_V2.4_REMOVE_BUILDING.md docs/development/ai/archive/
mv docs/dev-notes/AI_V3_*.md docs/development/ai/archive/
mv docs/dev-notes/BUG_*.md docs/development/archive/
mv docs/dev-notes/SESSION_HANDOFF_*.md docs/development/sessions/
```

---

## Plan Update Requirements

### AI V4 Remediation Plan

After recovery, update to reflect:

1. ✅ **Phase 0**: Completed via PR #290
2. Update file paths to new structure
3. Add Phase 1 starter prompt
4. Mark acceptance criteria status

### Instruction Files Migration Plan

After recovery, update to reflect:

1. ✅ Phase 1 & 2 were attempted but reverted
2. AGENTS.md and COPILOT.md need to be re-committed
3. Update to simpler Phase 1 approach

---

## Action Items

### Immediate (Today)

- [ ] Run recovery commands (Step 1)
- [ ] Move AI docs to subdirectory (Step 2)
- [ ] Update AI_V4_REMEDIATION_PLAN.md with Phase 0 completion
- [ ] Update INSTRUCTION_FILES_MIGRATION_PLAN.md with current status
- [ ] Commit all changes

### This Week

- [ ] Clean dev-notes (Step 3)
- [ ] Update docs/README.md with new structure
- [ ] Create docs/development/README.md navigation index
- [ ] Review and archive stale docs

### Next Session

- [ ] Resume AI V4 Remediation Phase 1 (CC Waste Tracking)
- [ ] Or resume Instruction Files Migration Phase 1

---

## Lessons Learned

1. **Always push commits** - Local work can be lost on reset
2. **Use feature branches** - Protect unfinished work from main resets
3. **One concern per session** - Don't mix docs reorganization with code fixes
4. **Archive vs delete** - Move stale docs to archive, don't delete

---

## References

- Git commit with full organized state: `e758c31`
- Initial reorganization commit: `738d084`
- PR #290 (Phase 0 completion): https://github.com/RegisCA/ggltcg/pull/290
