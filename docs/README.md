# Documentation Index

Welcome to the GGLTCG documentation.

## Quick Links

| Need | Document |
|------|----------|
| **Project story** | [RETROSPECTIVE.md](RETROSPECTIVE.md) — audit → two-weekend rebuild, with before/after |
| **Start coding** | [AGENTS.md](../AGENTS.md) (root context) |
| **Game rules** | [rules/QUICK_REFERENCE.md](rules/QUICK_REFERENCE.md) |
| **AI architecture** | [development/ai/AI_CURRENT_STATE.md](development/ai/AI_CURRENT_STATE.md) |
| **Architecture** | [development/ARCHITECTURE.md](development/ARCHITECTURE.md) |

## Documentation Structure

```
docs/
├── plans/                 # Active plans (actionable)
├── development/           # Technical documentation
│   ├── ai/               # AI system docs
│   ├── sessions/         # Session notes & postmortems
│   ├── archive/          # Completed/obsolete docs
│   └── ...
├── rules/                 # Game rules
│   ├── GGLTCG Rules v1_1.md
│   └── QUICK_REFERENCE.md
├── deployment/            # Deployment guides
├── setup/                 # Setup guides
└── dev-notes/             # Historical context (legacy)
```

## Key Documentation

### For AI Development

- **[AI Current State](development/ai/AI_CURRENT_STATE.md)** - Current AI subsystem reference (enum + Gemini architecture, env vars)
- **[AI V4 Design (archived)](development/ai/archive/AI_V4_DESIGN.md)** - Historical dual-request architecture design, superseded by enum
- **[Session Postmortem](development/sessions/SESSION_POSTMORTEM_2026_01_05.md)** - January 5 disaster analysis

### For General Development

- **[Architecture](development/ARCHITECTURE.md)** - System design and components
- **[Effect System](development/EFFECT_SYSTEM_ARCHITECTURE.md)** - Data-driven card effects
- **[Adding New Cards](development/ADDING_NEW_CARDS.md)** - Card implementation guide

### For Operations

- **[Deployment](deployment/DEPLOYMENT.md)** - Render + Vercel deployment

## Root Context Files

These files provide context for AI agents:

- **[AGENTS.md](../AGENTS.md)** - Root project context and architecture
- **[.github/instructions/](../.github/instructions/)** - Domain-specific coding standards

---

**Note**: `TROUBLESHOOTING.md` exists but contains generic guidance that may be outdated. Consider checking actual error messages and logs first.

