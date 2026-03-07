#!/usr/bin/env python
"""Extract AI logs for a specific game and turn."""
import sys
sys.path.insert(0, 'src')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.db_models import AIDecisionLogModel
import os
import json

# Get DB URL
db_url = os.environ.get('DATABASE_URL', 'sqlite:///./ggltcg.db')
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
db = Session()

# Query for the specific game
game_id = '0a24b599-4b46-4c32-925c-59d6ec78046a'
turn_number = 3

logs = db.query(AIDecisionLogModel).filter(
    AIDecisionLogModel.game_id == game_id,
    AIDecisionLogModel.turn_number == turn_number
).order_by(AIDecisionLogModel.id).all()

print(f'Found {len(logs)} logs for game {game_id}, turn {turn_number}\n')

if logs:
    for i, log in enumerate(logs):
        print(f'=== Log {i+1}/{len(logs)} (ID: {log.id}) ===')
        print(f'Player: {log.player_id}')
        print(f'AI Version: {log.ai_version}')
        print(f'Action Number: {log.action_number}')
        print(f'Model: {log.model_name}')
        
        if log.turn_plan:
            tp = log.turn_plan
            print(f'\nTurn Plan Keys: {list(tp.keys())}')
            
            # Check for V4 fields
            v4_fields = {
                'v4_request1_prompt': 'v4_request1_prompt' in tp,
                'v4_request1_response': 'v4_request1_response' in tp,
                'v4_request2_prompt': 'v4_request2_prompt' in tp,
                'v4_request2_response': 'v4_request2_response' in tp,
                'execution_log': 'execution_log' in tp,
                'v4_turn_debug': 'v4_turn_debug' in tp,
            }
            
            print('\nV4 Fields Present:')
            for field, exists in v4_fields.items():
                if exists:
                    value = tp[field]
                    if isinstance(value, str):
                        print(f'  {field}: Yes ({len(value)} chars)')
                    elif isinstance(value, (list, dict)):
                        print(f'  {field}: Yes ({type(value).__name__})')
                    else:
                        print(f'  {field}: Yes')
                else:
                    print(f'  {field}: No')
            
            # Write full data to file
            output_file = f'turn_{turn_number}_log_{i+1}.json'
            with open(output_file, 'w') as f:
                json.dump({
                    'log_id': log.id,
                    'game_id': str(log.game_id),
                    'turn_number': log.turn_number,
                    'player_id': log.player_id,
                    'ai_version': log.ai_version,
                    'model_name': log.model_name,
                    'action_number': log.action_number,
                    'prompt': log.prompt,
                    'response': log.response,
                    'reasoning': log.reasoning,
                    'turn_plan': tp,
                }, f, indent=2)
            print(f'\nFull data written to: {output_file}')
        else:
            print('Turn Plan: None')
        
        print('\n' + '='*60 + '\n')
else:
    print(f'No logs found for game {game_id}, turn {turn_number}')

db.close()
