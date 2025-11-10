"""
LLM-powered AI player using Claude or Gemini API.

This module implements an AI player that uses either Anthropic's Claude
or Google's Gemini to make strategic decisions in GGLTCG games.
"""

import json
import os
import logging
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

from .prompts import SYSTEM_PROMPT, get_ai_turn_prompt
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
            # Use gemini-2.0-flash-lite for best free tier quotas (30 RPM, 1M TPM, 1.5K RPD)
            # This allows ~7-8 actions per minute, plenty for gameplay testing
            # Alternative: gemini-2.5-flash (10 RPM) if we need smarter AI
            self.model_name = model or "gemini-2.0-flash-lite"
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
        valid_actions: list[ValidAction]
    ) -> Optional[int]:
        """
        Use LLM to select the best action from valid options.
        
        Args:
            game_state: Current game state
            ai_player_id: ID of the AI player
            valid_actions: List of valid actions the AI can take
            
        Returns:
            Index of selected action in valid_actions list (0-based),
            or None if selection failed
        """
        if not valid_actions:
            logger.warning("No valid actions available for AI")
            return None
        
        logger.info(f"🤖 AI Turn {game_state.turn_number} - {len(valid_actions)} actions available")
        
        # Build the prompt
        prompt = get_ai_turn_prompt(game_state, ai_player_id, valid_actions)
        
        logger.debug(f"AI Prompt:\n{prompt}")
        
        try:
            # Call LLM API based on provider
            logger.info(f"Calling {self.provider} API ({self.model_name if self.provider == 'gemini' else self.model})...")
            
            if self.provider == "anthropic":
                response_text = self._call_anthropic(prompt)
            else:  # gemini
                response_text = self._call_gemini(prompt)
            
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
            
            if action_number is None:
                logger.error(f"AI response missing action_number: {response_data}")
                return None
            
            # Convert to 0-based index
            action_index = action_number - 1
            
            # Validate index
            if action_index < 0 or action_index >= len(valid_actions):
                logger.error(f"AI selected invalid action number {action_number} (max {len(valid_actions)})")
                return None
            
            # Log the decision
            selected_action = valid_actions[action_index]
            logger.info(f"✅ AI Decision: {selected_action.description}")
            logger.info(f"💭 Reasoning: {reasoning}")
            
            return action_index
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return None
        
        except Exception as e:
            logger.exception(f"Error getting AI decision: {e}")
            return None
    
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
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API."""
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
                    "This may be due to safety filters or rate limits. Try again or adjust the prompt."
                )
            
            result = response.text.strip()
            logger.debug(f"Gemini response length: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.exception(f"Gemini API call failed: {e}")
            raise
    
    def get_action_details(
        self,
        selected_action: ValidAction
    ) -> Dict[str, Any]:
        """
        Convert a ValidAction into the request parameters needed for the API.
        
        Args:
            selected_action: The action selected by the AI
            
        Returns:
            Dictionary with request parameters for the API endpoint
        """
        result: Dict[str, Any] = {}
        
        if selected_action.action_type == "play_card":
            result["action_type"] = "play_card"
            result["card_name"] = selected_action.card_name
            # Note: For cards requiring targets, we'd need additional logic
            # For MVP, assuming simple cards or random target selection
        
        elif selected_action.action_type == "tussle":
            result["action_type"] = "tussle"
            result["attacker_name"] = selected_action.card_name
            
            # Check if this is a direct attack or targeted tussle
            if selected_action.target_options and selected_action.target_options[0] != "direct_attack":
                result["defender_name"] = selected_action.target_options[0]
            else:
                result["defender_name"] = None  # Direct attack
        
        elif selected_action.action_type == "end_turn":
            result["action_type"] = "end_turn"
        
        return result


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
