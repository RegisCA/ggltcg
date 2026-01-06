---
applyTo: '*'
description: "Universal project standards and quick reference for GGLTCG"
---

# GGLTCG Project Standards

## Start Here

**⚠️ CRITICAL**: Before writing code, read these files:

1. **`CONTEXT.md`** (root) - Project context and "Check Facts First" checklist
2. **`COPILOT.md`** - Architectural decisions
3. **`backend/BACKEND_GUIDE.md`** or **`frontend/FRONTEND_GUIDE.md`** - Subsystem-specific patterns

These files contain verified facts and prevent common mistakes (like fabricating game mechanics or creating invalid test states).

## Quick Reference

**Starting a game**:
1. `source .venv/bin/activate`
2. `cd backend && python run_server.py`
3. (New terminal) `cd frontend && npm run dev`
4. Open `http://localhost:5173`

**Running tests**:
```bash
cd backend && pytest tests/
```

**Making changes**:
1. Create feature branch
2. Make changes following AGENTS.md patterns
3. Test manually + run pytest
4. Create PR (use regisca-bot for automated changes)
5. Review and merge to main

## Core Principles

1. **IDs not names** - Always use unique card IDs for lookups
2. **Methods not direct assignment** - Use proper methods to modify state
3. **GameEngine for logic, GameState for data** - Clear separation
4. **Data-driven effects** - Use CSV definitions in `backend/data/cards.csv`
5. **Test before deploying** - All tests pass before merge

## Git Workflow

### Branch Naming

```
feature/card-name-implementation  # New feature
fix/bug-description               # Bug fix
refactor/component-name           # Code refactoring
chore/update-dependencies         # Maintenance
```

### Commit Messages

```
feat: Add Archer activated ability
fix: Prevent direct stat modification in effects
refactor: Consolidate validation logic in ActionValidator
docs: Update architecture documentation
test: Add tests for UnsleepEffect
chore: Update dependencies
```

### Pull Requests

See `bot-workflow.instructions.md` for using regisca-bot for automated PRs.

## Deployment

**CRITICAL**: Commits to `main` trigger automatic deployments.

- **Backend**: Deploys to Render (https://ggltcg.onrender.com)
- **Frontend**: Deploys to Vercel

### Pre-Deploy Checklist

- [ ] All tests pass (`pytest backend/tests/`)
- [ ] No TypeScript errors (`npm run build`)
- [ ] No console errors in browser
- [ ] API documentation updated

## Documentation Structure

### Hierarchical Context

| File | Purpose | When to Read |
|------|---------|--------------|
| `CONTEXT.md` | Root context, "Check Facts First" | Always |
| `COPILOT.md` | Architectural decisions | Architecture questions |
| `backend/BACKEND_GUIDE.md` | Backend patterns, testing | Backend work |
| `frontend/FRONTEND_GUIDE.md` | Design system, React patterns | Frontend work |

### Authoritative Sources

| File | Content |
|------|---------|
| `docs/rules/QUICK_REFERENCE.md` | Game rules (67 lines) |
| `docs/rules/GGLTCG Rules v1_1.md` | Detailed rules |
| `backend/data/cards.csv` | Card definitions |

### Universal Instruction Files

These apply to all code and remain as instruction files:

| File | Domain |
|------|--------|
| `security-and-owasp.instructions.md` | Security patterns |
| `bot-workflow.instructions.md` | Git/PR workflow |
| `markdown.instructions.md` | Markdown style |
