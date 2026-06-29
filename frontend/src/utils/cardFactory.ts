/**
 * Card factory utilities for GGLTCG frontend.
 * 
 * Provides helper functions to create Card objects with proper defaults,
 * ensuring all required properties are included and preventing TypeScript errors.
 */

import type { Card } from '../types/game';
import type { CardDataResponse } from '../types/api';

/**
 * Create a Card object from API CardDataResponse.
 * 
 * Used for preview cards in deck selection and other UI components
 * that need to display card data before a game is started.
 * 
 * @param cardData - Card data from the API
 * @param idPrefix - Optional prefix for generated ID (default: 'preview')
 * @returns Complete Card object with all required properties
 */
export function createCardFromApiData(
  cardData: CardDataResponse,
  idPrefix: string = 'preview'
): Card {
  return {
    id: `${idPrefix}-${cardData.name}`,
    name: cardData.name,
    card_type: cardData.card_type,
    cost: cardData.cost,
    effective_cost: null,  // Preview cards don't have cost modifications
    effect_text: cardData.effect,
    zone: 'Hand',
    owner: '',
    controller: '',
    speed: cardData.speed,
    strength: cardData.strength,
    stamina: cardData.stamina,
    current_stamina: cardData.stamina,
    base_speed: cardData.speed,
    base_strength: cardData.strength,
    base_stamina: cardData.stamina,
    is_broken: false,
    primary_color: cardData.primary_color,
    accent_color: cardData.accent_color,
  };
}

