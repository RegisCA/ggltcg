/**
 * Deck Selection Component
 * Allows players to select 6 unique cards for their deck
 */

import { useState } from 'react';
import { CARDS, getCardType } from '../data/cards';
import { CardDisplay } from './CardDisplay';
// import { CardHoverPreview } from './CardHoverPreview'; // Disabled until artwork is added
import type { Card } from '../types/game';

interface DeckSelectionProps {
  onDeckSelected: (deck: string[]) => void;
  playerName: string;
}

export function DeckSelection({ onDeckSelected, playerName }: DeckSelectionProps) {
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  // const [hoveredCard, setHoveredCard] = useState<Card | null>(null); // Disabled until artwork is added

  const toggleCard = (cardName: string) => {
    if (selectedCards.includes(cardName)) {
      setSelectedCards(selectedCards.filter((name) => name !== cardName));
    } else if (selectedCards.length < 6) {
      setSelectedCards([...selectedCards, cardName]);
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
    card_type: getCardType(cardData) as 'TOY' | 'ACTION',
    cost: typeof cardData.cost === 'number' ? cardData.cost : -1,
    zone: 'HAND',
    owner: '',
    controller: '',
    speed: cardData.speed,
    strength: cardData.strength,
    stamina: cardData.stamina,
    current_stamina: cardData.stamina,
    is_sleeped: false,
    primary_color: getCardType(cardData) === 'TOY' ? '#C74444' : '#8B5FA8',
    accent_color: getCardType(cardData) === 'TOY' ? '#C74444' : '#8B5FA8',
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
