---
applyTo: '*'
description: "Universal project standards and quick reference for GGLTCG"
---

# GGLTCG Project Standards

## Quick Reference

**Starting a game**:
1. `source .venv/bin/activate`
2. `cd backend && python run_server.py`
3. (New terminal) `cd frontend && npm run dev`
4. Open `http://localhost:5173`

**Running tests**:
```bash
pytest backend/tests/
```

**Making changes**:
1. Create feature branch
2. Make changes following guidelines
3. Test manually + run pytest
4. Create PR using regisca-bot if automated
5. Review and merge to main

## Core Principles (All Code)

1. **IDs not names** - Always use unique card IDs for lookups
2. **Methods not direct assignment** - Use proper methods to modify state
3. **GameEngine for logic, GameState for data** - Keep separation clean
4. **Data-driven effects when possible** - Use CSV definitions
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

## Documentation Resources

### Internal Docs

- `docs/rules/GGLTCG Rules v1_1.md` - Game rules
- `docs/development/ARCHITECTURE.md` - System architecture
- `docs/development/EFFECT_SYSTEM_ARCHITECTURE.md` - Effect system design

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Pytest Documentation](https://docs.pytest.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

## Instruction File Index

Domain-specific instructions are in separate files with proper `applyTo` targeting:

| File | Domain | Applies To |
|------|--------|------------|
| `architecture.instructions.md` | Game engine architecture | `backend/**/*.py` |
| `backend-python.instructions.md` | Python code style | `backend/**/*.py` |
| `frontend-react.instructions.md` | React/TypeScript | `frontend/**/*.{ts,tsx}` |
| `frontend-css.instructions.md` | CSS design tokens | `frontend/**/*.css` |
| `testing.instructions.md` | Test patterns | `backend/tests/**/*.py` |
| `security-and-owasp.instructions.md` | Security | `*` |
| `bot-workflow.instructions.md` | Git/PR workflow | `*` |
| `markdown.instructions.md` | Markdown style | `**/*.md` |
| `snyk_rules.instructions.md` | Security scanning | `**` |
