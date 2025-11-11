/**
 * Deck Selection Component
 * Allows players to select 6 unique cards for their deck
 */

import { useState } from 'react';
import { CARDS, getCardType } from '../data/cards';

interface DeckSelectionProps {
  onDeckSelected: (deck: string[]) => void;
  playerName: string;
}

export function DeckSelection({ onDeckSelected, playerName }: DeckSelectionProps) {
  const [selectedCards, setSelectedCards] = useState<string[]>([]);

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

  return (
    <div className="min-h-screen bg-game-bg p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-center mb-2">
          {playerName} - Select Your Deck
        </h1>
        <p className="text-center text-gray-400 mb-8">
          Choose 6 unique cards ({selectedCards.length}/6 selected)
        </p>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
          {CARDS.map((card) => {
            const isSelected = selectedCards.includes(card.name);
            const cardType = getCardType(card);
            
            return (
              <button
                key={card.name}
                onClick={() => toggleCard(card.name)}
                disabled={!isSelected && selectedCards.length >= 6}
                className={`
                  p-4 rounded-lg border-2 transition-all duration-200
                  ${isSelected
                    ? 'border-game-highlight bg-game-accent scale-105 shadow-lg'
                    : 'border-game-card bg-game-card hover:border-gray-500'
                  }
                  ${!isSelected && selectedCards.length >= 6
                    ? 'opacity-50 cursor-not-allowed'
                    : 'cursor-pointer hover:scale-105'
                  }
                `}
              >
                <div className="text-left">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-xl font-bold">{card.name}</h3>
                    <span className={`
                      px-2 py-1 rounded text-xs font-bold
                      ${cardType === 'TOY' ? 'bg-blue-600' : 'bg-purple-600'}
                    `}>
                      {cardType}
                    </span>
                  </div>
                  
                  <div className="text-sm text-gray-300 mb-3">
                    Cost: {card.cost} CC
                  </div>

                  {cardType === 'TOY' && (
                    <div className="flex gap-3 text-sm mb-2">
                      <div>SPD: {card.speed}</div>
                      <div>STR: {card.strength}</div>
                      <div>STA: {card.stamina}</div>
                    </div>
                  )}

                  <p className="text-xs text-gray-400 italic line-clamp-3">
                    {card.effect}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        <div className="text-center">
          <button
            onClick={handleConfirm}
            disabled={selectedCards.length !== 6}
            className={`
              px-8 py-4 rounded-lg text-xl font-bold transition-all
              ${selectedCards.length === 6
                ? 'bg-game-highlight hover:bg-red-600 cursor-pointer'
                : 'bg-gray-600 cursor-not-allowed opacity-50'
              }
            `}
          >
            Confirm Deck
          </button>
        </div>
      </div>
    </div>
  );
}
