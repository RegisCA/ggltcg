"""
Combo examples for AI V4.

These are selected when MULTIPLE synergistic cards are present in the game.
Combo examples take priority over individual card examples.
"""

COMBO_EXAMPLES = {
    "surge_knight": """<example combo="Surge + Knight">
<situation>
Turn 1 P1. Charge: 2. Hand: [Surge, Knight, Archer].
Opponent: 0 toys in play.
</situation>
<key_insight>Surge (0 Charge, +1 gain) bridges the Charge gap to enable Knight + direct_attack.</key_insight>
<math>
- Without Surge: 2 Charge = Knight (1) only, no attack possible
- With Surge: 2 + 1 = 3 Charge = Knight (1) + direct_attack (2) = AGGRESSION
</math>
<optimal_sequence>
1. play_card Surge (0 Charge, +1 gain) → 3 Charge
2. play_card Knight (1 Charge) → 2 Charge
3. direct_attack Knight (2 Charge) → 0 Charge
Result: 1 opponent card broken on Turn 1, Knight on board
</optimal_sequence>
<priority>This combo should ALWAYS be executed when both cards are in hand Turn 1.</priority>
</example>""",

    "surge_double_play": """<example combo="Surge + Multiple Toys">
<situation>
Turn 1 P1. Charge: 2. Hand: [Surge, Umbruh, Beary].
Opponent: 0 toys in play.
</situation>
<key_insight>Surge enables playing TWO 1-Charge toys on Turn 1 for board dominance.</key_insight>
<math>
- Without Surge: 2 Charge = one 1-Charge toy + no attack
- With Surge: 3 Charge = two 1-Charge toys + 1 Charge left (or direct_attack one toy)
</math>
<optimal_sequence>
1. play_card Surge (0 Charge, +1 gain) → 3 Charge
2. play_card Umbruh (1 Charge) → 2 Charge
3. direct_attack Umbruh (2 Charge) → 0 Charge
Result: 1 card broken, Umbruh on board (better than 2 toys with no attack)
</optimal_sequence>
<alternative>If no direct_attack needed (defensive game), play both toys for board width.</alternative>
</example>""",

    "archer_finish": """<example combo="Archer + Low-STA Target">
<situation>
Archer in play. Opponent has Umbruh (4/4/2 current STA).
Charge: 3.
</situation>
<key_insight>Archer ability (1 Charge each) can chip 2 STA to 0 = auto-break for 2 Charge total.</key_insight>
<math>
- Tussle costs 2 Charge and risks losing YOUR toy
- Archer ability: 2 uses × 1 Charge = 2 Charge, guaranteed removal, Archer survives
</math>
<optimal_sequence>
1. activate_ability Archer → Umbruh (1 Charge) → 2 Charge [Umbruh at 1 STA]
2. activate_ability Archer → Umbruh (1 Charge) → 1 Charge [Umbruh at 0 STA = BROKEN]
Result: Umbruh removed for 2 Charge, Archer remains for future use
</optimal_sequence>
<key_rule>Count target STA. If STA ≤ your Charge budget, Archer can finish it.</key_rule>
</example>""",

    "knight_cleanup": """<example combo="Knight + Board Clear">
<situation>
Turn 5. Charge: 6. Knight in play.
Opponent: 2 toys [Gibbers (3/2/2), Wizard (3/3/3)], 2 cards in hand, 2 broken.
LETHAL CHECK: Need 4 more cards broken.
</situation>
<key_insight>Knight auto-wins on YOUR turn. Use to clear board, then direct_attack.</key_insight>
<math>
- 2 tussles (4 Charge) = 2 toys broken → board clear
- 2 direct_attacks (4 Charge) = 2 hand cards broken
- Total: 8 Charge needed, have 6 Charge → NOT lethal this turn
</math>
<optimal_sequence>
1. tussle Knight → Gibbers (2 Charge) → 4 Charge [Gibbers broken]
2. tussle Knight → Wizard (2 Charge) → 2 Charge [Wizard broken]
3. direct_attack Knight (2 Charge) → 0 Charge [1 hand card broken]
Result: 3 cards broken, 1 hand card remains, WIN next turn guaranteed
</optimal_sequence>
<key_lesson>Knight can solo clear boards. Prioritize board clear before hand depletion.</key_lesson>
</example>""",
}
