# Instruction Files Migration Plan

**Created**: January 6, 2026  
**Updated**: January 7, 2026  
**Status**: ✅ COMPLETE  
**Purpose**: Migrate from `.github/instructions/*.md` files to hierarchical context system

---

## Final Structure (January 7, 2026)

### GitHub Copilot Auto-Discovery Files

| File | Lines | Purpose |
|------|-------|---------|
| `.github/copilot-instructions.md` | ~55 | Canonical file for VS Code Copilot |
| `AGENTS.md` | ~65 | Root context, architecture principles |
| `backend/AGENTS.md` | ~220 | Backend patterns, testing, AI system |
| `frontend/AGENTS.md` | ~145 | Design system, React patterns, API contracts |
| `docs/rules/QUICK_REFERENCE.md` | 68 | Authoritative game rules |

### Instruction Files (Path-Specific)

```
.github/instructions/       (~600 lines total)
├── architecture.instructions.md      (68)  - Quick reference → backend/AGENTS.md
├── backend-python.instructions.md    (83)  - Quick reference → backend/AGENTS.md
├── testing.instructions.md           (76)  - Quick reference → backend/AGENTS.md
├── frontend-react.instructions.md    (92)  - Quick reference → frontend/AGENTS.md
├── frontend-css.instructions.md      (69)  - Quick reference → frontend/AGENTS.md
├── coding.instructions.md           (~90)  - Universal, references AGENTS.md
├── bot-workflow.instructions.md     (104)  - Universal (keep full)
├── security-and-owasp.instructions.md (51) - Universal (keep full)
└── markdown.instructions.md          (38)  - Universal (keep full)
```

### Files Removed

- `CONTEXT.md` (348 lines) - Merged into trimmed `AGENTS.md`
- `COPILOT.md` (170 lines) - Merged into trimmed `AGENTS.md`
- `backend/BACKEND_GUIDE.md` - Renamed to `backend/AGENTS.md`
- `frontend/FRONTEND_GUIDE.md` - Renamed to `frontend/AGENTS.md`

### Context Reduction

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Root context files | 2 (518 lines) | 1 (65 lines) | **87%** |
| Total context loaded | ~1,200+ lines | ~500 lines | **~60%** |

---

## Key Changes (January 7, 2026)

1. **Created `.github/copilot-instructions.md`** - The canonical file GitHub Copilot looks for in VS Code
2. **Created trimmed `AGENTS.md`** - Merged CONTEXT.md + COPILOT.md, reduced from 518 → 65 lines
3. **Renamed guides to AGENTS.md** - Enables Copilot auto-discovery based on working directory
4. **Updated all instruction file references** - Now point to AGENTS.md files

## How It Works

GitHub Copilot in VS Code automatically loads:
1. `.github/copilot-instructions.md` - Always loaded (repository-wide)
2. `AGENTS.md` - Loaded based on proximity to working files
3. `.github/instructions/*.instructions.md` - Loaded based on `applyTo` patterns

The hierarchical AGENTS.md structure means:
- Working in `backend/` → loads `backend/AGENTS.md` + root `AGENTS.md`
- Working in `frontend/` → loads `frontend/AGENTS.md` + root `AGENTS.md`
- Less irrelevant context loaded per session
4. Commit and test
5. Continue to Phase 3 in next session
