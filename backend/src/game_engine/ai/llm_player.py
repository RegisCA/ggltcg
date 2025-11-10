"""
LLM-powered AI player using Claude or Gemini API.

This module implements an AI player that uses either Anthropic's Claude
or Google's Gemini to make strategic decisions in GGLTCG games.
"""

import json
import os
from typing import Optional, Dict, Any, Literal

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
            self.model_name = model or "gemini-2.0-flash-exp"
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
            return None
        
        # Build the prompt
        prompt = get_ai_turn_prompt(game_state, ai_player_id, valid_actions)
        
        try:
            # Call LLM API based on provider
            if self.provider == "anthropic":
                response_text = self._call_anthropic(prompt)
            else:  # gemini
                response_text = self._call_gemini(prompt)
            
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
            
            # Extract action number (1-based from prompt, convert to 0-based index)
            action_number = response_data.get("action_number")
            reasoning = response_data.get("reasoning", "No reasoning provided")
            
            if action_number is None:
                print(f"AI response missing action_number: {response_data}")
                return None
            
            # Convert to 0-based index
            action_index = action_number - 1
            
            # Validate index
            if action_index < 0 or action_index >= len(valid_actions):
                print(f"AI selected invalid action number {action_number} (max {len(valid_actions)})")
                return None
            
            # Log the decision
            selected_action = valid_actions[action_index]
            print(f"\n🤖 AI Decision (Turn {game_state.turn_number}) [{self.provider}]:")
            print(f"   Action: {selected_action.description}")
            print(f"   Reasoning: {reasoning}\n")
            
            return action_index
        
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            print(f"Response was: {response_text}")
            return None
        
        except Exception as e:
            print(f"Error getting AI decision: {e}")
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
        response = self.client.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1024,
            }
        )
        return response.text.strip()
    
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
