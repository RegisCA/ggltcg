#!/usr/bin/env python3
"""
Quick diagnostic tool for analyzing AI game failures.
Usage: python diagnose_ai_game.py <game_id> [turn_number]
"""

import sys
import json
import requests
from typing import Dict, List, Any

def fetch_game_logs(game_id: str, use_local: bool = True) -> Dict[str, Any]:
    """Fetch AI logs from API."""
    base_url = "http://localhost:8000" if use_local else "https://ggltcg.onrender.com"
    url = f"{base_url}/admin/ai-logs?game_id={game_id}&limit=50"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def analyze_turn(turn_logs: List[Dict], turn_number: int) -> Dict[str, Any]:
    """Analyze a specific turn and identify issues."""
    if not turn_logs:
        return {"error": "No logs found for this turn"}
    
    # Get the most recent/complete log
    log = turn_logs[0]
    plan = log.get('turn_plan', {})
    
    issues = []
    analysis = {
        "turn": turn_number,
        "cc_available": plan.get('cc_start'),
        "ai_version": plan.get('ai_version'),
        "strategy": plan.get('strategy', 'N/A'),
        "actions_planned": plan.get('total_actions'),
        "issues": issues
    }
    
    # Parse Request 1 response
    planning_response = plan.get('planning_response', '') or plan.get('v4_request1_response', '')
    prompt = plan.get('v4_request1_prompt', '')
    
    if planning_response:
        try:
            resp1 = json.loads(planning_response)
            cc_claimed = resp1.get('available_cc')
            cc_actual = plan.get('cc_start')
            
            # Calculate potential CC (including Surge/Rush)
            cc_potential = cc_actual
            if prompt and "## YOUR HAND" in prompt:
                try:
                    hand_section = prompt.split("## YOUR HAND")[1].split("##")[0]
                    cc_potential += hand_section.count("- Surge") * 1
                    cc_potential += hand_section.count("- Rush") * 2
                except:
                    pass
            
            analysis['cc_claimed'] = cc_claimed
            analysis['cc_potential'] = cc_potential
            analysis['sequences_generated'] = len(resp1.get('sequences', []))
            
            # CC Hallucination Check
            # We allow claimed CC to match EITHER actual OR potential
            if cc_claimed and cc_actual:
                if cc_claimed != cc_actual and cc_claimed != cc_potential:
                    issues.append({
                        "type": "CC_HALLUCINATION",
                        "severity": "CRITICAL",
                        "details": f"AI claimed {cc_claimed} CC. Actual: {cc_actual}, Potential: {cc_potential}",
                        "impact": "All generated sequences may be illegal"
                    })
            
            # Check sequence costs
            sequences = resp1.get('sequences', [])
            illegal_sequences = []
            for i, seq in enumerate(sequences):
                # Extract CC cost from sequence string
                if '| CC:' in seq:
                    cost_str = seq.split('| CC:')[1].split('spent')[0].strip()
                    try:
                        cost = int(cost_str.split('/')[0])
                        # Compare against potential CC, as sequences might use Surge
                        if cost > cc_potential:
                            illegal_sequences.append((i, cost))
                    except:
                        pass
            
            if illegal_sequences:
                issues.append({
                    "type": "ILLEGAL_SEQUENCES",
                    "severity": "HIGH",
                    "details": f"{len(illegal_sequences)}/{len(sequences)} sequences exceed available CC ({cc_potential})",
                    "illegal_sequences": illegal_sequences
                })
            
            analysis['sequences'] = sequences[:3]  # Show first 3
            
        except Exception as e:
            issues.append({
                "type": "PARSE_ERROR",
                "severity": "LOW",
                "details": f"Could not parse Request 1 response: {e}"
            })
    
    # Check execution log
    execution_log = plan.get('execution_log', [])
    if execution_log:
        failed_actions = [e for e in execution_log if e.get('status') != 'success']
        if failed_actions:
            issues.append({
                "type": "EXECUTION_FAILURE",
                "severity": "HIGH",
                "details": f"{len(failed_actions)} actions failed to execute",
                "failed_actions": failed_actions
            })
            
    return analysis

def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnose_ai_game.py <game_id> [turn_number]")
        sys.exit(1)
        
    game_id = sys.argv[1]
    target_turn = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print(f"Fetching logs for game {game_id}...")
    try:
        data = fetch_game_logs(game_id)
        logs = data.get('logs', [])
        
        # Group logs by turn
        turns = {}
        for log in logs:
            t = log.get('turn_number')
            if t not in turns:
                turns[t] = []
            turns[t].append(log)
            
        sorted_turns = sorted(turns.keys())
        print(f"Found {len(logs)} logs across turns: {sorted_turns}")
        
        turns_to_analyze = [target_turn] if target_turn else sorted_turns
        
        for t in turns_to_analyze:
            if t not in turns:
                print(f"Turn {t} not found in logs")
                continue
                
            print(f"\n{'='*60}")
            print(f"TURN {t} ANALYSIS")
            print(f"{'='*60}")
            
            analysis = analyze_turn(turns[t], t)
            
            print(f"AI Version: {analysis.get('ai_version')}")
            print(f"CC Available: {analysis.get('cc_available')}")
            if 'cc_claimed' in analysis:
                print(f"CC Claimed (Request 1): {analysis['cc_claimed']}")
                if analysis['cc_claimed'] != analysis.get('cc_potential', analysis.get('cc_available')):
                     print(f"  ⚠️  MISMATCH: Delta of {analysis['cc_claimed'] - analysis.get('cc_available')} CC")
            
            print(f"Sequences Generated: {analysis.get('sequences_generated')}")
            
            issues = analysis.get('issues', [])
            if issues:
                print(f"\n🚨 ISSUES FOUND: {len(issues)}\n")
                for issue in issues:
                    print(f"🔴 {issue['type']} ({issue['severity']})")
                    print(f"   {issue['details']}")
                    if 'illegal_sequences' in issue:
                        print("     - " + "\n     - ".join([f"Sequence {i}: {cost} CC (exceeds {analysis.get('cc_potential')} CC)" for i, cost in issue['illegal_sequences'][:3]]))
            else:
                print("\n✅ No issues detected")
                
            print(f"\nStrategy: {analysis.get('strategy')[:200]}...")
            
            if 'sequences' in analysis:
                print(f"Sample Sequences (first 3):")
                for i, seq in enumerate(analysis['sequences']):
                    print(f"  {i}: {seq[:100]}...")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
