"""Debug script to analyze AI log #6259 for targeting bug."""

import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir / "src"))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from api.database import get_db
from api.db_models import AIDecisionLogModel

db = next(get_db())
log = db.query(AIDecisionLogModel).filter(AIDecisionLogModel.id == 6347).first()

if not log:
    print('Log #6347 not found')
    sys.exit(1)

print('='*80)
print('AI LOG #6347')
print('='*80)
print(f'Game ID: {log.game_id}')
print(f'Turn: {log.turn_number}')
print(f'Player: {log.player_id}')
print(f'Model: {log.model_name}')
print(f'Action #: {log.action_number}')

print(f'\n{"="*80}')
print('REASONING')
print('='*80)
print(log.reasoning)

print(f'\n{"="*80}')
print('RESPONSE')
print('='*80)
print(log.response)

print(f'\n{"="*80}')
print('PROMPT ANALYSIS')
print('='*80)

# Find the game state section
prompt = log.prompt

# Look for "In Play" sections
if "- In Play" in prompt:
    # Find all "In Play" mentions
    lines = prompt.split('\n')
    in_play_lines = []
    for i, line in enumerate(lines):
        if '- In Play' in line or 'In Play' in line:
            # Get context around this line
            start_idx = max(0, i-1)
            end_idx = min(len(lines), i+3)
            in_play_lines.extend(lines[start_idx:end_idx])
    
    print('\n'.join(in_play_lines))

# Find valid actions section
if "## YOUR VALID ACTIONS" in prompt:
    start = prompt.find("## YOUR VALID ACTIONS")
    end = start + 4000
    print(f'\n{"="*80}')
    print('VALID ACTIONS')
    print('='*80)
    print(prompt[start:end])
