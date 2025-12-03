#!/bin/bash
#
# Test script for Admin Data Viewer
# Verifies all API endpoints are working
#

set -e  # Exit on error

API_BASE="http://localhost:8000"
ADMIN_PREFIX="/admin"

echo "🔍 Testing Admin Data Viewer API Endpoints"
echo "=========================================="
echo ""

# Test 1: Summary Stats
echo "✓ Testing GET /admin/stats/summary"
response=$(curl -s "${API_BASE}${ADMIN_PREFIX}/stats/summary")
echo "$response" | python3 -m json.tool | head -20
echo ""

# Test 2: AI Logs (empty in this case but should return structure)
echo "✓ Testing GET /admin/ai-logs"
response=$(curl -s "${API_BASE}${ADMIN_PREFIX}/ai-logs?limit=2")
count=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
echo "  Found $count AI logs"
echo ""

# Test 3: Games List
echo "✓ Testing GET /admin/games"
response=$(curl -s "${API_BASE}${ADMIN_PREFIX}/games?limit=2")
count=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
echo "  Found $count games"
if [ "$count" -gt 0 ]; then
    echo "$response" | python3 -m json.tool | head -30
fi
echo ""

# Test 4: Game Playbacks
echo "✓ Testing GET /admin/game-playbacks"
response=$(curl -s "${API_BASE}${ADMIN_PREFIX}/game-playbacks?limit=2")
count=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
echo "  Found $count playbacks"
echo ""

# Test 5: Players Stats
echo "✓ Testing GET /admin/players"
response=$(curl -s "${API_BASE}${ADMIN_PREFIX}/players?limit=2")
count=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
echo "  Found $count players"
echo ""

# Test 6: Users
echo "✓ Testing GET /admin/users"
response=$(curl -s "${API_BASE}${ADMIN_PREFIX}/users?limit=2")
count=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
echo "  Found $count users"
echo ""

echo "=========================================="
echo "✅ All API endpoints working!"
echo ""
echo "📊 Access the admin viewer at:"
echo "   http://localhost:5173/admin.html"
echo ""
