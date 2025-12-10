"""
LLM-powered AI player using Claude or Gemini API.

This module implements an AI player that uses either Anthropic's Claude
or Google's Gemini to make strategic decisions in GGLTCG games.
"""

import json
import os
import logging
import time
from typing import Optional, Dict, Any, Literal
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env in backend directory
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # python-dotenv is optional

from .prompts import SYSTEM_PROMPT, get_ai_turn_prompt, PROMPTS_VERSION
from game_engine.models.game_state import GameState
from api.schemas import ValidAction


class LLMPlayer:
    """
    AI player powered by LLM API (Claude or Gemini).
    
    Uses an LLM to analyze game state and select optimal actions.
    """
    
    def __init__(
        self,
        provider: Literal["anthropic", "gemini"] = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the AI player.
        
        Args:
            provider: LLM provider to use ("anthropic" or "gemini")
            api_key: API key (reads from env var if not provided)
            model: Model to use (provider-specific defaults if not provided)
        """
        self.provider = provider
        
        # Store last target/alternative cost selections from LLM
        self._last_target_id: Optional[str] = None
        self._last_alternative_cost_id: Optional[str] = None
        
        # Store last prompt/response for logging
        self._last_prompt: Optional[str] = None
        self._last_response: Optional[str] = None
        self._last_action_number: Optional[int] = None
        self._last_reasoning: Optional[str] = None
        
        if provider == "anthropic":
            from anthropic import Anthropic
            
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                    "or pass api_key parameter."
                )
            
            self.client = Anthropic(api_key=self.api_key)
            self.model = model or "claude-sonnet-4-20250514"
        
        elif provider == "gemini":
            import google.generativeai as genai
            
            self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "Google API key required. Set GOOGLE_API_KEY environment variable "
                    "or pass api_key parameter. Get a free key at: "
                    "https://aistudio.google.com/apikey"
                )
            
            genai.configure(api_key=self.api_key)
            
            # Allow model override via environment variable or parameter
            # Default: gemini-2.0-flash-lite (30 RPM, best free tier quotas)
            # Alternative: gemini-2.5-flash (15 RPM, more stable, better capacity)
            # Alternative: gemini-2.0-flash (10 RPM, stable)
            default_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
            self.model_name = model or default_model
            
            # Fallback model for capacity issues (configurable via env var)
            # Default: gemini-2.5-flash-lite (15 RPM, better capacity availability)
            self.fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-lite")
            
            logger.info(f"Initializing Gemini with model: {self.model_name}")
            logger.info(f"Fallback model (for 429 errors): {self.fallback_model}")
            
            self.client = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPT
            )
        
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'anthropic' or 'gemini'")
    
    def select_action(
        self,
        game_state: GameState,
        ai_player_id: str,
        valid_actions: list[ValidAction],
        game_engine=None
    ) -> Optional[tuple[int, str]]:
        """
        Use LLM to select the best action from valid options.
        
        Args:
            game_state: Current game state
            ai_player_id: ID of the AI player
            valid_actions: List of valid actions the AI can take
            game_engine: Optional GameEngine for calculating effective stats
            
        Returns:
            Tuple of (action_index, reasoning) where action_index is 0-based,
            or None if selection failed
        """
        if not valid_actions:
            logger.warning("No valid actions available for AI")
            return None
        
        logger.info(f"🤖 AI Turn {game_state.turn_number} - {len(valid_actions)} actions available")
        
        # Build the prompt
        prompt = get_ai_turn_prompt(game_state, ai_player_id, valid_actions, game_engine)
        
        # Store prompt for logging
        self._last_prompt = prompt
        self._last_response = None
        self._last_action_number = None
        self._last_reasoning = None
        
        logger.debug(f"AI Prompt:\n{prompt}")
        
        try:
            # Call LLM API based on provider
            logger.info(f"Calling {self.provider} API ({self.model_name if self.provider == 'gemini' else self.model})...")
            
            if self.provider == "anthropic":
                response_text = self._call_anthropic(prompt)
            else:  # gemini
                response_text = self._call_gemini(prompt)
            
            # Store raw response for logging
            self._last_response = response_text
            
            logger.debug(f"Raw API Response:\n{response_text}")
            
            # Parse JSON response
            # Handle markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            response_data = json.loads(response_text)
            logger.debug(f"Parsed JSON: {response_data}")
            
            # Extract action number (1-based from prompt, convert to 0-based index)
            action_number = response_data.get("action_number")
            reasoning = response_data.get("reasoning", "No reasoning provided")
            target_id = response_data.get("target_id")
            alternative_cost_id = response_data.get("alternative_cost_id")
            
            # Normalize string "null" to actual None
            # Some LLMs return the string "null" instead of null/None
            if target_id == "null" or target_id == "None":
                target_id = None
            if alternative_cost_id == "null" or alternative_cost_id == "None":
                alternative_cost_id = None
            
            # DEBUG: Log all actions with their numbers
            logger.info("=" * 60)
            logger.info("DEBUG - Valid Actions List:")
            for i, action in enumerate(valid_actions):
                logger.info(f"  Prompt number {i+1} -> Index {i}: {action.description}")
            logger.info("=" * 60)
            
            if action_number is None:
                logger.error(f"AI response missing action_number: {response_data}")
                return None
            
            logger.info(f"DEBUG - AI returned action_number: {action_number} (type: {type(action_number)})")
            
            # Convert to 0-based index
            action_index = action_number - 1
            logger.info(f"DEBUG - Converted to action_index: {action_index}")
            
            # Validate index
            if action_index < 0 or action_index >= len(valid_actions):
                logger.error(f"AI selected invalid action number {action_number} (max {len(valid_actions)})")
                return None
            
            # Log the decision
            selected_action = valid_actions[action_index]
            logger.info(f"✅ AI Decision: {selected_action.description}")
            logger.info(f"💭 Reasoning: {reasoning}")
            if target_id:
                logger.info(f"🎯 Target: {target_id}")
            if alternative_cost_id:
                logger.info(f"💰 Alternative Cost: {alternative_cost_id}")
            logger.info(f"DEBUG - Returning action_index: {action_index}")
            logger.info("=" * 60)
            
            # Store target and alternative cost selections
            self._last_target_id = target_id
            self._last_alternative_cost_id = alternative_cost_id
            
            # Store parsed action data for logging
            self._last_action_number = action_number
            self._last_reasoning = reasoning
            
            return (action_index, reasoning)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return None
        
        except Exception as e:
            logger.exception(f"Error getting AI decision: {e}")
            return None
    
    def get_last_decision_info(self) -> Dict[str, Any]:
        """
        Get information about the last AI decision for logging.
        
        Returns:
            Dict containing prompt, response, model info, and parsed action data
        """
        return {
            "prompt": self._last_prompt,
            "response": self._last_response,
            "model_name": self.model_name if self.provider == "gemini" else self.model,
            "prompts_version": PROMPTS_VERSION,
            "action_number": self._last_action_number,
            "reasoning": self._last_reasoning,
        }
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
        )
        return message.content[0].text.strip()
    
    def _call_gemini(self, prompt: str, retry_count: int = 3, allow_fallback: bool = True) -> str:
        """
        Call Google Gemini API with retry logic and automatic fallback to more stable models.
        
        Args:
            prompt: The prompt to send
            retry_count: Number of retries for 429 errors (default: 3)
            allow_fallback: Whether to fallback to GEMINI_FALLBACK_MODEL on capacity issues (default: True)
            
        Returns:
            The API response text
            
        Raises:
            Exception if all retries and fallbacks fail
        """
        last_exception = None
        current_model = self.model_name
        
        for attempt in range(retry_count):
            try:
                response = self.client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 1024,
                    }
                )
                
                # Log response metadata for debugging
                logger.debug(f"Gemini response candidates: {len(response.candidates) if response.candidates else 0}")
                
                # Check if response was blocked or empty
                if not response.candidates or not response.candidates[0].content.parts:
                    finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                    safety_ratings = response.candidates[0].safety_ratings if response.candidates else []
                    
                    logger.error(f"Gemini returned empty response")
                    logger.error(f"Finish reason: {finish_reason}")
                    logger.error(f"Safety ratings: {safety_ratings}")
                    
                    raise ValueError(
                        f"Gemini returned empty response (finish_reason: {finish_reason}). "
                        "This may be due to safety filters. Try again or adjust the prompt."
                    )
                
                result = response.text.strip()
                logger.debug(f"Gemini response length: {len(result)} characters")
                return result
                
            except Exception as e:
                error_str = str(e)
                last_exception = e
                
                # Check if it's a 429 Resource Exhausted error
                if "429" in error_str or "ResourceExhausted" in error_str or "Resource exhausted" in error_str:
                    if attempt < retry_count - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"Gemini API capacity issue (429 Resource Exhausted). "
                            f"Retry {attempt + 1}/{retry_count} after {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        # All retries exhausted - try fallback model if enabled
                        if allow_fallback and current_model != self.fallback_model:
                            logger.warning(
                                f"Gemini {current_model} capacity exhausted after {retry_count} retries. "
                                f"Falling back to {self.fallback_model} (more stable, better availability)..."
                            )
                            # Switch to fallback model
                            import google.generativeai as genai
                            self.model_name = self.fallback_model
                            self.client = genai.GenerativeModel(
                                model_name=self.fallback_model,
                                system_instruction=SYSTEM_PROMPT
                            )
                            # Try one more time with fallback model
                            return self._call_gemini(prompt, retry_count=1, allow_fallback=False)
                        else:
                            logger.error(
                                f"Gemini API capacity exhausted after {retry_count} retries. "
                                f"This is a Google infrastructure issue, not a rate limit. "
                                f"Consider: 1) Try again in a few minutes, 2) Use Anthropic Claude instead"
                            )
                else:
                    # Not a 429 error, don't retry
                    logger.exception(f"Gemini API call failed: {e}")
                
                raise last_exception
        
        # If we get here, all retries failed
        raise last_exception
    
    def get_action_details(
        self,
        selected_action: ValidAction
    ) -> Dict[str, Any]:
        """
        Convert a ValidAction into the request parameters needed for the API.
        Uses target_id and alternative_cost_id from the last LLM response.
        
        Args:
            selected_action: The action selected by the AI
            
        Returns:
            Dictionary with request parameters for the API endpoint
        """
        result: Dict[str, Any] = {}
        
        if selected_action.action_type == "play_card":
            result["action_type"] = "play_card"
            result["card_id"] = selected_action.card_id
            
            # Handle target selection (for cards like Twist, Wake, Copy, Sun)
            if self._last_target_id:
                result["target_id"] = self._last_target_id
                logger.info(f"Using AI-selected target: {self._last_target_id}")
            elif selected_action.target_options:
                # Fallback: Use first available target if AI didn't specify
                result["target_id"] = selected_action.target_options[0]
                logger.warning(f"AI didn't specify target, using first option: {result['target_id']}")
            
            # Handle alternative cost (for Ballaber)
            if self._last_alternative_cost_id:
                result["alternative_cost_card_id"] = self._last_alternative_cost_id
                logger.info(f"Using AI-selected alternative cost: {self._last_alternative_cost_id}")
            elif selected_action.alternative_cost_options and len(selected_action.alternative_cost_options) > 0:
                # Fallback: Use first available alternative cost card if AI didn't specify
                result["alternative_cost_card_id"] = selected_action.alternative_cost_options[0]
                logger.warning(f"AI didn't specify alternative cost, using first option: {result['alternative_cost_card_id']}")
        
        elif selected_action.action_type == "tussle":
            result["action_type"] = "tussle"
            result["attacker_id"] = selected_action.card_id
            
            # Handle target selection for tussles
            if self._last_target_id:
                result["defender_id"] = self._last_target_id
                logger.info(f"Using AI-selected tussle target: {self._last_target_id}")
            elif selected_action.target_options:
                # Check if this is a direct attack or targeted tussle
                if selected_action.target_options[0] == "direct_attack":
                    result["defender_id"] = None  # Direct attack
                else:
                    result["defender_id"] = selected_action.target_options[0]
                    logger.warning(f"AI didn't specify tussle target, using first option: {result['defender_id']}")
            else:
                result["defender_id"] = None  # Direct attack
        
        elif selected_action.action_type == "activate_ability":
            result["action_type"] = "activate_ability"
            result["card_id"] = selected_action.card_id
            result["amount"] = 1  # Always use 1 for now (can be repeated)
            
            # Handle target selection for activated abilities
            if self._last_target_id:
                result["target_id"] = self._last_target_id
                logger.info(f"Using AI-selected ability target: {self._last_target_id}")
            elif selected_action.target_options:
                # Fallback: Use first available target if AI didn't specify
                result["target_id"] = selected_action.target_options[0]
                logger.warning(f"AI didn't specify ability target, using first option: {result['target_id']}")
        
        elif selected_action.action_type == "end_turn":
            result["action_type"] = "end_turn"
        
        # Clear stored selections after use
        self._last_target_id = None
        self._last_alternative_cost_id = None
        
        return result
    
    def get_endpoint_name(self) -> str:
        """
        Get a human-readable name for the AI endpoint being used.
        
        Returns:
            String like "Gemini 2.0 Flash Lite" or "Claude Sonnet 4"
        """
        if self.provider == "anthropic":
            # Map model names to friendly names
            model_map = {
                "claude-sonnet-4-20250514": "Claude Sonnet 4",
                "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
                "claude-3-opus-20240229": "Claude 3 Opus",
            }
            return model_map.get(self.model, f"Claude ({self.model})")
        else:  # gemini
            # Map Gemini models to friendly names
            model_map = {
                "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
                "gemini-2.0-flash-exp": "Gemini 2.0 Flash (Experimental)",
                "gemini-1.5-flash": "Gemini 1.5 Flash",
                "gemini-1.5-pro": "Gemini 1.5 Pro",
            }
            return model_map.get(self.model_name, f"Gemini ({self.model_name})")


# Singleton instance
_ai_player: Optional[LLMPlayer] = None


def get_ai_player(provider: str = None) -> LLMPlayer:
    """
    Get the singleton AI player instance.
    
    Args:
        provider: Optional provider override ("anthropic" or "gemini")
    
    Returns:
        LLMPlayer instance
    """
    global _ai_player
    
    # Determine provider from environment or default to Gemini (free tier)
    if provider is None:
        provider = os.getenv("AI_PROVIDER", "gemini")
    
    if _ai_player is None:
        _ai_player = LLMPlayer(provider=provider)
    return _ai_player


def get_llm_response(prompt: str, is_json: bool = True, provider: str = None) -> str:
    """
    Get a response from the LLM for a custom prompt.
    
    This is a utility function for getting LLM responses outside of game action selection,
    such as generating narratives or other creative text.
    
    Args:
        prompt: The prompt to send to the LLM
        is_json: Whether to expect and parse JSON response (default: True)
        provider: Optional provider override ("anthropic" or "gemini")
    
    Returns:
        The LLM response text (parsed from JSON if is_json=True)
    """
    ai_player = get_ai_player(provider)
    
    # Call the appropriate LLM
    if ai_player.provider == "anthropic":
        # For Anthropic, we need to call without system prompt for custom prompts
        from anthropic import Anthropic
        client = Anthropic(api_key=ai_player.api_key)
        message = client.messages.create(
            model=ai_player.model,
            max_tokens=2048,  # Allow longer responses for narratives
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,  # Higher temperature for more creative narratives
        )
        response_text = message.content[0].text.strip()
    else:  # gemini
        import google.generativeai as genai
        # Create a new model instance without system instruction for custom prompts
        model = genai.GenerativeModel(model_name=ai_player.model_name)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.8,  # Higher temperature for creativity
                "max_output_tokens": 2048,  # Allow longer responses
            }
        )
        response_text = response.text.strip()
    
    if is_json:
        # Parse JSON response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        return json.loads(response_text)
    
    return response_text
