/**
 * Deck Selection Component
 * Allows players to select 6 unique cards for their deck
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { CardDisplay } from './CardDisplay';
import { getRandomDeck, getAllCards } from '../api/gameService';
import { apiClient } from '../api/client';
import { createCardFromApiData } from '../utils/cardFactory';
import type { Card } from '../types/game';
import type { CardDataResponse } from '../types/api';

interface DeckSelectionProps {
  onDeckSelected: (deck: string[], playerName: string) => void;
  hiddenMode?: boolean;  // When true, cards are face-down and only random selection works
  defaultPlayerName?: string;  // Override the default player name (for AI player)
}

type SortOption = 'cost-asc' | 'cost-desc' | 'name-asc' | 'name-desc' | 'status';

export function DeckSelection({ onDeckSelected, hiddenMode = false, defaultPlayerName }: DeckSelectionProps) {
  const { user } = useAuth();
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<SortOption>('cost-asc');
  const [isRandomizing, setIsRandomizing] = useState(false);
  const [cards, setCards] = useState<CardDataResponse[]>([]);
  const [isLoadingCards, setIsLoadingCards] = useState(true);
  const [favoriteDecks, setFavoriteDecks] = useState<string[][]>([[], [], []]);
  const [savingSlot, setSavingSlot] = useState<number | null>(null);

  // Use provided default name, or get display name from authenticated user
  const playerName = defaultPlayerName || user?.display_name || 'Player';

  // Load cards and favorite decks from backend on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load all cards
        const cardData = await getAllCards();
        setCards(cardData);
        
        // Load favorite decks if user is authenticated and not in hidden mode
        if (user?.google_id && !hiddenMode) {
          try {
            const response = await apiClient.get<{ decks: string[][] }>('/auth/me/decks');
            // Ensure response has proper structure
            if (response.data?.decks && Array.isArray(response.data.decks)) {
              setFavoriteDecks(response.data.decks);
            } else {
              console.warn('Invalid favorite decks response:', response.data);
              setFavoriteDecks([[], [], []]);
            }
          } catch (error) {
            console.error('Failed to load favorite decks:', error);
            // Keep default empty decks
            setFavoriteDecks([[], [], []]);
          }
        }
      } catch (error) {
        console.error('Failed to load cards:', error);
        alert('Failed to load card database. Please refresh the page.');
      } finally {
        setIsLoadingCards(false);
      }
    };

    loadData();
  }, [user, hiddenMode]);

  const toggleCard = (cardName: string) => {
    if (selectedCards.includes(cardName)) {
      setSelectedCards(selectedCards.filter((name) => name !== cardName));
    } else if (selectedCards.length < 6) {
      setSelectedCards([...selectedCards, cardName]);
    }
  };

  const handleRandomize = async () => {
    setIsRandomizing(true);
    try {
      // Use Quick Play logic: 4 toys, 2 actions
      const randomDeck = await getRandomDeck(4, 2);
      setSelectedCards(randomDeck);
    } catch (error) {
      console.error('Failed to get random deck:', error);
      alert('Failed to generate random deck. Please try again.');
    } finally {
      setIsRandomizing(false);
    }
  };

  const loadFavoriteDeck = (slotIndex: number) => {
    const deck = favoriteDecks?.[slotIndex];
    if (deck && Array.isArray(deck) && deck.length === 6) {
      setSelectedCards([...deck]);
    }
  };

  const saveFavoriteDeck = async (slotIndex: number) => {
    if (selectedCards.length !== 6) {
      alert('Please select exactly 6 cards before saving.');
      return;
    }

    setSavingSlot(slotIndex);
    try {
      await apiClient.put(`/auth/me/decks/${slotIndex}`, {
        deck: selectedCards
      });
      
      // Update local state
      const newDecks = [...(favoriteDecks || [[], [], []])];
      newDecks[slotIndex] = [...selectedCards];
      setFavoriteDecks(newDecks);
      
      alert(`Deck saved to slot ${slotIndex + 1}!`);
    } catch (error) {
      console.error('Failed to save favorite deck:', error);
      alert('Failed to save deck. Please try again.');
    } finally {
      setSavingSlot(null);
    }
  };

  const handleConfirm = () => {
    if (selectedCards.length === 6) {
      onDeckSelected(selectedCards, playerName);
    }
  };

  // Sort and split cards into Toys and Actions
  const sortCards = (cardList: CardDataResponse[]) => {
    return [...cardList].sort((a, b) => {
      switch (sortBy) {
        case 'cost-asc':
          return (a.cost ?? 999) - (b.cost ?? 999);
        case 'cost-desc':
          return (b.cost ?? -1) - (a.cost ?? -1);
        case 'name-asc':
          return a.name.localeCompare(b.name);
        case 'name-desc':
          return b.name.localeCompare(a.name);
        case 'status':
          // Sort by selected status first, then by cost
          const aSelected = selectedCards.includes(a.name) ? 0 : 1;
          const bSelected = selectedCards.includes(b.name) ? 0 : 1;
          if (aSelected !== bSelected) return aSelected - bSelected;
          return (a.cost ?? 999) - (b.cost ?? 999);
        default:
          return 0;
      }
    });
  };

  const toyCards = sortCards(cards.filter(c => c.speed !== undefined));
  const actionCards = sortCards(cards.filter(c => c.speed === undefined));

  // Convert CardDataResponse to Card for display using factory
  const createCardForDisplay = (cardData: CardDataResponse): Card => 
    createCardFromApiData(cardData, 'preview');

  if (isLoadingCards) {
    return (
      <div className="min-h-screen bg-game-bg flex items-center justify-center">
        <div className="text-2xl">Loading cards...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-game-bg">
      {/* Sticky Header */}
      <div 
        className="sticky top-0 z-10 bg-game-bg border-b border-gray-700"
        style={{ padding: 'var(--spacing-component-md)' }}
      >
        <div className="max-w-7xl mx-auto">
          {/* Title and Card Count */}
          <div className="flex justify-between items-center" style={{ marginBottom: 'var(--spacing-component-sm)' }}>
            <h1 className="text-3xl font-bold">
              {playerName}
            </h1>

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

          {/* Controls Row */}
          <div 
            className="flex items-center justify-between"
            style={{ gap: 'var(--spacing-component-md)' }}
          >
            {/* Sort Dropdown */}
            <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
              <label htmlFor="sort-select" className="font-semibold">Sort by:</label>
              <select
                id="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-1 cursor-pointer"
              >
                <option value="cost-asc">Cost (Low to High)</option>
                <option value="cost-desc">Cost (High to Low)</option>
                <option value="name-asc">Name (A to Z)</option>
                <option value="name-desc">Name (Z to A)</option>
                <option value="status">Selected First</option>
              </select>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
              {/* Favorite Deck Slots - Only show for authenticated users not in hidden mode */}
              {user?.google_id && !hiddenMode && Array.isArray(favoriteDecks) && (
                <>
                  {[0, 1, 2].map((slotIndex) => {
                    const deck = favoriteDecks?.[slotIndex] || [];
                    const hasCard = Array.isArray(deck) && deck.length === 6;
                    const isSaving = savingSlot === slotIndex;
                    
                    return (
                      <div key={slotIndex} className="flex flex-col items-center" style={{ gap: '4px' }}>
                        <button
                          onClick={() => loadFavoriteDeck(slotIndex)}
                          disabled={!hasCard}
                          className={`rounded font-bold transition-all ${
                            hasCard
                              ? 'bg-blue-600 hover:bg-blue-700 cursor-pointer'
                              : 'bg-gray-700 cursor-not-allowed opacity-50'
                          }`}
                          style={{ padding: '6px 12px', fontSize: '14px' }}
                          title={hasCard ? `Load: ${deck.join(', ')}` : 'Empty slot'}
                        >
                          📁 Deck {slotIndex + 1}
                        </button>
                        <button
                          onClick={() => saveFavoriteDeck(slotIndex)}
                          disabled={selectedCards.length !== 6 || isSaving}
                          className={`rounded font-bold transition-all text-xs ${
                            selectedCards.length === 6 && !isSaving
                              ? 'bg-green-600 hover:bg-green-700 cursor-pointer'
                              : 'bg-gray-700 cursor-not-allowed opacity-50'
                          }`}
                          style={{ padding: '4px 8px' }}
                        >
                          {isSaving ? 'Saving...' : '💾 Save'}
                        </button>
                      </div>
                    );
                  })}
                </>
              )}

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
          </div>
        </div>
      </div>

      {/* Scrollable Content - Split Layout */}
      <div 
        className="max-w-7xl mx-auto"
        style={{ padding: 'var(--spacing-component-md)' }}
      >
        <div className="grid grid-cols-2" style={{ gap: 'var(--spacing-component-lg)' }}>
          {/* Toys Column */}
          <div>
            <h2 
              className="text-2xl font-bold text-red-400 mb-4 sticky"
              style={{ top: 'calc(140px)', backgroundColor: 'var(--color-bg)', paddingTop: 'var(--spacing-component-xs)', paddingBottom: 'var(--spacing-component-xs)', zIndex: 5 }}
            >
              🎭 Toys ({toyCards.filter(c => selectedCards.includes(c.name)).length}/{toyCards.length})
            </h2>
            <div className="grid" style={{ gap: 'var(--spacing-component-xs)', gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))' }}>
              {toyCards.map((cardData) => {
                const isSelected = selectedCards.includes(cardData.name);
                const card = createCardForDisplay(cardData);
                const isDisabled = hiddenMode || (!isSelected && selectedCards.length >= 6);
                
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

          {/* Actions Column */}
          <div>
            <h2 
              className="text-2xl font-bold text-purple-400 mb-4 sticky"
              style={{ top: 'calc(140px)', backgroundColor: 'var(--color-bg)', paddingTop: 'var(--spacing-component-xs)', paddingBottom: 'var(--spacing-component-xs)', zIndex: 5 }}
            >
              ⚡ Actions ({actionCards.filter(c => selectedCards.includes(c.name)).length}/{actionCards.length})
            </h2>
            <div className="grid" style={{ gap: 'var(--spacing-component-xs)', gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))' }}>
              {actionCards.map((cardData) => {
                const isSelected = selectedCards.includes(cardData.name);
                const card = createCardForDisplay(cardData);
                const isDisabled = hiddenMode || (!isSelected && selectedCards.length >= 6);
                
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
        </div>
      </div>
    </div>
  );
}
