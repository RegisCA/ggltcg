# Documentation Index

Welcome to the GGLTCG documentation.

## Quick Links

| Need | Document |
|------|----------|
| **Start coding** | [AGENTS.md](../AGENTS.md) (root context) |
| **Game rules** | [rules/QUICK_REFERENCE.md](rules/QUICK_REFERENCE.md) |
| **AI V4 work** | [plans/AI_V4_REMEDIATION_PLAN.md](plans/AI_V4_REMEDIATION_PLAN.md) |
| **Architecture** | [development/ARCHITECTURE.md](development/ARCHITECTURE.md) |

## Documentation Structure

```
docs/
├── plans/                 # Active plans (actionable)
│   ├── AI_V4_REMEDIATION_PLAN.md
│   ├── INSTRUCTION_FILES_MIGRATION_PLAN.md
│   └── DOCS_RESTRUCTURING_PLAN.md (archive after this session)
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

- **[AI V4 Remediation Plan](plans/AI_V4_REMEDIATION_PLAN.md)** - Current work plan (Phase 0 ✅, Phase 1 ready)
- **[AI V4 Design](development/ai/AI_V4_DESIGN.md)** - Dual-request architecture
- **[Session Postmortem](development/sessions/SESSION_POSTMORTEM_2026_01_05.md)** - January 5 disaster analysis

### For General Development

- **[Architecture](development/ARCHITECTURE.md)** - System design and components
- **[Effect System](development/EFFECT_SYSTEM_ARCHITECTURE.md)** - Data-driven card effects
- **[Adding New Cards](development/features/ADDING_NEW_CARDS.md)** - Card implementation guide

### For Operations

- **[Deployment](deployment/DEPLOYMENT.md)** - Render + Vercel deployment

## Root Context Files

These files provide context for AI agents:

- **[AGENTS.md](../AGENTS.md)** - "Check Facts First" verification checklist
- **[COPILOT.md](../COPILOT.md)** - Architectural decisions and failure learnings
- **[.github/instructions/](../.github/instructions/)** - Domain-specific coding standards

---

**Note**: `TROUBLESHOOTING.md` exists but contains generic guidance that may be outdated. Consider checking actual error messages and logs first.

