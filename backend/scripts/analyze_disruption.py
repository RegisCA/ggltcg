#!/usr/bin/env python3
"""
Analyze Disruption deck performance to understand why it's underperforming.
"""

import requests
import json


def analyze_disruption_losses():
    """Analyze Disruption deck losses."""
    resp = requests.get("http://localhost:8000/admin/simulation/runs/8/results")
    data = resp.json()
    
    print("=" * 70)
    print("DISRUPTION DECK ANALYSIS - V4 vs V4 Baseline (Run #8)")
    print("=" * 70)
    print()
    
    # Find all Disruption games
    disruption_games = []
    for game in data["games"]:
        if game["deck1_name"] == "Disruption" or game["deck2_name"] == "Disruption":
            is_p1 = game["deck1_name"] == "Disruption"
            opponent = game["deck2_name"] if is_p1 else game["deck1_name"]
            won = (is_p1 and game["outcome"] == "player1_win") or (
                not is_p1 and game["outcome"] == "player2_win"
            )
            disruption_games.append({
                "game_number": game["game_number"],
                "opponent": opponent,
                "is_p1": is_p1,
                "won": won,
                "turns": game["turn_count"],
                "disruption_cc": game["p1_cc_spent"] if is_p1 else game["p2_cc_spent"],
                "opponent_cc": game["p2_cc_spent"] if is_p1 else game["p1_cc_spent"],
            })
    
    # Summary by opponent
    print("DISRUPTION PERFORMANCE BY OPPONENT:")
    print("-" * 50)
    opponents = ["Aggro_Rush", "Control_Ka", "Tempo_Charge", "Disruption"]
    for opp in opponents:
        games = [g for g in disruption_games if g["opponent"] == opp]
        wins = sum(1 for g in games if g["won"])
        avg_turns = sum(g["turns"] for g in games) / len(games) if games else 0
        avg_cc = sum(g["disruption_cc"] for g in games) / len(games) if games else 0
        print(f"  vs {opp:15}: {wins:2}/{len(games):2} wins ({100*wins/len(games) if games else 0:.0f}%), "
              f"avg {avg_turns:.1f} turns, avg {avg_cc:.1f} CC spent")
    
    print()
    print("INDIVIDUAL GAME BREAKDOWN vs AGGRO_RUSH (0-20 record!):")
    print("-" * 70)
    
    aggro_games = [g for g in disruption_games if g["opponent"] == "Aggro_Rush"]
    for g in aggro_games:
        result = "WIN" if g["won"] else "LOSS"
        pos = "P1" if g["is_p1"] else "P2"
        print(f"  Game #{g['game_number']:3}: [{pos}] {result} in {g['turns']:2} turns "
              f"| Disruption CC={g['disruption_cc']:2}, Aggro CC={g['opponent_cc']:2}")
    
    # Find interesting games to deep-dive
    print()
    print("GAMES TO INVESTIGATE (looking at action logs):")
    print("-" * 70)
    
    # Get action logs for first 2 Disruption losses
    games_to_check = [g["game_number"] for g in aggro_games if not g["won"]][:2]
    
    for game_num in games_to_check:
        try:
            resp = requests.get(f"http://localhost:8000/admin/simulation/runs/8/games/{game_num}")
            game_detail = resp.json()
            
            print(f"\n=== GAME #{game_num} ACTION LOG ===")
            
            action_log = game_detail.get("action_log", [])
            if action_log:
                for action in action_log[:20]:  # First 20 actions
                    print(f"  Turn {action.get('turn', '?')}: {action.get('player', '?')} - "
                          f"{action.get('action_type', '?')} {action.get('details', '')[:50]}")
            else:
                print("  (No action log available)")
        except Exception as e:
            print(f"  Error getting game {game_num}: {e}")
    
    # Analyze CC efficiency
    print()
    print("CC EFFICIENCY ANALYSIS:")
    print("-" * 50)
    
    wins = [g for g in disruption_games if g["won"]]
    losses = [g for g in disruption_games if not g["won"]]
    
    if wins:
        avg_win_cc = sum(g["disruption_cc"] for g in wins) / len(wins)
        avg_win_turns = sum(g["turns"] for g in wins) / len(wins)
        print(f"  When Disruption WINS:  avg CC={avg_win_cc:.1f}, avg turns={avg_win_turns:.1f}")
    
    if losses:
        avg_loss_cc = sum(g["disruption_cc"] for g in losses) / len(losses)
        avg_loss_turns = sum(g["turns"] for g in losses) / len(losses)
        print(f"  When Disruption LOSES: avg CC={avg_loss_cc:.1f}, avg turns={avg_loss_turns:.1f}")
    
    # Check if Disruption spends more CC but still loses (tempo problem?)
    print()
    games_outspent = [g for g in losses if g["disruption_cc"] > g["opponent_cc"]]
    print(f"  Losses where Disruption spent MORE CC than opponent: {len(games_outspent)}/{len(losses)}")
    print("  (This suggests losing despite having resources = tempo/efficiency problem)")


if __name__ == "__main__":
    analyze_disruption_losses()
