/**
 * Deck Selection Component
 * Allows players to select 6 unique cards for their deck
 */

import { useState } from 'react';
import { CARDS, getCardType } from '../data/cards';
import { CardDisplay } from './CardDisplay';
import { getRandomDeck } from '../api/gameService';
// import { CardHoverPreview } from './CardHoverPreview'; // Disabled until artwork is added
import type { Card } from '../types/game';

interface DeckSelectionProps {
  onDeckSelected: (deck: string[]) => void;
  playerName: string;
}

export function DeckSelection({ onDeckSelected, playerName }: DeckSelectionProps) {
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [numToys, setNumToys] = useState(4); // Default: 4 Toys
  const [numActions, setNumActions] = useState(2); // Default: 2 Actions
  const [isRandomizing, setIsRandomizing] = useState(false);
  // const [hoveredCard, setHoveredCard] = useState<Card | null>(null); // Disabled until artwork is added

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
      onDeckSelected(selectedCards);
    }
  };

  // Convert CardData to Card for display
  const createCardForDisplay = (cardData: typeof CARDS[0]): Card => ({
    name: cardData.name,
    card_type: getCardType(cardData) as 'Toy' | 'Action',
    cost: typeof cardData.cost === 'number' ? cardData.cost : -1,
    zone: 'Hand',
    owner: '',
    controller: '',
    speed: cardData.speed,
    strength: cardData.strength,
    stamina: cardData.stamina,
    current_stamina: cardData.stamina,
    is_sleeped: false,
    primary_color: getCardType(cardData) === 'Toy' ? '#C74444' : '#8B5FA8',
    accent_color: getCardType(cardData) === 'Toy' ? '#C74444' : '#8B5FA8',
  });

  return (
    <div className="min-h-screen bg-game-bg p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header with title and Confirm button */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold">
              {playerName} - Select Your Deck
            </h1>
            <p className="text-gray-400 mt-2">
              Choose 6 unique cards ({selectedCards.length}/6 selected)
            </p>
          </div>
          
          <button
            onClick={handleConfirm}
            disabled={selectedCards.length !== 6}
            className={`
              px-8 py-4 rounded text-xl font-bold transition-all
              ${selectedCards.length === 6
                ? 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                : 'bg-gray-600 cursor-not-allowed opacity-50'
              }
            `}
          >
            Confirm Deck {selectedCards.length === 6 ? '✓' : `(${selectedCards.length}/6)`}
          </button>
        </div>

        {/* Deck Composition Slider */}
        <div className="mb-8 p-6 bg-gray-800 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold">Deck Composition</h2>
            <button
              onClick={handleRandomize}
              disabled={isRandomizing}
              className={`
                px-6 py-3 rounded font-bold transition-all
                ${isRandomizing
                  ? 'bg-gray-600 cursor-not-allowed opacity-50'
                  : 'bg-purple-600 hover:bg-purple-700 cursor-pointer'
                }
              `}
            >
              {isRandomizing ? 'Randomizing...' : '🎲 Random Deck'}
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-lg">
                  <span className="text-red-400 font-bold">Toys:</span> {numToys}
                </span>
                <span className="text-lg">
                  <span className="text-purple-400 font-bold">Actions:</span> {numActions}
                </span>
              </div>
              
              <input
                type="range"
                min="0"
                max="6"
                value={numToys}
                onChange={(e) => handleSliderChange(parseInt(e.target.value))}
                className="w-full h-3 bg-gray-700 rounded-lg appearance-none cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none
                  [&::-webkit-slider-thumb]:w-6
                  [&::-webkit-slider-thumb]:h-6
                  [&::-webkit-slider-thumb]:rounded-full
                  [&::-webkit-slider-thumb]:bg-game-highlight
                  [&::-webkit-slider-thumb]:cursor-pointer
                  [&::-moz-range-thumb]:w-6
                  [&::-moz-range-thumb]:h-6
                  [&::-moz-range-thumb]:rounded-full
                  [&::-moz-range-thumb]:bg-game-highlight
                  [&::-moz-range-thumb]:cursor-pointer
                  [&::-moz-range-thumb]:border-0
                "
              />
              
              <div className="flex justify-between text-sm text-gray-500 mt-1">
                <span>All Actions</span>
                <span>3-3 Split</span>
                <span>All Toys</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {CARDS.map((cardData) => {
            const isSelected = selectedCards.includes(cardData.name);
            const card = createCardForDisplay(cardData);
            const isDisabled = !isSelected && selectedCards.length >= 6;
            
            return (
              <div
                key={cardData.name}
                // onMouseEnter={() => setHoveredCard(card)} // Disabled until artwork is added
                // onMouseLeave={() => setHoveredCard(null)} // Disabled until artwork is added
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
