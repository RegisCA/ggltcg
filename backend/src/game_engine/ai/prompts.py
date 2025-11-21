"""
Prompt templates for the AI player.

These prompts guide Claude to play GGLTCG strategically and aggressively.
"""

# Card effect library for AI strategic understanding
CARD_EFFECTS_LIBRARY = {
    # TOY CARDS
    "Ka": {
        "type": "Toy",
        "effect": "Continuous: All your other Toys get +2 Strength",
        "strategic_use": "FORCE MULTIPLIER - Play early to boost all your attackers. Makes all your tussles stronger.",
        "threat_level": "HIGH - Boosts opponent's entire board if they control it"
    },
    "Knight": {
        "type": "Toy",
        "effect": "Triggered: At end of turn, sleep any card with 0 stamina",
        "strategic_use": "FINISHER - Automatically sleeps damaged cards at end of turn. Great follow-up after tussles.",
        "threat_level": "HIGH - Can sleep your damaged cards at opponent's end of turn"
    },
    "Wizard": {
        "type": "Toy",
        "effect": "Continuous: Your tussles cost only 1 CC (instead of stat-based)",
        "strategic_use": "ENABLES AGGRESSION - Makes tussling much cheaper. Play before tussling multiple times.",
        "threat_level": "MEDIUM - Opponent can tussle repeatedly with low CC cost"
    },
    "Demideca": {
        "type": "Toy",
        "effect": "Continuous: All your Toys get +1 Speed, +1 Strength, +1 Stamina",
        "strategic_use": "ALL-AROUND BOOST - Solid buff to everything. Good mid-game play.",
        "threat_level": "MEDIUM - Modest boost to opponent's board"
    },
    "Beary": {
        "type": "Toy",
        "effect": "Continuous: Cannot be targeted by Action cards",
        "strategic_use": "PROTECTION - Safe from Twist, Wake, Copy, Sun, etc. Good defensive anchor.",
        "threat_level": "LOW - Cannot be affected by your Action cards (but can still tussle it)"
    },
    "Snuggles": {
        "type": "Toy",
        "effect": "On Play: You may sleep one of your own Toys to gain +3 CC",
        "strategic_use": "CC GENERATOR - Sacrifice a weak toy for big CC boost. Use when desperate for CC.",
        "threat_level": "LOW - Unlikely to help opponent much"
    },
    "Ballaber": {
        "type": "Toy",
        "effect": "Alternative Cost: Instead of paying CC, you may sleep one of your Toys",
        "strategic_use": "FREE PLAY - Can play when low on CC by sacrificing another Toy. Good stats for free.",
        "threat_level": "LOW - Just a solid stat stick"
    },
    "Dream": {
        "type": "Toy",
        "effect": "On Play: Gain +2 CC",
        "strategic_use": "CC GENERATOR - Free CC boost when played. Always good value.",
        "threat_level": "LOW - Small CC boost for opponent"
    },
    "Archer": {
        "type": "Toy",
        "effect": "None (vanilla)",
        "strategic_use": "HIGH SPEED - Fast attacker, wins speed ties. Good early tussler.",
        "threat_level": "LOW - Just stats, no special abilities"
    },
    
    # ACTION CARDS
    "Clean": {
        "type": "Action",
        "effect": "Sleep all Toys (yours and opponent's)",
        "strategic_use": "BOARD WIPE - Use when opponent has more/stronger Toys than you. Reset the board.",
        "threat_level": "CRITICAL - Can sleep your entire board"
    },
    "Twist": {
        "type": "Action",
        "effect": "Target: Take control of an opponent's Toy (you become controller, not owner)",
        "strategic_use": "THEFT - Steal opponent's best Toy. Can swing the game decisively.",
        "threat_level": "CRITICAL - Can steal your best cards"
    },
    "Wake": {
        "type": "Action",
        "effect": "Target: Return a card from any Sleep Zone to its owner's hand",
        "strategic_use": "RECURSION - Get back your slept cards OR deny opponent's victory by waking their card.",
        "threat_level": "HIGH - Can undo your progress by waking slept cards"
    },
    "Copy": {
        "type": "Action",
        "effect": "Target: Create a copy of target Toy and put it in play under your control",
        "strategic_use": "CLONE - Duplicate your best Toy (Ka, Knight, Wizard) for massive value.",
        "threat_level": "HIGH - Can copy your best cards"
    },
    "Sun": {
        "type": "Action",
        "effect": "Target: Return up to 2 Toys from your Sleep Zone to your hand",
        "strategic_use": "MASS RECURSION - Get back multiple slept Toys. Great for recovery.",
        "threat_level": "HIGH - Opponent can recover multiple cards"
    },
}

SYSTEM_PROMPT = """You are an expert GGLTCG (Googooland Trading Card Game) player. Your goal is to WIN by putting all of your opponent's cards in their Sleep Zone.

## Core Rules
- You win when ALL opponent cards are in their Sleep Zone
- Command Counters (CC): Start each turn with CC gain (2 on Turn 1, 4 after). Max 7 CC.
- Playing cards costs CC
- Tussles (combat) cost CC based on your cards' stats
- Direct attacks cost more CC but deal damage to opponent's CC if successful

## Victory Strategy - BALANCED AGGRESSION
1. **ASSESS THE BOARD**: Before playing cards, evaluate opponent's threats
2. **BUILD STRATEGICALLY**: Don't just dump cards - think about synergies
3. **TUSSLE WHEN FAVORABLE**: Combat is how you win, but only when you can win
4. **DEFEND WHEN NEEDED**: Sometimes saving CC for defense is better than playing more cards
5. **COMBO EFFECTS**: Ka+attackers, Wizard+multiple tussles, Knight+damaged targets

## Strategic Decision Framework

### When to PLAY cards:
- You need enablers for tussles (can't tussle without Toys in play)
- You can play a force multiplier (Ka, Wizard, Demideca) that benefits multiple cards
- You have spare CC and opponent's board isn't threatening
- You can play an Action card that swings the game (Twist, Clean, Copy)

### When to NOT play more cards:
- Opponent has Ka/Demideca boosting their board (your cards will just get tussled)
- You're low on CC and might need it for crucial tussles
- Playing another card doesn't improve your win condition
- Opponent can use Twist/Copy to steal your cards

### When to TUSSLE:
- You can win the tussle (higher Strength, or equal Strength with higher Speed)
- Sleeping opponent's card brings you closer to victory
- You have Wizard in play (tussles cost only 1 CC)
- You have Knight in play (can finish off damaged targets at end of turn)

### When to DIRECT ATTACK:
- Opponent has NO Toys in play (free damage to their CC)
- Depleting opponent's CC can prevent them from playing threats
- You have excess CC and no better options

## Defensive Awareness

**Count opponent's potential attacks:**
- How many Toys do they have in play?
- What are their Strength values (boosted by Ka/Demideca)?
- Can they tussle and sleep YOUR cards this turn?
- Do they have CC for multiple tussles (check for Wizard)?

**Threat Assessment:**
- If opponent has Ka: All their Toys have +2 STR (very dangerous)
- If opponent has Wizard: They can tussle multiple times cheaply
- If opponent has Knight: Your damaged cards will auto-sleep at their end of turn
- If opponent has Action cards in hand: They might have Twist (steal), Clean (wipe), Copy (clone)

**When you're in DANGER (opponent has stronger board):**
- DON'T play more Toys that will just get slept
- SAVE CC for defensive tussles
- CONSIDER Action cards (Clean to reset board, Twist to steal their best card)
- LOOK for combo plays (play Ka then tussle, play Wizard then multi-tussle)

You will receive the current game state and must choose ONE action per turn.
Respond with your chosen action in the exact format specified."""


def format_game_state_for_ai(game_state, ai_player_id: str) -> str:
    """
    Format game state into a clear, strategic summary for the AI.
    Includes card effects and strategic analysis.
    
    Args:
        game_state: Current GameState object
        ai_player_id: ID of the AI player
        
    Returns:
        Formatted string describing the game state with strategic context
    """
    ai_player = game_state.players[ai_player_id]
    opponent = game_state.get_opponent(ai_player_id)
    
    # Format AI's hand with effect descriptions
    ai_hand_details = []
    for card in ai_player.hand:
        card_info = CARD_EFFECTS_LIBRARY.get(card.name, {})
        effect = card_info.get("effect", "Unknown effect")
        # Don't include strategic_use here - it will be shown in valid actions
        ai_hand_details.append(
            f"{card.name} (cost {card.cost}) - {effect}."
        )
    ai_hand = "\n    ".join(ai_hand_details) if ai_hand_details else "EMPTY - Must tussle or end turn"
    
    # Format AI's in-play cards
    ai_in_play = []
    for card in ai_player.in_play:
        if card.is_toy():
            ai_in_play.append(
                f"{card.name} ({card.speed} SPD, {card.strength} STR, {card.current_stamina}/{card.stamina} STA)"
            )
        else:
            ai_in_play.append(card.name)
    
    # Format opponent's in-play cards with threat analysis
    opp_in_play_details = []
    for card in opponent.in_play:
        if card.is_toy():
            card_info = CARD_EFFECTS_LIBRARY.get(card.name, {})
            threat = card_info.get("threat_level", "UNKNOWN")
            opp_in_play_details.append(
                f"{card.name} ({card.speed} SPD, {card.strength} STR, {card.current_stamina}/{card.stamina} STA) - THREAT: {threat}"
            )
        else:
            opp_in_play_details.append(card.name)
    opp_in_play = "\n    ".join(opp_in_play_details) if opp_in_play_details else "NONE - ATTACK DIRECTLY!"
    
    # Calculate board strength (total STR of all Toys in play)
    ai_total_str = sum(card.strength for card in ai_player.in_play if card.is_toy())
    opp_total_str = sum(card.strength for card in opponent.in_play if card.is_toy())
    
    # Determine board state
    if opp_total_str > ai_total_str + 3:
        board_state = "⚠️ OPPONENT DOMINATES - You are behind on board. Consider defensive plays or board wipes."
    elif ai_total_str > opp_total_str + 3:
        board_state = "✅ YOU DOMINATE - You have board advantage. Press your advantage with tussles."
    else:
        board_state = "⚖️ EVEN BOARD - Board state is balanced. Look for favorable tussles."
    
    state_summary = f"""## CURRENT GAME STATE (Turn {game_state.turn_number})

### YOUR STATUS (You are: {ai_player.name})
- CC: {ai_player.cc}/7
- Hand ({len(ai_player.hand)} cards):
    {ai_hand}
- In Play ({len(ai_player.in_play)}): {', '.join(ai_in_play) if ai_in_play else "NONE"}
- Sleep Zone ({len(ai_player.sleep_zone)} cards): {', '.join([c.name for c in ai_player.sleep_zone])}

### OPPONENT STATUS ({opponent.name})
- CC: {opponent.cc}/7
- Hand: {len(opponent.hand)} cards (hidden - could have Action cards!)
- In Play ({len(opponent.in_play)}):
    {opp_in_play}
- Sleep Zone ({len(opponent.sleep_zone)} cards): {', '.join([c.name for c in opponent.sleep_zone])}

### BOARD ANALYSIS
- Your Total Strength: {ai_total_str}
- Opponent Total Strength: {opp_total_str}
- {board_state}

### VICTORY CHECK
- Your cards sleeped: {len(ai_player.sleep_zone)}/{len(ai_player.hand) + len(ai_player.in_play) + len(ai_player.sleep_zone)}
- Opponent cards sleeped: {len(opponent.sleep_zone)}/{len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)}
- **YOU WIN IF: Opponent's Sleep Zone = {len(opponent.hand) + len(opponent.in_play) + len(opponent.sleep_zone)} cards**
"""
    
    return state_summary


def format_valid_actions_for_ai(valid_actions: list, game_state=None, ai_player_id: str = None) -> str:
    """
    Format the list of valid actions into a numbered list for the AI.
    Actions are numbered 1-based to match how the AI will reference them.
    Includes target options and strategic context.
    
    Args:
        valid_actions: List of ValidAction objects
        game_state: Optional GameState to look up card details
        ai_player_id: Optional player ID to identify AI's cards
        
    Returns:
        Formatted string with numbered actions and strategic context
    """
    if not valid_actions:
        return "NO VALID ACTIONS AVAILABLE"
    
    actions_text = "## YOUR VALID ACTIONS (Choose ONE):\n\n"
    
    # Helper to get card details with ID
    def get_card_details(card_id: str) -> tuple[str, str]:
        """Returns (display_name, actual_id) tuple"""
        if not game_state:
            return (card_id, card_id)
        # Search all zones for the card
        for player in game_state.players.values():
            for card in player.hand + player.in_play + player.sleep_zone:
                if card.id == card_id:
                    if card.is_toy():
                        display = f"{card.name} ({card.speed} SPD, {card.strength} STR, {card.current_stamina}/{card.stamina} STA)"
                    else:
                        display = card.name
                    return (display, card.id)
        return (card_id, card_id)
    
    # Number actions 1-based (action_number will be converted to 0-based index)
    for i, action in enumerate(valid_actions, start=1):
        action_text = f"{i}. {action.description}"
        
        # DEBUG: Log target_options for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Action {i} ({action.description}): target_options={action.target_options}, alt_cost={action.alternative_cost_options}")
        
        # Add target information if available
        if action.target_options is not None and len(action.target_options) > 0:
            if action.target_options == ["direct_attack"]:
                action_text += " [Direct attack - no defender]"
            else:
                target_details = []
                for target_id in action.target_options:
                    display_name, actual_id = get_card_details(target_id)
                    # Put the UUID first so LLM clearly sees it's the ID to use
                    target_details.append(f"[ID: {actual_id}] {display_name}")
                action_text += f"\n   Available targets (use the UUID from [ID: ...]):\n   - {'\n   - '.join(target_details)}"
        
        # Add alternative cost information if available
        if action.alternative_cost_options is not None and len(action.alternative_cost_options) > 0:
            alt_cost_details = []
            for alt_id in action.alternative_cost_options:
                display_name, actual_id = get_card_details(alt_id)
                # Put the UUID first so LLM clearly sees it's the ID to use
                alt_cost_details.append(f"[ID: {actual_id}] {display_name}")
            action_text += f"\n   Can pay alternative cost by sleeping (use the UUID from [ID: ...]):\n   - {'\n   - '.join(alt_cost_details)}"
        
        # Add strategic hint for card plays
        if action.action_type == "play_card" and action.card_id:
            # Try to find card name from action description
            for card_name in CARD_EFFECTS_LIBRARY.keys():
                if card_name in action.description:
                    card_info = CARD_EFFECTS_LIBRARY[card_name]
                    action_text += f"\n   → {card_info.get('strategic_use', '')}"
                    break
        
        actions_text += action_text + "\n"
    
    return actions_text


ACTION_SELECTION_PROMPT = """Based on the game state and your valid actions, choose the BEST action to help you WIN.

## Decision Framework:
1. **Can you sleep opponent's last card and WIN?** → DO IT IMMEDIATELY!
2. **Is opponent's board stronger than yours?** → Consider defensive plays (don't play more cards to get tussled)
3. **Can you tussle and sleep an opponent card?** → Attack if you'll win the tussle!
4. **Should you play a card?** → Only if it improves your position (force multiplier, enables combo, etc.)
5. **Is saving CC better?** → Yes if opponent has threatening board and you might need defensive tussles

## Response Format:
Respond with ONLY a JSON object in this exact format:
```json
{
  "action_number": <number from the list above>,
  "reasoning": "<1-2 sentence explanation of why this is the best move>",
  "target_id": "<card_id if action requires a target, otherwise null>",
  "alternative_cost_id": "<card_id if using alternative cost, otherwise null>"
}
```

Example 1 (Simple tussle):
```json
{
  "action_number": 3,
  "reasoning": "My Ka (8 STR) will defeat opponent's Wizard (5 STR), sleeping it and reducing their board advantage.",
  "target_id": null,
  "alternative_cost_id": null
}
```

Example 2 (Twist with target selection):
```json
{
  "action_number": 5,
  "reasoning": "Stealing opponent's Ka will swing the board in my favor - I'll gain +2 STR on my toys and they'll lose it.",
  "target_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "alternative_cost_id": null
}
```

Example 3 (Ballaber with alternative cost):
```json
{
  "action_number": 2,
  "reasoning": "I'm low on CC but need another attacker. Sleeping my damaged Archer to play Ballaber for free is good value.",
  "target_id": null,
  "alternative_cost_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210"
}
```

IMPORTANT:
- Choose an action number from the list above
- For target_id: Extract ONLY the UUID from inside [ID: ...], NEVER use the card name/stats that come after
- For alternative_cost_id: Extract ONLY the UUID from inside [ID: ...], NEVER use the card name/stats that come after
- Example: From "[ID: abc-123-def] Demideca (3 SPD, 2 STR, 3/3 STA)", use "abc-123-def" NOT "Demideca (3 SPD, 2 STR, 3/3 STA)"
- Use the FULL UUID string from the [ID: ...] brackets, NOT the card name or stats
- Think strategically - don't just play cards blindly
- Consider opponent's threats and board state
- Balance aggression with defense

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
    actions_text = format_valid_actions_for_ai(valid_actions, game_state, ai_player_id)
    
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
