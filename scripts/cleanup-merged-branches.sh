#!/bin/bash
# Branch Cleanup Script
# Safely removes local branches that have been merged into main
# Works with both regular merges and squash merges (GitHub's default)

set -e

AUTO_CONFIRM=false
DRY_RUN=false

print_usage() {
    echo "Usage: ./scripts/cleanup-merged-branches.sh [--yes|-y] [--dry-run]"
    echo ""
    echo "Options:"
    echo "  --yes, -y   Delete matched branches without prompting"
    echo "  --dry-run   Show branches that would be deleted, but do not delete"
    echo "  --help, -h  Show this help"
}

for arg in "$@"; do
    case "$arg" in
        --yes|-y)
            AUTO_CONFIRM=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $arg"
            echo ""
            print_usage
            exit 1
            ;;
    esac
done

echo "🧹 GGLTCG Branch Cleanup Script"
echo "================================"
echo ""

# Ensure we're on main and up to date
echo "📥 Fetching latest from origin..."
git fetch origin --prune

echo ""
echo "🔍 Finding branches to clean up..."
echo ""

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

# Switch to main if not already there
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  You're on branch: $CURRENT_BRANCH"
    echo "   Switching to main for cleanup..."
    git checkout main
fi

# Update main
git pull origin main

echo ""
echo "📋 Branches to clean up:"
echo "------------------------"

# Find branches that:
# 1. Are merged (traditional merge)
# 2. OR have a corresponding remote branch that was deleted (squash merged PRs)
# 3. OR whose remote branch no longer exists after fetch --prune
BRANCHES_TO_DELETE=""

for branch in $(git branch | grep -v "^\*" | grep -v "main"); do
    branch=$(echo "$branch" | xargs)  # Trim whitespace
    
    # Skip protected branches
    if [ "$branch" = "main" ] || [ -z "$branch" ]; then
        continue
    fi
    
    # Check if branch is merged (traditional)
    if git branch --merged main | grep -q "^\s*$branch$"; then
        echo "  $branch (merged)"
        BRANCHES_TO_DELETE="$BRANCHES_TO_DELETE $branch"
        continue
    fi
    
    # Check if remote tracking branch was deleted (squash merge indicator)
    REMOTE_BRANCH="origin/$branch"
    if ! git show-ref --verify --quiet "refs/remotes/$REMOTE_BRANCH"; then
        # Remote branch doesn't exist - likely squash merged and deleted
        echo "  $branch (remote deleted - likely squash merged)"
        BRANCHES_TO_DELETE="$BRANCHES_TO_DELETE $branch"
        continue
    fi
done

if [ -z "$BRANCHES_TO_DELETE" ]; then
    echo "✅ No branches to clean up!"
    echo ""
    echo "📊 Current local branches:"
    git branch
    exit 0
fi

echo ""

# Ask for confirmation unless explicitly auto-confirmed
if [ "$AUTO_CONFIRM" = true ]; then
    REPLY="y"
elif [ "$DRY_RUN" = true ]; then
    REPLY="n"
    echo "🔎 Dry run mode: no branches will be deleted"
else
    read -p "❓ Delete these branches? (y/N) " -n 1 -r
    echo ""
fi

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🗑️  Deleting branches..."
    
    # Delete each branch
    for branch in $BRANCHES_TO_DELETE; do
        if [ ! -z "$branch" ]; then
            echo "   Deleting: $branch"
            if [ "$DRY_RUN" = true ]; then
                echo "   (dry-run) Skipped deletion"
            else
                git branch -D "$branch" 2>/dev/null || echo "   ⚠️  Could not delete $branch"
            fi
        fi
    done
    
    echo ""
    echo "✅ Local cleanup complete!"
    echo ""
else
    echo "❌ Cleanup cancelled"
fi

echo ""
echo "📊 Remaining local branches:"
git branch
