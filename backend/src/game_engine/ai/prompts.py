"""
Prompt templates for the AI player.

These prompts guide Claude/Gemini to play GGLTCG strategically and aggressively.

Version 2.0 Changes:
- Unified target_id to target_ids (array) for multi-target support (Sun card)
- Implemented Gemini structured output mode with JSON schema
- Restructured prompt with critical constraints at top
- Simplified decision framework from 5 to 3 core rules
- Added negative constraints (AVOID THESE MISTAKES)
- Added pre-response verification checklist
- Consolidated examples and added game-specific scenarios
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# Version tracking for AI decision logs
# Increment this when making significant changes to prompts or strategy
# Format: MAJOR.MINOR (MAJOR = strategy overhaul, MINOR = tweaks/fixes)
PROMPTS_VERSION = "2.0"


# ============================================================================
# JSON SCHEMA FOR STRUCTURED OUTPUT (Gemini native structured output mode)
# ============================================================================

class AIDecision(BaseModel):
    """
    Schema for AI player decisions.
    Uses Pydantic for Gemini's native structured output mode.
    """
    action_number: int = Field(
        ...,
        description="Action number from the valid actions list (1-indexed)",
        ge=1  # Must be >= 1
    )
    reasoning: str = Field(
        ...,
        description="1-2 sentence explanation of why this is the best move",
        max_length=200
    )
    target_ids: Optional[List[str]] = Field(
        default=None,
        description="Array of target card UUIDs. Use for targeting cards (Twist, Wake, Copy, Sun, tussles). Extract ONLY the UUID from [ID: xxx], never card names."
    )
    alternative_cost_id: Optional[str] = Field(
        default=None,
        description="UUID of card to sleep for alternative cost (Ballaber). Extract ONLY the UUID from [ID: xxx]."
    )


# Generate JSON Schema from Pydantic model for google-genai SDK
# The new SDK accepts standard JSON Schema via response_json_schema parameter
AI_DECISION_JSON_SCHEMA = AIDecision.model_json_schema()

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
}

SYSTEM_PROMPT = """You are an expert GGLTCG (Googooland Trading Card Game) player. Your goal is to WIN by putting all of your opponent's cards in their Sleep Zone.

## CRITICAL OUTPUT RULES (READ FIRST)
- Respond with ONLY valid JSON matching the schema
- action_number: Must be a number from the valid actions list (1 to N)
- target_ids: Array of UUIDs extracted from [ID: xxx] brackets. NEVER use card names or stats.
- alternative_cost_id: Single UUID from [ID: xxx] brackets (for Ballaber only)
- Example: From "[ID: abc-123-def] Demideca (3 SPD, 2 STR)" extract ONLY "abc-123-def"

## Core Rules
- You win when ALL opponent cards are in their Sleep Zone
- Command Counters (CC): Start each turn with CC gain (2 on Turn 1, 4 after). Max 7 CC.
- Playing cards costs CC
- Tussles (combat) cost CC (standard cost is 2 CC) and resolve based on cards' stats
- Direct attacks cost CC (standard cost is 2 CC) and sleep a random card from opponent's hand if they have no Toys in play.

## DECISION PRIORITY (Execute in Order)
1. **WIN CHECK**: Can you sleep opponent's last card this turn? → DO IT NOW!
2. **THREAT CHECK**: Is opponent's board stronger? → Play defensive (Action cards, save CC)
3. **VALUE CHECK**: Does playing/attacking improve your position? → Execute best move

## AVOID THESE MISTAKES
- DON'T play cards blindly - evaluate if they help your win condition
- DON'T attack into losing tussles (check STR vs STA, SPD for who strikes first)
- DON'T waste board wipes (Clean/Toynado) when you have the advantage
- DON'T use Sun to recover cards you can't afford to play
- DON'T forget to use both target slots for Sun (select 2 targets when available)

## Tussle Combat Rules
1. Compare YOUR STRENGTH vs THEIR STAMINA (NOT strength vs strength!)
2. Higher SPEED strikes first
3. If your STR >= their current STA AND you're faster → You win, they sleep
4. Knight auto-wins all tussles on your turn (ignore stats)

## Strategic Patterns
- **Ka + attackers**: +2 STR to all your Toys = more tussle wins
- **Wizard + multiple tussles**: 1 CC per tussle instead of 2 CC
- **Wake then Sun**: Wake a card first, then Sun can recover it + 2 more (3 total!)
- **Toynado vs Twist**: If opponent stole your card, Toynado returns it to YOUR hand

You will receive the current game state and must choose ONE action per turn."""


def format_game_state_for_ai(game_state, ai_player_id: str, game_engine=None) -> str:
    """
    Format game state into a clear, strategic summary for the AI.
    Includes card effects and strategic analysis.
    
    Args:
        game_state: Current GameState object
        ai_player_id: ID of the AI player
        game_engine: Optional GameEngine for calculating effective stats with continuous effects
        
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
            if game_engine:
                # Use GameEngine to get stats with continuous effects (Ka, Demideca, etc.)
                spd = game_engine.get_card_stat(card, "speed")
                str_val = game_engine.get_card_stat(card, "strength")
                cur_sta = game_engine.get_effective_stamina(card)
                max_sta = game_engine.get_card_stat(card, "stamina")
            else:
                # Fallback to card methods (won't include continuous effects)
                spd = card.get_effective_speed()
                str_val = card.get_effective_strength()
                cur_sta = card.get_effective_stamina()
                max_sta = card.stamina + card.modifications.get("stamina", 0)
            ai_in_play.append(
                f"{card.name} ({spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA)"
            )
        else:
            ai_in_play.append(card.name)
    
    # Format opponent's in-play cards with threat analysis
    opp_in_play_details = []
    for card in opponent.in_play:
        if card.is_toy():
            card_info = CARD_EFFECTS_LIBRARY.get(card.name, {})
            threat = card_info.get("threat_level", "UNKNOWN")
            if game_engine:
                # Use GameEngine to get stats with continuous effects (Ka, Demideca, etc.)
                spd = game_engine.get_card_stat(card, "speed")
                str_val = game_engine.get_card_stat(card, "strength")
                cur_sta = game_engine.get_effective_stamina(card)
                max_sta = game_engine.get_card_stat(card, "stamina")
            else:
                # Fallback to card methods (won't include continuous effects)
                spd = card.get_effective_speed()
                str_val = card.get_effective_strength()
                cur_sta = card.get_effective_stamina()
                max_sta = card.stamina + card.modifications.get("stamina", 0)
            opp_in_play_details.append(
                f"{card.name} ({spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA) - THREAT: {threat}"
            )
        else:
            opp_in_play_details.append(card.name)
    opp_in_play = "\n    ".join(opp_in_play_details) if opp_in_play_details else "NONE - ATTACK DIRECTLY!"
    
    # Calculate board strength (total STR of all Toys in play)
    if game_engine:
        ai_total_str = sum(game_engine.get_card_stat(card, "strength") for card in ai_player.in_play if card.is_toy())
        opp_total_str = sum(game_engine.get_card_stat(card, "strength") for card in opponent.in_play if card.is_toy())
    else:
        ai_total_str = sum(card.get_effective_strength() for card in ai_player.in_play if card.is_toy())
        opp_total_str = sum(card.get_effective_strength() for card in opponent.in_play if card.is_toy())
    
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


def format_valid_actions_for_ai(valid_actions: list, game_state=None, ai_player_id: str = None, game_engine=None) -> str:
    """
    Format the list of valid actions into a numbered list for the AI.
    Actions are numbered 1-based to match how the AI will reference them.
    Includes target options and strategic context.
    
    Args:
        valid_actions: List of ValidAction objects
        game_state: Optional GameState to look up card details
        ai_player_id: Optional player ID to identify AI's cards
        game_engine: Optional GameEngine for calculating effective stats with continuous effects
        
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
                        if game_engine:
                            # Use GameEngine to get stats with continuous effects
                            spd = game_engine.get_card_stat(card, "speed")
                            str_val = game_engine.get_card_stat(card, "strength")
                            cur_sta = game_engine.get_effective_stamina(card)
                            max_sta = game_engine.get_card_stat(card, "stamina")
                        else:
                            # Fallback to card methods
                            spd = card.get_effective_speed()
                            str_val = card.get_effective_strength()
                            cur_sta = card.get_effective_stamina()
                            max_sta = card.stamina + card.modifications.get("stamina", 0)
                        display = f"{card.name} ({spd} SPD, {str_val} STR, {cur_sta}/{max_sta} STA)"
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
        logger.debug(f"Action {i} ({action.description}): target_options={action.target_options}, alt_cost={action.alternative_cost_options}, max_targets={action.max_targets}")
        
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
                # Format targets list (extract join logic to avoid backslash in f-string)
                targets_list = '\n   - '.join(target_details)
                
                # Indicate multi-target selection when max_targets > 1 (e.g., Sun)
                max_targets = getattr(action, 'max_targets', 1) or 1
                if max_targets > 1:
                    action_text += f"\n   Select up to {max_targets} targets (add UUIDs to target_ids array):\n   - {targets_list}"
                else:
                    action_text += f"\n   Available targets (use the UUID from [ID: ...]):\n   - {targets_list}"
        
        # Add alternative cost information if available
        if action.alternative_cost_options is not None and len(action.alternative_cost_options) > 0:
            alt_cost_details = []
            for alt_id in action.alternative_cost_options:
                display_name, actual_id = get_card_details(alt_id)
                # Put the UUID first so LLM clearly sees it's the ID to use
                alt_cost_details.append(f"[ID: {actual_id}] {display_name}")
            # Format alternative cost list (extract join logic to avoid backslash in f-string)
            alt_cost_list = '\n   - '.join(alt_cost_details)
            action_text += f"\n   Can pay alternative cost by sleeping (use the UUID from [ID: ...]):\n   - {alt_cost_list}"
        
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


ACTION_SELECTION_PROMPT = """Based on the game state and your valid actions, choose the BEST action to WIN.

## EXAMPLE SCENARIOS

**Scenario A - Recovery with Sun:**
You have Sun in hand, 3 cards in sleep zone (Ka, Knight, Demideca).
- GOOD: Play Sun targeting Ka AND Knight (recover 2 strong Toys)
- BAD: Play Sun but only select 1 target when 2 are available (wasted value)

**Scenario B - Win Condition:**
Opponent at 4/5 slept, you can attack. → Attack immediately to WIN!

**Scenario C - Defensive:**  
Opponent has 12 total STR, you have 4. You're at 2/5 slept.
→ Play Toynado to reset, survive another turn.

## BEFORE RESPONDING - VERIFY:
✓ action_number matches an option from the list (1 to N)
✓ target_ids contains ONLY UUIDs from [ID: xxx], not card names
✓ For Sun: Did you select 2 targets if available?
✓ reasoning addresses win condition

Your response (JSON only):"""


def get_ai_turn_prompt(game_state, ai_player_id: str, valid_actions: list, game_engine=None) -> str:
    """
    Create the complete prompt for the AI's turn.
    
    Args:
        game_state: Current GameState object
        ai_player_id: ID of the AI player
        valid_actions: List of valid actions from the API
        game_engine: Optional GameEngine for calculating effective stats with continuous effects
        
    Returns:
        Complete prompt string
    """
    state_text = format_game_state_for_ai(game_state, ai_player_id, game_engine)
    actions_text = format_valid_actions_for_ai(valid_actions, game_state, ai_player_id, game_engine)
    
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
