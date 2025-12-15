/**
 * Card factory utilities for GGLTCG frontend.
 * 
 * Provides helper functions to create Card objects with proper defaults,
 * ensuring all required properties are included and preventing TypeScript errors.
 */

import type { Card, CardType, Zone } from '../types/game';
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
    is_sleeped: false,
    primary_color: cardData.primary_color,
    accent_color: cardData.accent_color,
  };
}

/**
 * Create a minimal Card object for testing or placeholders.
 * 
 * @param name - Card name
 * @param cardType - Card type ('Toy' or 'Action')
 * @param cost - Card cost
 * @param overrides - Optional property overrides
 * @returns Complete Card object
 */
export function createTestCard(
  name: string,
  cardType: CardType,
  cost: number,
  overrides: Partial<Card> = {}
): Card {
  const isToy = cardType === 'Toy';
  
  return {
    id: `test-${name}-${Date.now()}`,
    name,
    card_type: cardType,
    cost,
    effective_cost: null,
    effect_text: '',
    zone: 'Hand',
    owner: 'test-player',
    controller: 'test-player',
    speed: isToy ? 1 : null,
    strength: isToy ? 1 : null,
    stamina: isToy ? 1 : null,
    current_stamina: isToy ? 1 : null,
    base_speed: isToy ? 1 : null,
    base_strength: isToy ? 1 : null,
    base_stamina: isToy ? 1 : null,
    is_sleeped: false,
    primary_color: '#888888',
    accent_color: '#888888',
    ...overrides,
  };
}

/**
 * Create a Card object with zone-specific defaults.
 * 
 * @param baseCard - Base card properties
 * @param zone - Target zone for the card
 * @returns Card with zone-appropriate properties
 */
export function createCardInZone(
  baseCard: Omit<Card, 'zone' | 'is_sleeped'>,
  zone: Zone
): Card {
  return {
    ...baseCard,
    zone,
    is_sleeped: zone === 'Sleep',
  };
}

/**
 * Update a Card's effective cost.
 * 
 * Helper for updating cost display when Gibbers or Dream effects apply.
 * 
 * @param card - Card to update
 * @param effectiveCost - New effective cost (null if same as base)
 * @returns New Card object with updated effective_cost
 */
export function withEffectiveCost(card: Card, effectiveCost: number | null): Card {
  return {
    ...card,
    effective_cost: effectiveCost === card.cost ? null : effectiveCost,
  };
}
