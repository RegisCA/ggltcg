#!/bin/bash
# Quick lobby flow test using curl
# Usage: ./test_lobby_curl.sh

set -e  # Exit on error

BASE_URL="https://ggltcg.onrender.com"

echo "🎮 Testing Multiplayer Lobby Flow"
echo "=================================="
echo ""

# Step 1: Create lobby
echo "📝 Step 1: Creating lobby (Player 1: Alice)..."
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/games/lobby/create" \
  -H "Content-Type: application/json" \
  -d '{"player1_name": "Alice"}')

echo "$CREATE_RESPONSE" | python3 -m json.tool

GAME_CODE=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['game_code'])")
GAME_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['game_id'])")

echo ""
echo "✅ Lobby created! Game Code: $GAME_CODE"
echo "   Game ID: $GAME_ID"
echo ""

# Step 2: Check status (waiting)
echo "📊 Step 2: Checking lobby status (should be waiting_for_player)..."
curl -s "$BASE_URL/games/lobby/$GAME_CODE/status" | python3 -m json.tool
echo ""

# Step 3: Join lobby
echo "📝 Step 3: Joining lobby (Player 2: Bob)..."
JOIN_RESPONSE=$(curl -s -X POST "$BASE_URL/games/lobby/$GAME_CODE/join" \
  -H "Content-Type: application/json" \
  -d '{"player2_name": "Bob"}')

echo "$JOIN_RESPONSE" | python3 -m json.tool
echo ""
echo "✅ Player 2 joined!"
echo ""

# Step 4: Check status (both joined)
echo "📊 Step 4: Checking lobby status (should be deck_selection)..."
curl -s "$BASE_URL/games/lobby/$GAME_CODE/status" | python3 -m json.tool
echo ""

# Step 5: Player 1 submits deck
echo "📝 Step 5: Player 1 submitting deck..."
P1_DECK='["Ka", "Demideca", "Ballaber", "Twist", "Clean", "Sun"]'
START1_RESPONSE=$(curl -s -X POST "$BASE_URL/games/lobby/$GAME_CODE/start" \
  -H "Content-Type: application/json" \
  -d "{\"player_id\": \"player1\", \"deck\": $P1_DECK}")

echo "$START1_RESPONSE" | python3 -m json.tool
echo ""

# Step 6: Player 2 submits deck
echo "📝 Step 6: Player 2 submitting deck..."
P2_DECK='["Ka", "Demideca", "Ballaber", "Twist", "Clean", "Sun"]'
START2_RESPONSE=$(curl -s -X POST "$BASE_URL/games/lobby/$GAME_CODE/start" \
  -H "Content-Type: application/json" \
  -d "{\"player_id\": \"player2\", \"deck\": $P2_DECK}")

echo "$START2_RESPONSE" | python3 -m json.tool
echo ""

# Check if game started
STATUS=$(echo "$START2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")

if [ "$STATUS" = "active" ]; then
    echo "🎉 SUCCESS! Game started!"
    echo ""
    echo "📊 Step 7: Fetching game state (as Player 1 to see hand)..."
    curl -s "$BASE_URL/games/$GAME_ID?player_id=player1" | python3 -m json.tool | head -40
    echo ""
    echo "✅ All tests passed! Game is ready to play."
else
    echo "⚠️  Game status: $STATUS (expected: active)"
fi

echo ""
echo "Game Code: $GAME_CODE"
echo "Game ID: $GAME_ID"
