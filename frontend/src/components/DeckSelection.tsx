/**
 * Deck Selection Component
 * Allows players to select 6 unique cards for their deck
 */

import { useState, useEffect } from 'react';
import { CardDisplay } from './CardDisplay';
import { getRandomDeck, getAllCards } from '../api/gameService';
import type { Card } from '../types/game';
import type { CardDataResponse } from '../types/api';

interface DeckSelectionProps {
  onDeckSelected: (deck: string[], customName?: string) => void;
  playerName: string;
}

export function DeckSelection({ onDeckSelected, playerName }: DeckSelectionProps) {
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [numToys, setNumToys] = useState(4); // Default: 4 Toys
  const [numActions, setNumActions] = useState(2); // Default: 2 Actions
  const [isRandomizing, setIsRandomizing] = useState(false);
  const [customName, setCustomName] = useState(playerName);
  const [isEditingName, setIsEditingName] = useState(false);
  const [cards, setCards] = useState<CardDataResponse[]>([]);
  const [isLoadingCards, setIsLoadingCards] = useState(true);

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

  // Reset customName and clear selections when playerName prop changes (when switching between player 1 and player 2)
  useEffect(() => {
    setCustomName(playerName);
    setSelectedCards([]);
    setNumToys(4);
    setNumActions(2);
  }, [playerName]);

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
      onDeckSelected(selectedCards, customName);
    }
  };

  // Convert CardDataResponse to Card for display
  const createCardForDisplay = (cardData: CardDataResponse): Card => ({
    name: cardData.name,
    card_type: cardData.card_type,
    cost: cardData.cost,
    zone: 'Hand',
    owner: '',
    controller: '',
    speed: cardData.speed,
    strength: cardData.strength,
    stamina: cardData.stamina,
    current_stamina: cardData.stamina,
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
    <div className="min-h-screen bg-game-bg p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header with title, card count, and Confirm button */}
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-3">
            {isEditingName ? (
              <input
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                onBlur={() => setIsEditingName(false)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') setIsEditingName(false);
                }}
                autoFocus
                maxLength={30}
                className="text-3xl font-bold bg-gray-800 border-2 border-game-highlight rounded px-3 py-1 focus:outline-none"
              />
            ) : (
              <h1 
                className="text-3xl font-bold cursor-pointer hover:text-game-highlight transition-colors"
                onClick={() => setIsEditingName(true)}
                title="Click to edit name"
              >
                {customName}
              </h1>
            )}
            <button
              onClick={() => setIsEditingName(true)}
              className="text-gray-400 hover:text-game-highlight transition-colors"
              style={{ 
                background: 'none',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                fontSize: '1.25rem'
              }}
              title="Edit name"
            >
              ✏️
            </button>
          </div>

          <p className="text-xl font-semibold text-game-highlight">
            Choose 6 unique cards ({selectedCards.length}/6 selected)
          </p>
          
          <button
            onClick={handleConfirm}
            disabled={selectedCards.length !== 6}
            className={`
              px-8 py-3 rounded text-xl font-bold transition-all
              ${selectedCards.length === 6
                ? 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                : 'bg-gray-600 cursor-not-allowed opacity-50'
              }
            `}
          >
            Confirm Deck {selectedCards.length === 6 ? '✓' : `(${selectedCards.length}/6)`}
          </button>
        </div>

        {/* Deck Composition Controls */}
        <div className="mb-3 p-3 bg-gray-800 rounded-lg flex items-center justify-between gap-6">
          <div className="flex items-center gap-4" style={{ maxWidth: '600px' }}>
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
            className={`
              px-6 py-3 rounded font-bold transition-all whitespace-nowrap
              ${isRandomizing
                ? 'bg-gray-600 cursor-not-allowed opacity-50'
                : 'bg-purple-600 hover:bg-purple-700 cursor-pointer'
              }
            `}
          >
            {isRandomizing ? 'Randomizing...' : '🎲 Random Deck'}
          </button>
        </div>

        <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))' }}>
          {cards.map((cardData) => {
            const isSelected = selectedCards.includes(cardData.name);
            const card = createCardForDisplay(cardData);
            const isDisabled = !isSelected && selectedCards.length >= 6;
            
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
