#!/usr/bin/env python3
"""
Deep analysis of deck matchups and why Disruption underperforms.
"""

# Deck compositions
DECKS = {
    "Aggro_Rush": {
        "cards": ["Dream", "Knight", "Raggy", "Umbruh", "Rush", "Surge"],
        "strategy": "Fast aggro with efficient creatures and CC generation",
        "toys": ["Dream (4cc, 5/4)", "Knight (1cc, 4/3 auto-win)", "Raggy (3cc, 3/2 free tussle)", "Umbruh (1cc, 4/4 CC on death)"],
        "actions": ["Rush (0cc, +2CC)", "Surge (0cc, +1CC)"],
        "strengths": ["Very cheap efficient creatures", "Rush + Surge = fast mana", "Knight auto-wins tussles", "Dream gets cheaper with sleeps"],
        "weaknesses": ["No board control", "Reliant on early tempo"],
    },
    "Control_Ka": {
        "cards": ["Ka", "Wizard", "Beary", "Copy", "Clean", "Wake"],
        "strategy": "Board control with Ka strength boost",
        "toys": ["Ka (2cc, 9/1 +2 str to team)", "Wizard (2cc, 3/3 tussles cost 1)", "Beary (1cc, 3/3 immune to opponent effects)"],
        "actions": ["Copy (-1cc, copy in-play card)", "Clean (3cc, sleep all)", "Wake (1cc, unsleep 1)"],
        "strengths": ["Ka buffs entire team +2 strength", "Clean is a board wipe", "Beary survives Clean/Monster", "Copy can duplicate key cards"],
        "weaknesses": ["Ka is fragile (1 stamina)", "Slow to set up"],
    },
    "Tempo_Charge": {
        "cards": ["Belchaletta", "Drum", "Hind Leg Kicker", "Violin", "Jumpscare", "Surge"],
        "strategy": "Charge generation and tempo plays",
        "toys": ["Belchaletta (1cc, 3/4 +2CC/turn)", "Drum (1cc, 3/2 +2 speed team)", "Hind Leg Kicker (1cc, 3/1 +1CC on card play)", "Violin (1cc, 1/2 +2 str team)"],
        "actions": ["Jumpscare (0cc, bounce)", "Surge (0cc, +1CC)"],
        "strengths": ["Massive CC generation (Belchaletta + HLK)", "Violin gives +2 strength", "All toys are cheap", "Jumpscare is tempo swing"],
        "weaknesses": ["Toys have low stamina", "No hard removal"],
    },
    "Disruption": {
        "cards": ["Gibbers", "Sock Sorcerer", "Monster", "Twist", "Drop", "Toynado"],
        "strategy": "Opponent disruption and control",
        "toys": ["Gibbers (1cc, 1/1 opponent cards +1 cost)", "Sock Sorcerer (3cc, 3/5 team immune to opponent effects)", "Monster (2cc, 1/2 set all stamina to 1)"],
        "actions": ["Twist (3cc, steal opponent card)", "Drop (2cc, sleep 1)", "Toynado (2cc, bounce all)"],
        "strengths": ["Monster can devastate boards", "Twist steals threats", "Sock Sorcerer protects team", "Gibbers slows opponent"],
        "weaknesses": ["Very reactive, not proactive", "Gibbers is 1/1 (dies immediately)", "Monster damages own cards too!", "Expensive actions (Twist=3cc, Toynado=2cc)"],
    },
}


def analyze_matchup(deck1: str, deck2: str) -> str:
    """Analyze why deck1 beats/loses to deck2."""
    d1 = DECKS[deck1]
    d2 = DECKS[deck2]
    
    analysis = []
    
    # Disruption vs Aggro_Rush specific
    if deck1 == "Disruption" and deck2 == "Aggro_Rush":
        analysis.append("WHY DISRUPTION LOSES TO AGGRO_RUSH:")
        analysis.append("")
        analysis.append("1. TEMPO MISMATCH:")
        analysis.append("   - Aggro has Rush (0cc, +2CC) + Surge (0cc, +1CC) = explosive early game")
        analysis.append("   - Disruption's answers are expensive (Twist=3cc, Drop=2cc)")
        analysis.append("   - By the time Disruption can react, Aggro already has board presence")
        analysis.append("")
        analysis.append("2. CREATURE QUALITY:")
        analysis.append("   - Aggro: Knight (4/3), Umbruh (4/4), Dream (5/4), Raggy (3/2)")
        analysis.append("   - Disruption: Gibbers (1/1), Monster (1/2), Sock Sorcerer (3/5)")
        analysis.append("   - Gibbers dies to everything, Monster damages own team!")
        analysis.append("")
        analysis.append("3. KNIGHT IS A PROBLEM:")
        analysis.append("   - Knight auto-wins tussles on your turn")
        analysis.append("   - Drop only sleeps 1 card, Knight comes back")
        analysis.append("   - Twist costs 3cc to steal it")
        analysis.append("")
        analysis.append("4. MONSTER BACKFIRES:")
        analysis.append("   - Monster sets ALL stamina to 1 (including your own cards)")
        analysis.append("   - Aggro's creatures are already cheap/replaceable")
        analysis.append("   - Disruption's expensive creatures get wrecked too")
        analysis.append("")
        analysis.append("5. GIBBERS IS TOO SLOW:")
        analysis.append("   - +1 cost doesn't matter when Aggro has 3 CC by turn 2")
        analysis.append("   - Gibbers is 1/1, dies to any tussle")
        analysis.append("   - Takes too long to have meaningful impact")
    
    return "\n".join(analysis)


def main():
    print("=" * 70)
    print("DISRUPTION DECK - DEEP ANALYSIS")
    print("=" * 70)
    print()
    
    print("DECK COMPOSITION:")
    print("-" * 50)
    d = DECKS["Disruption"]
    print(f"Cards: {', '.join(d['cards'])}")
    print(f"Strategy: {d['strategy']}")
    print()
    print("Toys:")
    for t in d["toys"]:
        print(f"  - {t}")
    print()
    print("Actions:")
    for a in d["actions"]:
        print(f"  - {a}")
    print()
    print("Strengths:")
    for s in d["strengths"]:
        print(f"  + {s}")
    print()
    print("Weaknesses:")
    for w in d["weaknesses"]:
        print(f"  - {w}")
    print()
    
    print("=" * 70)
    print(analyze_matchup("Disruption", "Aggro_Rush"))
    print()
    
    print("=" * 70)
    print("KEY INSIGHT: WHY DISRUPTION HAS 20% WIN RATE")
    print("=" * 70)
    print()
    print("Disruption is a REACTIVE deck in a game where PROACTIVE wins:")
    print()
    print("- Game average is 9 turns - not enough time for control to stabilize")
    print("- Monster (their board wipe) HURTS THEM TOO - damages Sock Sorcerer/Gibbers")
    print("- Gibbers is 1/1 for 1cc - terrible stat line, dies instantly")
    print("- Twist costs 3cc - by the time you can steal, opponent has multiple threats")
    print("- No good early game presence - relies on disrupting opponent's plan")
    print()
    print("The deck only wins 50% vs Control_Ka (the slowest deck) and loses to")
    print("anything with decent early game pressure.")
    print()
    print("SUGGESTIONS TO IMPROVE DISRUPTION DECK:")
    print("- Replace Gibbers with a more resilient early game creature")
    print("- Add CC generation (Rush/Surge) to keep up tempo")
    print("- Consider adding Beary for staying power")
    print("- Monster should probably be a different card")


if __name__ == "__main__":
    main()
