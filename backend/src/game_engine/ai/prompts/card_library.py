"""
Card effects library for AI strategic understanding.

This module contains detailed information about each card's effects,
strategic uses, and threat levels to help the AI make informed decisions.
"""

# Card effect library for AI strategic understanding
CARD_EFFECTS_LIBRARY = {
    # TOY CARDS
    "Ka": {
        "type": "Toy",
        "effect": "Continuous: All your other Toys get +2 Strength",
        "strategic_use": "TUSSLER - Either play when you want to force your opponent into a certain move like using Knight, or play when you can commit to an offensive play. Warning: Weak to a Raggy Archer combo",
        "threat_level": "MEDIUM - Good tussler, defensive pressure. Boosts opponent's entire board if they control it"
    },
    "Knight": {
        "type": "Toy",
        "effect": "Combat modifier: On your turn, this card wins all tussles it enters",
        "strategic_use": "TUSSLER - Can defeat strong Toys",
        "threat_level": "MEDIUM - Strong tussler that can sleep your cards reliably"
    },
    "Wizard": {
        "type": "Toy",
        "effect": "Continuous: All tussles you initiate cost exactly 1 CC (overrides normal tussle cost calculation)",
        "strategic_use": "ENABLES AGGRESSION - Makes tussling cost 1 CC (normally costs 2 CC per tussle). Play with a good tussler, play when you can commit to a good play",
        "threat_level": "HIGH - Can sleep lots of cards if used correctly, prioritize sleeping Wizard before other cards"
    },
    "Demideca": {
        "type": "Toy",
        "effect": "Continuous: All your Toys get +1 Speed, +1 Strength, +1 Stamina",
        "strategic_use": "ALL-AROUND BOOST - Solid buff to everything. Good mid-game play",
        "threat_level": "LOW - Can change the outcome of tussles in your opponents favor, if you cannot take out an opposing card, take Demideca out first to stop the continuous effect"
    },
    "Beary": {
        "type": "Toy",
        "effect": "Continuous: Cannot be affected by effects and targeted by opponent's Action cards",
        "strategic_use": "PROTECTION - Good defensive anchor if you need cards in play to block opposing effects",
        "threat_level": "LOW - Cannot be affected by effects. High speed"
    },
    "Ballaber": {
        "type": "Toy",
        "effect": "Alternative Cost: Instead of paying CC, you may sleep one of your cards",
        "strategic_use": "FREE PLAY - Can start tussling easily because of being able to be played for free. Warning: never sleep a card you have in play to play Ballaber for free. Sleep a card you have not used CC on",
        "threat_level": "MEDIUM - Strong tussler"
    },
    "Dream": {
        "type": "Toy",
        "effect": "Passive: Costs 1 CC less for each card in your Sleep Zone (base cost 4, minimum 0)",
        "strategic_use": "LATE GAME VALUE - Gets cheaper as game progresses. Can be FREE if you have 4+ sleeping cards. Strong 4/5/4 stats",
        "threat_level": "MEDIUM - Strong stats, gets cheaper in late game"
    },
    "Archer": {
        "type": "Toy",
        "effect": "Restriction: Cannot initiate tussles. Activated Ability: Spend 1 CC to remove 1 stamina from target opponent card in play (can repeat multiple times)",
        "strategic_use": "PRECISION FINISHER - Cannot tussle, but can spend CC to directly damage opponent's cards. Use to finish off damaged cards or weaken targets before tussling. Costs 1 CC per 1 stamina removed - can use multiple times per turn if you have CC",
        "threat_level": "LOW - Can directly damage your cards with CC, potentially finishing off weakened cards"
    },
    "Umbruh": {
        "type": "Toy",
        "effect": "Triggered: When this card is sleeped (from play), gain 1 CC",
        "strategic_use": "CC GAIN - Generates 1 CC when sleeped. Good value even if it gets removed",
        "threat_level": "HIGH - Your opponent playing this card is a sign that they want to go offensive on their next turn"
    },
    "Raggy": {
        "type": "Toy",
        "effect": "Passive: This card's tussles cost 0 CC. Restriction: Cannot tussle on turn 1",
        "strategic_use": "FREE TUSSLES - If your opponent has no cards in play, you can use it to sleep multiple opposing cards",
        "threat_level": "HIGH - Can sleep lots of your cards if you do not have a board presence"
    },
    
    # ACTION CARDS
    "Rush": {
        "type": "Action",
        "effect": "Gain 2 CC. Cannot be played on your first turn",
        "strategic_use": "CC BOOST - Free 2 CC after turn 1. Good for setting up big plays",
        "threat_level": "HIGH - Enables opponent to commit to plays (2 CC is enough for one tussle or card play)"
    },
    "Clean": {
        "type": "Action",
        "effect": "Sleep all Toys (yours and opponent's)",
        "strategic_use": "Use if your opponent has at least 2 cards in play (do not use to remove just 1 card). Warning: it removes your cards in play too",
        "threat_level": "MEDIUM - Do not put too many cards in play or Clean could sleep a lot of your cards"
    },
    "Twist": {
        "type": "Action",
        "effect": "Target: Take control of an opponent's Toy (you become controller, not owner)",
        "strategic_use": "THEFT - Steal opponent's best Toy. Can swing the game decisively.",
        "threat_level": "HIGH - Can steal your best cards"
    },
    "Wake": {
        "type": "Action",
        "effect": "Target: Return a card from your Sleep Zone to your hand",
        "strategic_use": "RECURSION - Get back one slept card",
        "threat_level": "LOW - Can undo your progress by waking slept cards"
    },
    "Copy": {
        "type": "Action",
        "effect": "Target: Create a copy of one of YOUR Toys in play (you must control the target)",
        "strategic_use": "CLONE - Duplicate your best Toy (Ka, Knight, Wizard). Can ONLY copy your own Toys, not opponent's.",
        "threat_level": "LOW - Can copy your best cards"
    },
    "Sun": {
        "type": "Action",
        "effect": "Target: Return up to 2 Toys from your Sleep Zone to your hand",
        "strategic_use": "MASS RECURSION - Get back multiple slept Toys. Great for recovery. Select 2 targets if possible.",
        "threat_level": "LOW - Opponent can recover multiple cards"
    },
    "Toynado": {
        "type": "Action",
        "effect": "Return all cards in play to their owner's hands",
        "strategic_use": "RESET - Bounces everything back to hand. Use when opponent has stronger board (or has used Twist to steal your best card).",
        "threat_level": "LOW - Can reset your board advantage"
    },
    
    # NEW CARDS (Beta)
    "Surge": {
        "type": "Action",
        "effect": "Gain 1 CC",
        "strategic_use": "FREE CC - Use when you need 1 more CC for a key play. Lower value than Rush but playable on turn 1.",
        "threat_level": "LOW - Small CC advantage for opponent"
    },
    "Drum": {
        "type": "Toy",
        "effect": "Continuous: All your Toys get +2 Speed",
        "strategic_use": "SPEED ADVANTAGE - Makes your cards strike first in tussles. Weak stats (1/3/2) but the speed boost is big.",
        "threat_level": "MEDIUM - Opponent's cards will strike first against yours"
    },
    "Violin": {
        "type": "Toy",
        "effect": "Continuous: All your Toys get +2 Strength",
        "strategic_use": "FORCE MULTIPLIER - Like Ka but cheaper with weaker stats (3/1/2). Good budget option for strength boost.",
        "threat_level": "MEDIUM - Boosts opponent's entire board"
    },
    "Drop": {
        "type": "Action",
        "effect": "Target: Sleep any card in play (yours or opponent's)",
        "strategic_use": "PRECISION REMOVAL - Sleep a specific threat. Cheaper than Clean but only one target. Triggers when-sleeped effects!",
        "threat_level": "HIGH - Can sleep your best card"
    },
    "Jumpscare": {
        "type": "Action",
        "effect": "Target: Return any card in play to owner's hand (no sleep trigger)",
        "strategic_use": "TEMPO BOUNCE - Return a threat without triggering when-sleeped. Great vs Umbruh! Opponent must replay the card.",
        "threat_level": "LOW - Can bounce your key card back to hand"
    },
    "Sock Sorcerer": {
        "type": "Toy",
        "effect": "Continuous: All your Toys are immune to opponent's card effects",
        "strategic_use": "TEAM PROTECTION - Protects ALL your cards from Twist, Clean, Copy, Drop, etc. Very powerful defensive anchor!",
        "threat_level": "CRITICAL - Your Action cards won't affect opponent's board while in play"
    },
    "VeryVeryAppleJuice": {
        "type": "Action",
        "effect": "This turn only: All your Toys get +1 Speed, +1 Strength, +1 Stamina",
        "strategic_use": "COMBAT BUFF - Use BEFORE tussling to win fights you'd otherwise lose. One turn only - use it or lose it!",
        "threat_level": "LOW - Temporary boost makes opponent's tussles stronger this turn"
    },
    "Belchaletta": {
        "type": "Toy",
        "effect": "Triggered: At start of your turn, gain 2 CC",
        "strategic_use": "CC ENGINE - Generates 2 extra CC every turn (6 total per turn!). Huge value if it survives. Priority removal target.",
        "threat_level": "HIGH - Opponent gains +2 CC per turn on top of normal 4"
    },
    "Hind Leg Kicker": {
        "type": "Toy",
        "effect": "Triggered: When you play another card, gain 1 CC",
        "strategic_use": "CC REFUND - Each card you play refunds 1 CC. Play before other cards in your turn. Great for combo turns with many plays. Weak stats (3/3/1) - protect it!",
        "threat_level": "MEDIUM - Opponent gets partial CC refund on plays"
    },
    "Gibbers": {
        "type": "Toy",
        "effect": "Continuous: Opponent's cards cost 1 more CC to play",
        "strategic_use": "ECONOMIC DISRUPTION - Makes opponent's plays more expensive. Very weak stats (1/1/1) but the cost increase hampers their tempo. Protect it to maintain the effect!",
        "threat_level": "HIGH - Your cards cost 1 more to play while Gibbers is in play. Priority removal target!"
    },
    "That was fun": {
        "type": "Action",
        "effect": "Target: Return an Action card from your Sleep Zone to your hand",
        "strategic_use": "ACTION RECURSION - Bring back powerful Actions like Rush, Clean, or Twist. More limited than Wake (only Actions) but free at 0 CC. Good synergy with high-impact Action cards.",
        "threat_level": "LOW - Lets opponent reuse their Action cards"
    },
    "Paper Plane": {
        "type": "Toy",
        "effect": "Combat modifier: Can direct attack opponent's hand even when they have cards in play",
        "strategic_use": "HAND PRESSURE - Bypasses opponent's defensive board to directly attack their hand. Use to pressure opponents who turtle behind defenders. Still costs CC and counts toward 2 direct attack limit per turn.",
        "threat_level": "MEDIUM - Can attack your hand directly even when you have defenders. Consider removing before it chips away your hand."
    },
    "Monster": {
        "type": "Toy",
        "effect": "On play: Set all opponent cards' stamina to 1. Cards already at 1 stamina are sleeped instead.",
        "strategic_use": "BOARD CONTROL - Weakens entire opponent board or sleeps low-stamina cards. Best against boards with mixed stamina values. Triggers sleep on 1-stamina cards like Beary (if not protected).",
        "threat_level": "MEDIUM - Can weaken or sleep your entire board when played. Particularly dangerous against low-stamina cards."
    },
}
