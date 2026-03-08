#!/usr/bin/env python
"""
Investigate AI V4 execution failures for game 0a24b599-4b46-4c32-925c-59d6ec78046a turn 3
"""
import requests
import json

GAME_ID = '0a24b599-4b46-4c32-925c-59d6ec78046a'
TURN = 3
API_URL = 'https://ggltcg.onrender.com'  # Try production first, fallback to local

def fetch_ai_logs():
    """Fetch AI logs from admin API"""
    url = f'{API_URL}/admin/ai-logs?game_id={GAME_ID}&limit=200'
    print(f'Fetching from: {url}')
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def analyze_logs(data):
    """Analyze the logs for turn 3"""
    logs = data.get('logs', [])
    turn3_logs = [log for log in logs if log['turn_number'] == TURN]
    
    print(f'\n{"="*80}')
    print(f'INVESTIGATION: Game {GAME_ID}, Turn {TURN}')
    print(f'{"="*80}\n')
    
    if not turn3_logs:
        print(f'❌ No logs found for turn {TURN}')
        return
    
    print(f'✅ Found {len(turn3_logs)} log entries for turn {TURN}\n')
    
    for i, log in enumerate(turn3_logs):
        print(f'{"="*80}')
        print(f'LOG ENTRY {i+1}/{len(turn3_logs)}')
        print(f'{"="*80}')
        print(f'Log ID: {log["id"]}')
        print(f'Player: {log["player_id"]}')
        print(f'AI Version: {log["ai_version"]}')
        print(f'Action Number: {log["action_number"]}')
        print(f'Planned Action Index: {log.get("planned_action_index")}')
        print(f'Plan Execution Status: {log.get("plan_execution_status")}')
        
        tp = log.get('turn_plan')
        if not tp:
            print('\n⚠️  No turn_plan data')
            continue
        
        print(f'\n--- TURN PLAN STRUCTURE ---')
        print(f'Available keys: {list(tp.keys())}')
        
        # V4 Request 1 (Sequence Generator)
        r1_prompt = tp.get('v4_request1_prompt')
        r1_response = tp.get('v4_request1_response')
        
        # V4 Request 2 (Strategic Selector)
        r2_prompt = tp.get('v4_request2_prompt')
        r2_response = tp.get('v4_request2_response')
        
        # Debug info
        v4_debug = tp.get('v4_turn_debug', {})
        exec_log = tp.get('execution_log', [])
        
        print(f'\nV4 Request 1 Prompt: {"✅ Present" if r1_prompt else "❌ Missing"} ({len(r1_prompt or "")} chars)')
        print(f'V4 Request 1 Response: {"✅ Present" if r1_response else "❌ Missing"} ({len(r1_response or "")} chars)')
        print(f'V4 Request 2 Prompt: {"✅ Present" if r2_prompt else "❌ Missing"} ({len(r2_prompt or "")} chars)')
        print(f'V4 Request 2 Response: {"✅ Present" if r2_response else "❌ Missing"} ({len(r2_response or "")} chars)')
        print(f'V4 Turn Debug: {"✅ Present" if v4_debug else "❌ Missing"}')
        print(f'Execution Log: {"✅ Present" if exec_log else "❌ Missing"} ({len(exec_log)} entries)')
        
        # Save to files for detailed analysis
        output_dir = '/Users/regis/Projects/ggltcg/backend/scripts/turn3_analysis'
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        if r1_prompt:
            with open(f'{output_dir}/request1_prompt_log{i+1}.txt', 'w') as f:
                f.write(r1_prompt)
            print(f'✅ Saved request1 prompt to turn3_analysis/request1_prompt_log{i+1}.txt')
        
        if r1_response:
            with open(f'{output_dir}/request1_response_log{i+1}.json', 'w') as f:
                f.write(r1_response)
            print(f'✅ Saved request1 response to turn3_analysis/request1_response_log{i+1}.json')
            
            # Parse and analyze sequences
            try:
                # r1_response might already be a dict if loaded from turn_plan
                if isinstance(r1_response, str):
                    r1_data = json.loads(r1_response)
                else:
                    r1_data = r1_response
                    
                sequences = r1_data.get('sequences', [])
                print(f'\n📊 Request 1 generated {len(sequences)} sequences')
                
                for idx, seq in enumerate(sequences):
                    # seq might also need parsing
                    if isinstance(seq, str):
                        try:
                            seq = json.loads(seq)
                        except:
                            print(f'  ⚠️  Sequence {idx} is a string and cannot be parsed')
                            continue
                    
                    print(f'\n  Sequence {idx}:')
                    print(f'    Label: {seq.get("tactical_label")}')
                    actions = seq.get('actions', [])
                    print(f'    Actions: {len(actions)}')
                    
                    # Check for Knight cc_cost=0 issue
                    for aid, act in enumerate(actions):
                        card_name = act.get('card_name', '')
                        cc_cost = act.get('cc_cost', 'N/A')
                        action_type = act.get('action_type', '')
                        
                        if 'knight' in card_name.lower():
                            print(f'    🔍 Action {aid}: {action_type} {card_name} (cc_cost={cc_cost})')
                            if cc_cost == 0:
                                print(f'        ⚠️  FOUND cc_cost=0 for Knight in REQUEST 1 RESPONSE')
                        
                        if action_type == 'tussle':
                            target_names = act.get('target_names', [])
                            print(f'    🔍 Action {aid}: tussle with targets={target_names}')
                            if not target_names:
                                print(f'        ⚠️  FOUND empty target_names for tussle in REQUEST 1 RESPONSE')
                
            except (json.JSONDecodeError, TypeError) as e:
                print(f'⚠️  Failed to parse request1 response: {e}')
        
        if r2_prompt:
            with open(f'{output_dir}/request2_prompt_log{i+1}.txt', 'w') as f:
                f.write(r2_prompt)
            print(f'✅ Saved request2 prompt to turn3_analysis/request2_prompt_log{i+1}.txt')
            
            # Check if sequences are properly embedded in R2 prompt
            if 'sequences' in r2_prompt and 'knight' in r2_prompt.lower():
                print(f'  🔍 Checking sequences in R2 prompt for Knight...')
                # Look for cc_cost=0 in the prompt itself
                if '"cc_cost": 0' in r2_prompt and 'knight' in r2_prompt.lower():
                    print(f'  ⚠️  FOUND cc_cost=0 for a card (possibly Knight) in REQUEST 2 PROMPT')
        
        if r2_response:
            with open(f'{output_dir}/request2_response_log{i+1}.json', 'w') as f:
                f.write(r2_response)
            print(f'✅ Saved request2 response to turn3_analysis/request2_response_log{i+1}.json')
            
            try:
                r2_data = json.loads(r2_response)
                selected_idx = r2_data.get('selected_index', -1)
                reasoning = r2_data.get('reasoning', '')
                print(f'\n📊 Request 2 selected sequence {selected_idx}')
                print(f'    Reasoning: {reasoning[:200]}...')
            except json.JSONDecodeError as e:
                print(f'⚠️  Failed to parse request2 response: {e}')
        
        if v4_debug:
            with open(f'{output_dir}/v4_turn_debug_log{i+1}.json', 'w') as f:
                json.dump(v4_debug, f, indent=2)
            print(f'✅ Saved v4_turn_debug to turn3_analysis/v4_turn_debug_log{i+1}.json')
            
            print(f'\n📊 V4 Debug Metrics:')
            for key, value in v4_debug.items():
                print(f'    {key}: {value}')
        
        if exec_log:
            with open(f'{output_dir}/execution_log_log{i+1}.json', 'w') as f:
                json.dump(exec_log, f, indent=2)
            print(f'✅ Saved execution_log to turn3_analysis/execution_log_log{i+1}.json')
            
            print(f'\n📊 Execution Log ({len(exec_log)} entries):')
            for eidx, entry in enumerate(exec_log):
                action = entry.get('action', '')
                result = entry.get('result', '')
                print(f'    {eidx}: {action} -> {result}')
        
        # Save complete log entry
        with open(f'{output_dir}/complete_log{i+1}.json', 'w') as f:
            json.dump(log, f, indent=2)
        print(f'\n✅ Saved complete log entry to turn3_analysis/complete_log{i+1}.json')
        
        print('\n')

def main():
    try:
        print('Fetching AI logs from admin API...')
        data = fetch_ai_logs()
        analyze_logs(data)
        
        print(f'\n{"="*80}')
        print('ANALYSIS COMPLETE')
        print(f'{"="*80}')
        print('\n📁 All files saved to: backend/scripts/turn3_analysis/')
        print('\nNext steps:')
        print('1. Review request1_response to see if sequences have cc_cost=0 for Knight')
        print('2. Review request2_prompt to see if corrupted data was passed to selector')
        print('3. Compare execution_log to see what actually happened')
        
    except requests.exceptions.ConnectionError:
        print('❌ Could not connect to API at http://localhost:8000')
        print('   Make sure the backend server is running!')
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
