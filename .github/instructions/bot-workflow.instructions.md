---
applyTo: '*'
description: "Instructions for creating pull requests and performing automated tasks using the regisca-bot account"
---
# Bot Workflow Instructions

## Overview

The `regisca-bot` GitHub account is used to create pull requests for automated changes (security updates, dependency upgrades, etc.) so that the main `RegisCA` account can review and approve them following proper PR workflow.

## GitHub CLI Authentication

The GitHub CLI (`gh`) is configured with multiple accounts:
- `regisca-bot` - Bot account for automated PRs
- `RegisCA` - Main account for reviews and approvals

### Check Active Account

```bash
gh auth status
```

This shows which account is currently active.

### Switch Accounts

The GitHub CLI can have multiple accounts authenticated simultaneously. The active account is determined by which one was authenticated most recently or set explicitly.

To switch to a specific account:
```bash
gh auth switch -u regisca-bot
```

Or to switch back to the main account:
```bash
gh auth switch -u RegisCA
```

## Creating Pull Requests as Bot

When creating automated pull requests (security updates, dependency upgrades, etc.):

1. **Ensure regisca-bot is the active GitHub CLI account**:
   ```bash
   gh auth status  # Verify regisca-bot is active
   ```

2. **Create and checkout a feature branch**:
   ```bash
   git checkout -b branch-name
   ```

3. **Make changes and commit** (git user should already be configured as regisca-bot):
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

4. **Push the branch**:
   ```bash
   git push -u origin branch-name
   ```

5. **Create PR using GitHub CLI** (this will use the active regisca-bot account):
   ```bash
   gh pr create --title "PR Title" --body "PR Description" --base main --head branch-name
   ```

## Important Notes

- **DO NOT** use the MCP GitHub API tools (`mcp_github_github_create_pull_request`) as they use the authenticated user's credentials (RegisCA), not the bot account
- **ALWAYS** use `gh pr create` command to ensure the PR is created by regisca-bot
- Git user configuration should already be set to regisca-bot in the repository
- The bot account token has scopes: `project`, `read:org`, `repo`

## Deployment Pipeline

**⚠️ CRITICAL: Commits to `main` trigger automatic deployments**

When a PR is merged to the `main` branch, automated deployments are triggered:

- **Backend**: Automatically deploys to Render (https://ggltcg.onrender.com)
- **Frontend**: Automatically deploys to Vercel (production URL)

**Best Practices:**
- Always test changes thoroughly before merging to `main`
- Use feature branches and PRs for all changes
- Ensure backend and frontend changes are compatible before merging
- Monitor deployment status after merging (check Render and Vercel dashboards)

## Workflow for Security Updates

For Snyk security updates or similar automated changes:

1. Switch to regisca-bot GitHub CLI account
2. Create feature branch with descriptive name (e.g., `snyk-upgrade-package-name`)
3. Update requirements.txt or relevant dependency files
4. Test changes locally to ensure they work
5. Commit with detailed message explaining the security fix
6. Push branch
7. Create PR using `gh pr create` (as regisca-bot)
8. Switch back to RegisCA account to review and approve the PR

This workflow ensures proper separation of concerns and maintains PR approval workflow.
