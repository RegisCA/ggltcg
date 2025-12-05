/**
 * Deck Selection Component
 * Allows players to select 6 unique cards for their deck
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { CardDisplay } from './CardDisplay';
import { getRandomDeck, getAllCards } from '../api/gameService';
import type { Card } from '../types/game';
import type { CardDataResponse } from '../types/api';

interface DeckSelectionProps {
  onDeckSelected: (deck: string[], playerName: string) => void;
  hiddenMode?: boolean;  // When true, cards are face-down and only random selection works
  defaultPlayerName?: string;  // Override the default player name (for AI player)
}

export function DeckSelection({ onDeckSelected, hiddenMode = false, defaultPlayerName }: DeckSelectionProps) {
  const { user } = useAuth();
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [numToys, setNumToys] = useState(4); // Default: 4 Toys
  const [numActions, setNumActions] = useState(2); // Default: 2 Actions
  const [isRandomizing, setIsRandomizing] = useState(false);
  const [cards, setCards] = useState<CardDataResponse[]>([]);
  const [isLoadingCards, setIsLoadingCards] = useState(true);

  // Use provided default name, or get display name from authenticated user
  const playerName = defaultPlayerName || user?.display_name || 'Player';

  // Load cards from backend on mount
  useEffect(() => {
    getAllCards()
      .then((cardData) => {
        setCards(cardData);
        setIsLoadingCards(false);
      })
      .catch((error) => {
        console.error('Failed to load cards:', error);
        alert('Failed to load card database. Please refresh the page.');
        setIsLoadingCards(false);
      });
  }, []);

  const toggleCard = (cardName: string) => {
    if (selectedCards.includes(cardName)) {
      setSelectedCards(selectedCards.filter((name) => name !== cardName));
    } else if (selectedCards.length < 6) {
      setSelectedCards([...selectedCards, cardName]);
    }
  };

  const handleSliderChange = (newNumToys: number) => {
    // Ensure sum equals 6
    const newNumActions = 6 - newNumToys;
    setNumToys(newNumToys);
    setNumActions(newNumActions);
  };

  const handleRandomize = async () => {
    setIsRandomizing(true);
    try {
      const randomDeck = await getRandomDeck(numToys, numActions);
      setSelectedCards(randomDeck);
    } catch (error) {
      console.error('Failed to get random deck:', error);
      alert('Failed to generate random deck. Please try again.');
    } finally {
      setIsRandomizing(false);
    }
  };

  const handleConfirm = () => {
    if (selectedCards.length === 6) {
      onDeckSelected(selectedCards, playerName);
    }
  };

  // Convert CardDataResponse to Card for display
  const createCardForDisplay = (cardData: CardDataResponse): Card => ({
    id: `preview-${cardData.name}`,  // Temporary ID for preview cards
    name: cardData.name,
    card_type: cardData.card_type,
    cost: cardData.cost,
    effect_text: cardData.effect,  // Map 'effect' from API to 'effect_text' for Card type
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
  });

  if (isLoadingCards) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl">Loading cards...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-game-bg" style={{ padding: 'var(--spacing-component-md)' }}>
      <div className="max-w-7xl mx-auto">
        {/* Header with title, card count, and Confirm button */}
        <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
          <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
            <h1 className="text-3xl font-bold">
              {playerName}
            </h1>
          </div>

          <p className="text-xl font-semibold text-game-highlight">
            Choose 6 unique cards ({selectedCards.length}/6 selected)
          </p>
          
          <button
            onClick={handleConfirm}
            disabled={selectedCards.length !== 6}
            className={`rounded text-xl font-bold transition-all ${
              selectedCards.length === 6
                ? 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                : 'bg-gray-600 cursor-not-allowed opacity-50'
            }`}
            style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-xl)' }}
          >
            Confirm Deck {selectedCards.length === 6 ? '✓' : `(${selectedCards.length}/6)`}
          </button>
        </div>

        {/* Deck Composition Controls */}
        <div 
          className="bg-gray-800 rounded-lg flex items-center justify-between"
          style={{ 
            marginBottom: 'var(--spacing-component-sm)', 
            padding: 'var(--spacing-component-sm)',
            gap: 'var(--spacing-component-lg)'
          }}
        >
          <div className="flex items-center" style={{ gap: 'var(--spacing-component-md)', maxWidth: '600px' }}>
            <span className="text-lg font-semibold whitespace-nowrap">
              <span className="text-red-400">Toys:</span> {numToys}
            </span>
            
            <input
              type="range"
              min="0"
              max="6"
              value={numToys}
              onChange={(e) => handleSliderChange(parseInt(e.target.value))}
              className="flex-1 h-4 bg-gray-700 rounded-lg appearance-none cursor-pointer
                [&::-webkit-slider-thumb]:appearance-none
                [&::-webkit-slider-thumb]:w-8
                [&::-webkit-slider-thumb]:h-8
                [&::-webkit-slider-thumb]:rounded-full
                [&::-webkit-slider-thumb]:bg-game-highlight
                [&::-webkit-slider-thumb]:cursor-pointer
                [&::-webkit-slider-thumb]:shadow-lg
                [&::-moz-range-thumb]:w-8
                [&::-moz-range-thumb]:h-8
                [&::-moz-range-thumb]:rounded-full
                [&::-moz-range-thumb]:bg-game-highlight
                [&::-moz-range-thumb]:cursor-pointer
                [&::-moz-range-thumb]:border-0
                [&::-moz-range-thumb]:shadow-lg
              "
              style={{ minWidth: '200px', maxWidth: '400px' }}
            />
            
            <span className="text-lg font-semibold whitespace-nowrap">
              <span className="text-purple-400">Actions:</span> {numActions}
            </span>
          </div>

          <button
            onClick={handleRandomize}
            disabled={isRandomizing}
            className={`rounded font-bold transition-all whitespace-nowrap ${
              isRandomizing
                ? 'bg-gray-600 cursor-not-allowed opacity-50'
                : 'bg-purple-600 hover:bg-purple-700 cursor-pointer'
            }`}
            style={{ padding: 'var(--spacing-component-sm) var(--spacing-component-lg)' }}
          >
            {isRandomizing ? 'Randomizing...' : '🎲 Random Deck'}
          </button>
        </div>

        <div className="grid" style={{ gap: 'var(--spacing-component-xs)', gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))' }}>
          {cards.map((cardData) => {
            const isSelected = selectedCards.includes(cardData.name);
            const card = createCardForDisplay(cardData);
            const isDisabled = hiddenMode || (!isSelected && selectedCards.length >= 6);
            
            // In hidden mode, show card backs
            if (hiddenMode) {
              return (
                <div
                  key={cardData.name}
                  style={{ display: 'flex', justifyContent: 'center' }}
                >
                  <div
                    className={`
                      w-[165px] h-[225px] rounded border-2 flex items-center justify-center
                      ${isSelected ? 'border-yellow-400 bg-gray-600 shadow-lg shadow-yellow-400/30' : 'border-gray-600 bg-gray-700'}
                    `}
                    style={{ padding: 'var(--spacing-component-md)' }}
                  >
                    <img 
                      src="/ggltcg-logo.svg" 
                      alt="Hidden card" 
                      className={`w-full h-full object-contain ${isSelected ? 'opacity-70' : 'opacity-40'}`}
                    />
                  </div>
                </div>
              );
            }
            
            return (
              <div
                key={cardData.name}
                onClick={() => !isDisabled && toggleCard(cardData.name)}
                style={{ display: 'flex', justifyContent: 'center' }}
              >
                <CardDisplay
                  card={card}
                  size="medium"
                  isSelected={isSelected}
                  isClickable={!isDisabled}
                  isDisabled={isDisabled}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Hover Preview - Disabled until artwork is added */}
      {/* <CardHoverPreview card={hoveredCard} /> */}
    </div>
  );
}
