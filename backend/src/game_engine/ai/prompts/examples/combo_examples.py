"""
Combo examples for AI V4.

These are selected when MULTIPLE synergistic cards are present in the game.
Combo examples take priority over individual card examples.
"""

COMBO_EXAMPLES = {
    "surge_knight": """<example combo="Surge + Knight">
<situation>
Turn 1 P1. CC: 2. Hand: [Surge, Knight, Archer].
Opponent: 0 toys in play.
</situation>
<key_insight>Surge (0 CC, +1 gain) bridges the CC gap to enable Knight + direct_attack.</key_insight>
<math>
- Without Surge: 2 CC = Knight (1) only, no attack possible
- With Surge: 2 + 1 = 3 CC = Knight (1) + direct_attack (2) = AGGRESSION
</math>
<optimal_sequence>
1. play_card Surge (0 CC, +1 gain) → 3 CC
2. play_card Knight (1 CC) → 2 CC  
3. direct_attack Knight (2 CC) → 0 CC
Result: 1 opponent card slept on Turn 1, Knight on board
</optimal_sequence>
<priority>This combo should ALWAYS be executed when both cards are in hand Turn 1.</priority>
</example>""",

    "surge_double_play": """<example combo="Surge + Multiple Toys">
<situation>
Turn 1 P1. CC: 2. Hand: [Surge, Umbruh, Beary].
Opponent: 0 toys in play.
</situation>
<key_insight>Surge enables playing TWO 1-CC toys on Turn 1 for board dominance.</key_insight>
<math>
- Without Surge: 2 CC = one 1-CC toy + no attack
- With Surge: 3 CC = two 1-CC toys + 1 CC left (or direct_attack one toy)
</math>
<optimal_sequence>
1. play_card Surge (0 CC, +1 gain) → 3 CC
2. play_card Umbruh (1 CC) → 2 CC
3. direct_attack Umbruh (2 CC) → 0 CC
Result: 1 card slept, Umbruh on board (better than 2 toys with no attack)
</optimal_sequence>
<alternative>If no direct_attack needed (defensive game), play both toys for board width.</alternative>
</example>""",

    "archer_finish": """<example combo="Archer + Low-STA Target">
<situation>
Archer in play. Opponent has Umbruh (4/4/2 current STA).
CC: 3.
</situation>
<key_insight>Archer ability (1 CC each) can chip 2 STA to 0 = auto-sleep for 2 CC total.</key_insight>
<math>
- Tussle costs 2 CC and risks losing YOUR toy
- Archer ability: 2 uses × 1 CC = 2 CC, guaranteed removal, Archer survives
</math>
<optimal_sequence>
1. activate_ability Archer → Umbruh (1 CC) → 2 CC [Umbruh at 1 STA]
2. activate_ability Archer → Umbruh (1 CC) → 1 CC [Umbruh at 0 STA = SLEPT]
Result: Umbruh removed for 2 CC, Archer remains for future use
</optimal_sequence>
<key_rule>Count target STA. If STA ≤ your CC budget, Archer can finish it.</key_rule>
</example>""",

    "knight_cleanup": """<example combo="Knight + Board Clear">
<situation>
Turn 5. CC: 6. Knight in play. 
Opponent: 2 toys [Gibbers (3/2/2), Wizard (3/3/3)], 2 cards in hand, 2 slept.
LETHAL CHECK: Need 4 more cards slept.
</situation>
<key_insight>Knight auto-wins on YOUR turn. Use to clear board, then direct_attack.</key_insight>
<math>
- 2 tussles (4 CC) = 2 toys slept → board clear
- 2 direct_attacks (4 CC) = 2 hand cards slept
- Total: 8 CC needed, have 6 CC → NOT lethal this turn
</math>
<optimal_sequence>
1. tussle Knight → Gibbers (2 CC) → 4 CC [Gibbers slept]
2. tussle Knight → Wizard (2 CC) → 2 CC [Wizard slept]
3. direct_attack Knight (2 CC) → 0 CC [1 hand card slept]
Result: 3 cards slept, 1 hand card remains, WIN next turn guaranteed
</optimal_sequence>
<key_lesson>Knight can solo clear boards. Prioritize board clear before hand depletion.</key_lesson>
</example>""",
}
