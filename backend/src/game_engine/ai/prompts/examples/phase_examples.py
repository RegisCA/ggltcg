"""
Phase-based examples for AI V4.

Each phase has a distinct strategic focus:
- Early game (T1-3): Board building, Charge efficiency, avoid traps
- Mid game (T4-6): Pressure with toy advantage, favorable trades
- End game (T7+): Lethal detection, closing sequences
"""

PHASE_EXAMPLES = {
    "early_game": """<example phase="early_game">
<situation>
Turn 1 as Player 1. Charge: 2. Hand: [Surge, Knight, Archer].
Opponent: 0 toys in play.
</situation>
<analysis>
- T1 P1 has 2 Charge base, Surge gives +1 = 3 Charge budget
- Opponent has 0 toys = direct_attack available!
- Priority: Deploy toy AND deal damage
</analysis>
<optimal_sequence>
1. play_card Surge (0 Charge, +1 gain) → 3 Charge
2. play_card Knight (1 Charge) → 2 Charge
3. direct_attack with Knight (2 Charge) → 0 Charge
Result: 1 opponent card broken, board presence established
</optimal_sequence>
<key_lesson>Turn 1 with 0 opponent toys = opportunity to direct_attack. Don't just deploy—attack!</key_lesson>
</example>""",

    "mid_game": """<example phase="mid_game">
<situation>
Turn 4. Charge: 4. Your toys: [Knight (1/5/3), Umbruh (4/4/2)].
Opponent toys: [Archer (2/0/5), Raggy (1/4/4)].
</situation>
<analysis>
- 4 Charge budget, 2 tussles = 4 Charge
- Knight auto-wins vs anything on YOUR turn
- Raggy is high threat (free tussles after T1)
- Archer blocks direct_attack but can't attack
</analysis>
<optimal_sequence>
1. tussle Knight → Raggy (2 Charge) → 2 Charge [Knight wins, Raggy broken]
2. tussle Umbruh → Archer (2 Charge) → 0 Charge [Umbruh wins, Archer broken]
Result: 2 toys broken, board cleared, direct_attack available next turn
</optimal_sequence>
<key_lesson>Use Knight's auto-win vs high-value targets. Clear blockers systematically.</key_lesson>
</example>""",

    "end_game": """<example phase="end_game">
<situation>
Turn 8. Charge: 6. Your toys: [Knight (1/5/3), Paper Plane (2/2/1)].
Opponent: 2 cards in hand, 1 toy in play [Gibbers (3/2/2)], 3 cards broken.
LETHAL CHECK: Need to break 3 more cards to win (1 toy + 2 hand).
</situation>
<analysis>
- Knight tussle Gibbers (2 Charge) = 1 broken → 4 Charge remain
- Paper Plane bypasses blockers = direct_attack even with toys
- 2 direct_attacks (4 Charge) = 2 hand cards broken
- Total: 3 cards broken = LETHAL
</analysis>
<optimal_sequence>
1. tussle Knight → Gibbers (2 Charge) → 4 Charge [Gibbers broken, 0 toys remain]
2. direct_attack Paper Plane (2 Charge) → 2 Charge [1 hand card broken]
3. direct_attack Knight (2 Charge) → 0 Charge [1 hand card broken]
Result: WIN - all 6 opponent cards broken
</optimal_sequence>
<key_lesson>Always check for lethal first. Count: toys + hand cards remaining vs your attack potential.</key_lesson>
</example>""",
}
