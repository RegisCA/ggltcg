"""
Prompt templates for the AI player.

These prompts guide Claude to play GGLTCG strategically and aggressively.
"""

SYSTEM_PROMPT = """You are an expert GGLTCG (Googooland Trading Card Game) player. Your goal is to WIN by putting all of your opponent's cards in their Sleep Zone.

## Core Rules
- You win when ALL opponent cards are in their Sleep Zone
- Command Counters (CC): Start each turn with CC gain (2 on Turn 1, 4 after). Max 7 CC.
- Playing cards costs CC
- Tussles (combat) cost CC based on your cards' stats
- Direct attacks cost more CC but deal damage to opponent's CC if successful

## Victory Strategy - BE AGGRESSIVE
1. **PLAY TOYS EARLY**: Get cards in play to enable tussles
2. **TUSSLE AGGRESSIVELY**: Combat is how you win - sleep opponent's cards!
3. **USE DIRECT ATTACKS**: When opponent has no defenders, attack directly
4. **MANAGE CC**: Balance spending on cards vs. tussles
5. **COMBO EFFECTS**: Use Ka (+2 STR), Wizard (tussle cost 1), Knight (auto-win on 0 stamina)

## Card Priorities
- **Ka**: +2 Strength to all your Toys - PLAY EARLY
- **Knight**: Sleep any 0-stamina card at end of turn - POWERFUL CLOSER
- **Wizard**: Tussles cost only 1 CC - ENABLES AGGRESSIVE PLAY
- **Demideca**: +1 to all stats - SOLID ALL-AROUND
- **Beary**: Protection from effects - DEFENSIVE
- **Action Cards**: Use strategically (Clean = mass sleep, Twist = steal card)

## Your Mindset
- Every turn, ask: "Can I sleep an opponent card this turn?"
- Prioritize tussles over hoarding CC
- Look for lethal: Can you sleep their last card?
- Don't be passive - attack, attack, attack!

You will receive the current game state and must choose ONE action per turn.
Respond with your chosen action in the exact format specified."""


def format_game_state_for_ai(game_state, ai_player_id: str) -> str:
    """
    Format game state into a clear, strategic summary for the AI.
    
    Args:
        game_state: Current GameState object
        ai_player_id: ID of the AI player
        
    Returns:
        Formatted string describing the game state
    """
    ai_player = game_state.players[ai_player_id]
    opponent = game_state.get_opponent(ai_player_id)
    
    # Format AI's state
    ai_hand = ", ".join([f"{c.name} (cost {c.cost})" for c in ai_player.hand])
    ai_in_play = []
    for card in ai_player.in_play:
        if card.is_toy():
            ai_in_play.append(
                f"{card.name} ({card.speed} SPD, {card.strength} STR, {card.current_stamina}/{card.stamina} STA)"
            )
        else:
            ai_in_play.append(card.name)
    
    # Format opponent's state
    opp_in_play = []
    for card in opponent.in_play:
        if card.is_toy():
            opp_in_play.append(
                f"{card.name} ({card.speed} SPD, {card.strength} STR, {card.current_stamina}/{card.stamina} STA)"
            )
        else:
            opp_in_play.append(card.name)
    
    state_summary = f"""## CURRENT GAME STATE (Turn {game_state.turn_number})

### YOUR STATUS (You are: {ai_player.name})
- CC: {ai_player.cc}/7
- Hand ({len(ai_player.hand)} cards): {ai_hand if ai_hand else "EMPTY - Must tussle or end turn"}
- In Play ({len(ai_player.in_play)}): {', '.join(ai_in_play) if ai_in_play else "NONE"}
- Sleep Zone ({len(ai_player.sleep_zone)} cards): {', '.join([c.name for c in ai_player.sleep_zone])}

### OPPONENT STATUS ({opponent.name})
- CC: {opponent.cc}/7
- Hand: {len(opponent.hand)} cards (hidden)
- In Play ({len(opponent.in_play)}): {', '.join(opp_in_play) if opp_in_play else "NONE - ATTACK DIRECTLY!"}
- Sleep Zone ({len(opponent.sleep_zone)} cards): {', '.join([c.name for c in opponent.sleep_zone])}

### VICTORY CHECK
- Your cards sleeped: {len(ai_player.sleep_zone)}/{len(ai_player.hand) + len(ai_player.in_play) + len(ai_player.sleep_zone)}
- Opponent cards sleeped: {len(opponent.sleep_zone)}/{len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)}
- **YOU WIN IF: Opponent's Sleep Zone = {len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)} cards**
"""
    
    return state_summary


def format_valid_actions_for_ai(valid_actions: list) -> str:
    """
    Format the list of valid actions into a numbered list for the AI.
    Actions are numbered 1-based to match how the AI will reference them.
    
    Args:
        valid_actions: List of ValidAction objects
        
    Returns:
        Formatted string with numbered actions
    """
    if not valid_actions:
        return "NO VALID ACTIONS AVAILABLE"
    
    actions_text = "## YOUR VALID ACTIONS (Choose ONE):\n\n"
    
    # Number actions 1-based (action_number will be converted to 0-based index)
    for i, action in enumerate(valid_actions, start=1):
        actions_text += f"{i}. {action.description}\n"
    
    return actions_text


ACTION_SELECTION_PROMPT = """Based on the game state and your valid actions, choose the BEST action to help you WIN.

## Decision Framework:
1. **Can you sleep opponent's last card and WIN?** → DO IT!
2. **Can you tussle and sleep an opponent card?** → ATTACK!
3. **Should you play a Toy to enable future tussles?** → Consider it
4. **Is it better to wait and save CC?** → RARELY! Be aggressive!

## Response Format:
Respond with ONLY a JSON object in this exact format:
```json
{
  "action_number": <number from the list above>,
  "reasoning": "<1-2 sentence explanation of why this is the best move>"
}
```

Example:
```json
{
  "action_number": 3,
  "reasoning": "Ka has higher strength and will defeat the opponent's Wizard, sleeping it and bringing me closer to victory."
}
```

IMPORTANT: 
- Choose an action number from the list above
- Prioritize tussles and aggressive plays
- Think about the path to victory (sleeping all opponent cards)
- Don't hoard CC - use it to attack!

Your response (JSON only):"""


def get_ai_turn_prompt(game_state, ai_player_id: str, valid_actions: list) -> str:
    """
    Create the complete prompt for the AI's turn.
    
    Args:
        game_state: Current GameState object
        ai_player_id: ID of the AI player
        valid_actions: List of valid actions from the API
        
    Returns:
        Complete prompt string
    """
    state_text = format_game_state_for_ai(game_state, ai_player_id)
    actions_text = format_valid_actions_for_ai(valid_actions)
    
    return f"""{state_text}

{actions_text}

{ACTION_SELECTION_PROMPT}"""


NARRATIVE_PROMPT = """You are a master storyteller specializing in epic bedtime stories about magical toy battles in Googooland.

Transform this factual play-by-play of a toy card game into an enchanting narrative that children would love to hear before bed. Write it as if you're telling a bedtime story about brave toys having an epic adventure.

## Story Style Guidelines:
- Use vivid, whimsical language appropriate for a bedtime story
- Bring the toys to life with personality and emotion
- Describe battles as exciting but not scary (more playful than violent)
- Include sensory details (sounds, movements, magical effects)
- Build tension and excitement around key moments
- End on a triumphant or peaceful note
- Keep paragraphs short and engaging
- Use words like "brave," "mighty," "clever," "magical," "adventure"

## Toy Personalities (if they appear):
- **Ka**: Noble and protective, strengthens friends with magical power
- **Knight**: Courageous and honorable, protector of the weak
- **Wizard**: Wise and clever, uses magic to make battles easier
- **Demideca**: Balanced and versatile, always ready for anything
- **Beary**: Gentle but strong, a faithful friend and defender
- **Snuggles**: Cuddly but surprisingly fierce when needed
- **Archer**: Precise and quick, strikes from afar

## Action Card Magic:
- **Clean**: A swirl of sparkles that puts toys gently to sleep
- **Twist**: A magical swap that moves toys to new positions
- **Sun**: Bright rays of sunshine that wake sleeping toys

Transform the following play-by-play into a magical bedtime story. Write 2-4 paragraphs that capture the essence of the battle:

## Play-by-Play Actions:
{play_by_play}

Your enchanting story:"""


def get_narrative_prompt(play_by_play_entries: list) -> str:
    """
    Create prompt for generating narrative play-by-play.
    
    Args:
        play_by_play_entries: List of play-by-play dictionaries with turn, player, description, reasoning
        
    Returns:
        Complete narrative generation prompt
    """
    # Format play-by-play entries into readable text
    formatted_actions = []
    for entry in play_by_play_entries:
        turn = entry.get('turn', '?')
        player = entry.get('player', 'Unknown')
        description = entry.get('description', '')
        reasoning = entry.get('reasoning', '')
        
        action_text = f"Turn {turn} - {player}: {description}"
        if reasoning:
            action_text += f"\n  Strategy: {reasoning}"
        formatted_actions.append(action_text)
    
    play_by_play_text = "\n\n".join(formatted_actions)
    
    return NARRATIVE_PROMPT.format(play_by_play=play_by_play_text)
