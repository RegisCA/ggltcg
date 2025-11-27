#!/bin/bash
# Branch Cleanup Script
# Safely removes local branches that have been merged into main

set -e

echo "🧹 GGLTCG Branch Cleanup Script"
echo "================================"
echo ""

# Ensure we're on main and up to date
echo "📥 Fetching latest from origin..."
git fetch origin --prune

echo ""
echo "🔍 Finding merged branches..."
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
echo "📋 Merged branches (will be deleted):"
echo "-------------------------------------"

# Find merged branches (excluding main and current branch)
MERGED_BRANCHES=$(git branch --merged main | grep -v "^\*" | grep -v "main")

if [ -z "$MERGED_BRANCHES" ]; then
    echo "✅ No merged branches to clean up!"
    exit 0
fi

echo "$MERGED_BRANCHES"
echo ""

# Ask for confirmation
read -p "❓ Delete these branches? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🗑️  Deleting merged branches..."
    
    # Delete each merged branch
    echo "$MERGED_BRANCHES" | while read -r branch; do
        if [ ! -z "$branch" ]; then
            echo "   Deleting: $branch"
            git branch -d "$branch" 2>/dev/null || echo "   ⚠️  Could not delete $branch (may have unmerged changes)"
        fi
    done
    
    echo ""
    echo "✅ Local cleanup complete!"
    echo ""
    echo "🌐 Remote branches:"
    echo "   To delete remote branches, run:"
    echo "   git push origin --delete <branch-name>"
    echo ""
else
    echo "❌ Cleanup cancelled"
fi

echo ""
echo "📊 Remaining local branches:"
git branch
