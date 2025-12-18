# Quick Test Guide - Multiplayer Lobby

## Local Testing Setup

### 1. Start Backend (if not already running)

```bash
cd backend
source ../.venv/bin/activate  # or your venv activation
python run_server.py
# Backend: http://localhost:8000
```

### 2. Start Frontend

```bash
cd frontend
npm run dev
# Frontend: http://localhost:5174/ (or check terminal for port)
```

## Test Scenarios

### Scenario 1: Full Multiplayer Flow

### Player 1 (Browser Window 1)

1. Open `http://localhost:5174/`
2. Click "Create Game"
3. Enter name "Alice"
4. Copy the 6-character game code (e.g., "9P47XA")
5. Wait for Player 2 to join
6. Select a deck (e.g., 4 Toys, 2 Actions)
7. Wait for Player 2's deck selection
8. Game should start automatically

### Player 2 (Browser Window 2 or Incognito)

1. Open `http://localhost:5174/`
2. Click "Join Game"
3. Enter name "Bob"
4. Enter the game code from Player 1
5. Select a deck
6. Game should start automatically

### Expected Result (Scenario 1)

- Both players see the same game
- Both can take turns (no AI auto-play)
- Game state syncs between windows

### Scenario 2: Single-Player (Regression Test)

1. Open `http://localhost:5174/`
2. Click "Play vs AI"
3. Select deck for Player 1
4. Select deck for AI
5. Game starts with AI opponent

### Expected Result (Scenario 2)

- AI takes turns automatically
- Everything works as before

### Scenario 3: Error Handling

### Test Invalid Game Code

1. Click "Join Game"
2. Enter name
3. Enter invalid code "ABCDEF"
4. Should show error: "Lobby not found" or similar

### Test Already Full Lobby

1. Create a lobby
2. Have Player 2 join
3. Try to join with a 3rd player using same code
4. Should show error

## Visual Checks

- [ ] Menu buttons have hover effects
- [ ] Game code is displayed in large monospace font
- [ ] Copy-to-clipboard works and shows "✓ Copied"
- [ ] Player names appear in waiting room
- [ ] Deck selection status shows "✓ Deck Ready"
- [ ] Loading states show during API calls
- [ ] Error messages display clearly

## Production Test (Optional)

If backend is deployed to `https://ggltcg.onrender.com`:

1. Set `VITE_API_URL=https://ggltcg.onrender.com` in `.env` (or use default)
2. Run same tests as above
3. Verify lobby creation and joining works across different networks

## Common Issues

### Port Already in Use

```bash
# Kill process on port 5173/5174
lsof -ti:5173 | xargs kill -9
```

### Backend Not Responding

```bash
# Check backend is running
curl http://localhost:8000/docs
# Should return FastAPI docs
```

### CORS Errors

- Backend should have CORS enabled for `http://localhost:5174`
- Check browser console for specific errors

## Success Criteria

✅ Can create lobby and get game code  
✅ Can join lobby with valid code  
✅ Both players see each other's names  
✅ Deck selection works for both players  
✅ Game starts automatically when both ready  
✅ Both players can play (no AI interference)  
✅ Single-player mode still works  

---

### Next Steps After Testing

1. Fix any bugs found
2. Deploy frontend to Vercel
3. Test production deployment
4. Share game with real players! 🎮
