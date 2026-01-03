"""
Card-specific tactical examples for AI V4.

Each example demonstrates a key pattern for a specific card.
Priority order for selection: Knight, Archer, Surge, Paper Plane, Drop, Wake.
"""

CARD_EXAMPLES = {
    "Knight": """<example card="Knight">
<situation>
Knight in play. Opponent has Wizard (3/3/3 SPD/STR/STA).
It's YOUR turn.
</situation>
<key_rule>Knight auto-wins ANY tussle on YOUR turn. Ignore stats entirely.</key_rule>
<optimal_play>
tussle Knight → Wizard (2 CC)
Result: Wizard slept instantly (Knight's ability triggers)
</optimal_play>
<anti_pattern>DON'T compare Knight's stats to opponent's. DON'T skip tussle thinking you'll lose.</anti_pattern>
</example>""",

    "Archer": """<example card="Archer">
<situation>
Archer in play. Opponent has Paper Plane (2/2/1 STA).
CC: 3.
</situation>
<key_rule>Archer ability (1 CC): Deal 1 damage to any toy. Use to chip low-STA toys to 0 = auto-sleep.</key_rule>
<math>Paper Plane has 1 STA. 1 activate_ability = 1 damage = 0 STA = slept!</math>
<optimal_play>
activate_ability Archer → Paper Plane (1 CC)
Result: Paper Plane slept for 1 CC (vs 2 CC for tussle)
</optimal_play>
<key_insight>Archer CANNOT attack (0 STR) but CAN remove toys efficiently via ability.</key_insight>
</example>""",

    "Surge": """<example card="Surge">
<situation>
Turn 1 P1. CC: 2. Hand: [Surge, Knight].
</situation>
<key_rule>Surge costs 0 CC and grants +1 CC immediately. Always play FIRST to unlock budget.</key_rule>
<math>Without Surge: 2 CC = Knight (1) + no attack. With Surge: 3 CC = Knight (1) + direct_attack (2).</math>
<optimal_sequence>
1. play_card Surge (0 CC, +1 gain) → 3 CC
2. play_card Knight (1 CC) → 2 CC
3. direct_attack Knight (2 CC) → 0 CC
</optimal_sequence>
<anti_pattern>DON'T play Knight first then realize you can't attack. Surge ENABLES plays.</anti_pattern>
</example>""",

    "Paper Plane": """<example card="Paper Plane">
<situation>
Paper Plane in play. Opponent has 1 toy (Archer) blocking direct attacks.
CC: 4.
</situation>
<key_rule>Paper Plane SPECIAL ABILITY: Can direct_attack even when opponent has toys in play.</key_rule>
<optimal_sequence>
1. direct_attack Paper Plane (2 CC) → 2 CC [bypasses Archer!]
2. direct_attack Paper Plane (2 CC) → 0 CC [max 2 per turn reached]
Result: 2 hand cards slept, Archer still in play but irrelevant
</optimal_sequence>
<key_insight>Paper Plane turns blockers into non-threats. Prioritize hand depletion over clearing board.</key_insight>
</example>""",

    "Drop": """<example card="Drop">
<situation>
Turn 1 P1. CC: 2. Hand: [Drop, Umbruh].
Opponent: 0 toys in play.
</situation>
<key_rule>Drop (2 CC): Sleeps target opponent toy. REQUIRES A TARGET—useless if opponent has 0 toys!</key_rule>
<wrong_play>play_card Drop → INVALID (no valid target)</wrong_play>
<optimal_play>
play_card Umbruh (1 CC) → 1 CC
Result: Board presence. Drop stays in hand for when opponent plays toys.
</optimal_play>
<anti_pattern>DON'T play Drop Turn 1 as P1. Save it for removing opponent's best toy later.</anti_pattern>
</example>""",

    "Wake": """<example card="Wake">
<situation>
Hand: [Wake, Knight]. Your sleep zone has Beary (slept earlier).
CC: 4.
</situation>
<key_rule>Wake (1 CC): ACTION card that returns target card from YOUR sleep zone to hand. Then you can play it.</key_rule>
<optimal_sequence>
1. play_card Wake → target Beary (1 CC) → 3 CC [Beary returns to hand]
2. play_card Beary (2 CC) → 1 CC [Beary now in play]
3. tussle/direct_attack as needed
</optimal_sequence>
<key_insight>Wake is play_card (ACTION from hand), NOT activate_ability. Costs 1 CC to play, then recovered card's cost to play it.</key_insight>
</example>""",
}
