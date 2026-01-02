"""
Phase-based examples for AI V4.

Each phase has a distinct strategic focus:
- Early game (T1-3): Board building, CC efficiency, avoid traps
- Mid game (T4-6): Pressure with toy advantage, favorable trades  
- End game (T7+): Lethal detection, closing sequences
"""

PHASE_EXAMPLES = {
    "early_game": """<example phase="early_game">
<situation>
Turn 1 as Player 1. CC: 2. Hand: [Surge, Knight, Archer].
Opponent: 0 toys in play.
</situation>
<analysis>
- T1 P1 has 2 CC base, Surge gives +1 = 3 CC budget
- Opponent has 0 toys = direct_attack available!
- Priority: Deploy toy AND deal damage
</analysis>
<optimal_sequence>
1. play_card Surge (0 CC, +1 gain) → 3 CC
2. play_card Knight (1 CC) → 2 CC
3. direct_attack with Knight (2 CC) → 0 CC
Result: 1 opponent card slept, board presence established
</optimal_sequence>
<key_lesson>Turn 1 with 0 opponent toys = opportunity to direct_attack. Don't just deploy—attack!</key_lesson>
</example>""",

    "mid_game": """<example phase="mid_game">
<situation>
Turn 4. CC: 4. Your toys: [Knight (1/5/3), Umbruh (4/4/2)].
Opponent toys: [Archer (2/0/5), Raggy (1/4/4)].
</situation>
<analysis>
- 4 CC budget, 2 tussles = 4 CC
- Knight auto-wins vs anything on YOUR turn
- Raggy is high threat (free tussles after T1)
- Archer blocks direct_attack but can't attack
</analysis>
<optimal_sequence>
1. tussle Knight → Raggy (2 CC) → 2 CC [Knight wins, Raggy slept]
2. tussle Umbruh → Archer (2 CC) → 0 CC [Umbruh wins, Archer slept]
Result: 2 toys slept, board cleared, direct_attack available next turn
</optimal_sequence>
<key_lesson>Use Knight's auto-win vs high-value targets. Clear blockers systematically.</key_lesson>
</example>""",

    "end_game": """<example phase="end_game">
<situation>
Turn 8. CC: 6. Your toys: [Knight (1/5/3), Paper Plane (2/2/1)].
Opponent: 2 cards in hand, 1 toy in play [Gibbers (3/2/2)], 3 cards slept.
LETHAL CHECK: Need to sleep 3 more cards to win (1 toy + 2 hand).
</situation>
<analysis>
- Knight tussle Gibbers (2 CC) = 1 slept → 4 CC remain
- Paper Plane bypasses blockers = direct_attack even with toys
- 2 direct_attacks (4 CC) = 2 hand cards slept
- Total: 3 cards slept = LETHAL
</analysis>
<optimal_sequence>
1. tussle Knight → Gibbers (2 CC) → 4 CC [Gibbers slept, 0 toys remain]
2. direct_attack Paper Plane (2 CC) → 2 CC [1 hand card slept]
3. direct_attack Knight (2 CC) → 0 CC [1 hand card slept]
Result: WIN - all 6 opponent cards slept
</optimal_sequence>
<key_lesson>Always check for lethal first. Count: toys + hand cards remaining vs your attack potential.</key_lesson>
</example>""",
}
