/**
 * Deck Selection Component
 *
 * Allows players to select 6 unique cards for their deck. Restyled to the
 * Paper & Ink language (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md) — the last
 * surface with its own bespoke card styling (WP-1 #6 tail). Reuses CardDisplay
 * (§4) for every card instead of hand-rolled markup, Gochi Hand zone headers
 * (§5 zone-header pattern) and the board's gold/purple button language (§7.2).
 *
 * This screen lives outside a game (no LocalPlayerContext provider), so
 * CardDisplay's material default applies: cards render as the player's own
 * (cream paper) material — see useLocalPlayerId's documented "own" default.
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { CardDisplay } from './CardDisplay';
import { getRandomDeck, getAllCards } from '../api/gameService';
import { apiClient } from '../api/client';
import { createCardFromApiData } from '../utils/cardFactory';
import type { Card } from '../types/game';
import type { CardDataResponse } from '../types/api';

interface DeckSelectionProps {
  onDeckSelected: (deck: string[], playerName: string) => void;
  onBack?: () => void;  // Optional back button handler
  hiddenMode?: boolean;  // When true, cards are face-down and only random selection works
  defaultPlayerName?: string;  // Override the default player name (for AI player)
  /** Test/preview seam: when provided, skips the getAllCards() fetch and
   *  renders this card pool instead. Production callers never pass this —
   *  used by the /design.html harness fixture. */
  cardsOverride?: CardDataResponse[];
}

type SortOption = 'cost-asc' | 'cost-desc' | 'name-asc' | 'name-desc' | 'status';

// A medium Toy's stat rail dominates its height (~131px) regardless of effect
// length; Actions have no rail. Sharing one minHeight across the Toys/Actions
// grids equalizes them the same way TargetSelectionModal does across its
// per-zone grids (grid-auto-rows:1fr only equalizes within one grid).
const MIXED_CARD_MIN_HEIGHT = 134;

export function DeckSelection({ onDeckSelected, onBack, hiddenMode = false, defaultPlayerName, cardsOverride }: DeckSelectionProps) {
  const { user } = useAuth();
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<SortOption>('cost-asc');
  const [isRandomizing, setIsRandomizing] = useState(false);
  const [cards, setCards] = useState<CardDataResponse[]>(cardsOverride ?? []);
  const [isLoadingCards, setIsLoadingCards] = useState(!cardsOverride);
  const [favoriteDecks, setFavoriteDecks] = useState<string[][]>([[], [], []]);
  const [savingSlot, setSavingSlot] = useState<number | null>(null);

  // Use provided default name, or get display name from authenticated user
  const playerName = defaultPlayerName || user?.display_name || 'Player';

  // Load cards and favorite decks from backend on mount
  useEffect(() => {
    if (cardsOverride) return; // preview harness supplies cards directly

    const loadData = async () => {
      try {
        // Load all cards
        const cardData = await getAllCards();
        setCards(cardData);

        // Load favorite decks if user is authenticated and not in hidden mode
        if (user?.google_id && !hiddenMode) {
          try {
            const response = await apiClient.get<{ favorite_decks: string[][] }>('/auth/me/decks');
            // Ensure response has proper structure
            if (response.data?.favorite_decks && Array.isArray(response.data.favorite_decks)) {
              setFavoriteDecks(response.data.favorite_decks);
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
  }, [user, hiddenMode, cardsOverride]);

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
      // Use Quick Play logic: completely random 6 cards (any combination)
      // Backend will select any 6 cards from the entire pool
      const randomDeck = await getRandomDeck(0, 0); // Special: 0,0 means "truly random"
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
      console.log(`Saving deck to slot ${slotIndex}:`, selectedCards);
      const response = await apiClient.put(`/auth/me/decks/${slotIndex}`, {
        deck: selectedCards
      });
      console.log('Save response:', response.data);

      // Update local state
      const newDecks = [...(favoriteDecks || [[], [], []])];
      newDecks[slotIndex] = [...selectedCards];
      setFavoriteDecks(newDecks);

      alert(`Deck saved to slot ${slotIndex + 1}!`);
    } catch (error) {
      console.error('Failed to save favorite deck:', error);
      if (axios.isAxiosError(error)) {
        console.error('Axios error details:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status
        });
      }
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
        case 'status': {
          // Sort by selected status first, then by cost
          const aSelected = selectedCards.includes(a.name) ? 0 : 1;
          const bSelected = selectedCards.includes(b.name) ? 0 : 1;
          if (aSelected !== bSelected) return aSelected - bSelected;
          return (a.cost ?? 999) - (b.cost ?? 999);
        }
        default:
          return 0;
      }
    });
  };

  const toyCards = sortCards(cards.filter(c => c.speed !== null && c.speed !== undefined));
  const actionCards = sortCards(cards.filter(c => c.speed === null || c.speed === undefined));

  // Convert CardDataResponse to Card for display using factory
  const createCardForDisplay = (cardData: CardDataResponse): Card =>
    createCardFromApiData(cardData, 'preview');

  if (isLoadingCards) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))', color: 'var(--ink-text)' }}
      >
        <div style={{ fontSize: '20px', fontWeight: 700 }}>Loading cards...</div>
      </div>
    );
  }

  const renderCardGrid = (cardList: CardDataResponse[]) => (
    <div
      style={{
        display: 'grid',
        gap: 'var(--spacing-component-xs)',
        gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
        gridAutoRows: '1fr',
      }}
    >
      {cardList.map((cardData) => {
        const isSelected = selectedCards.includes(cardData.name);
        const card = createCardForDisplay(cardData);
        const isDisabled = hiddenMode || (!isSelected && selectedCards.length >= 6);

        if (hiddenMode) {
          return (
            <div key={cardData.name} style={{ display: 'flex', justifyContent: 'center' }}>
              <div
                style={{
                  width: '100%',
                  maxWidth: '165px',
                  aspectRatio: '165 / 225',
                  borderRadius: '6px',
                  border: `2.5px solid ${isSelected ? 'var(--gold)' : 'rgba(237,232,222,.25)'}`,
                  background: 'var(--ink)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: isSelected ? '0 4px 10px rgba(242,193,78,.25)' : 'none',
                  padding: 'var(--spacing-component-md)',
                }}
              >
                <img
                  src="/ggltcg-logo.svg"
                  alt="Hidden card"
                  style={{ width: '100%', height: '100%', objectFit: 'contain', opacity: isSelected ? 0.7 : 0.4 }}
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
              fluid
              minHeight={MIXED_CARD_MIN_HEIGHT}
              isSelected={isSelected}
              isClickable={!isDisabled}
              isDisabled={isDisabled}
              disableDetailModal
            />
          </div>
        );
      })}
    </div>
  );

  return (
    <div
      className="min-h-screen"
      style={{ background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))', color: 'var(--ink-text)' }}
    >
      {/* Sticky Header */}
      <div
        className="sticky top-0 z-10"
        style={{
          background: 'var(--desk-top)',
          borderBottom: '1px solid rgba(237,232,222,.15)',
          padding: 'var(--spacing-component-md)',
        }}
      >
        <div className="max-w-7xl mx-auto">
          {/* Title and Card Count */}
          <div
            className="flex flex-wrap justify-between items-center"
            style={{ marginBottom: 'var(--spacing-component-sm)', gap: 'var(--spacing-component-sm)' }}
          >
            <div className="flex items-center" style={{ gap: 'var(--spacing-component-md)' }}>
              {onBack && (
                <button
                  onClick={onBack}
                  className="flex items-center transition-colors"
                  style={{ gap: 'var(--spacing-component-xs)', color: 'var(--ink-muted)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '13px' }}
                >
                  <span>←</span> Back
                </button>
              )}
              <h1 style={{ fontFamily: 'var(--font-card-name)', fontSize: '28px', lineHeight: 1 }}>
                {playerName}
              </h1>
            </div>

            <p style={{ fontWeight: 900, fontSize: '14px', letterSpacing: '.02em', color: 'var(--gold)' }}>
              Choose 6 unique cards ({selectedCards.length}/6 selected)
            </p>

            <button
              onClick={handleConfirm}
              disabled={selectedCards.length !== 6}
              style={{
                fontWeight: 900,
                fontSize: '14px',
                borderRadius: '6px',
                border: 'none',
                padding: 'var(--spacing-component-sm) var(--spacing-component-xl)',
                background: selectedCards.length === 6 ? 'var(--gold)' : 'rgba(237,232,222,.15)',
                color: selectedCards.length === 6 ? 'var(--desk-bottom)' : 'var(--ink-faint)',
                boxShadow: selectedCards.length === 6 ? '0 3px 0 rgba(0,0,0,.5)' : 'none',
                cursor: selectedCards.length === 6 ? 'pointer' : 'not-allowed',
              }}
            >
              Confirm Deck {selectedCards.length === 6 ? '✓' : `(${selectedCards.length}/6)`}
            </button>
          </div>

          {/* Controls Row */}
          <div
            className="flex flex-wrap items-center justify-between"
            style={{ gap: 'var(--spacing-component-md)' }}
          >
            {/* Sort Dropdown */}
            <div className="flex items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
              <label
                htmlFor="sort-select"
                style={{ fontWeight: 700, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--ink-muted)' }}
              >
                Sort by:
              </label>
              <select
                id="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                style={{
                  background: 'var(--bar)',
                  border: '1px solid rgba(237,232,222,.25)',
                  borderRadius: '6px',
                  color: 'var(--ink-text)',
                  padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
                  cursor: 'pointer',
                  fontSize: '13px',
                }}
              >
                <option value="cost-asc">Cost (Low to High)</option>
                <option value="cost-desc">Cost (High to Low)</option>
                <option value="name-asc">Name (A to Z)</option>
                <option value="name-desc">Name (Z to A)</option>
                <option value="status">Selected First</option>
              </select>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center" style={{ gap: 'var(--spacing-component-sm)' }}>
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
                          style={{
                            borderRadius: '6px',
                            fontWeight: 700,
                            fontSize: '12px',
                            padding: '6px 12px',
                            border: '1px solid rgba(126,166,224,.35)',
                            background: hasCard ? 'rgba(126,166,224,.15)' : 'rgba(237,232,222,.05)',
                            color: hasCard ? 'var(--you)' : 'var(--ink-faint)',
                            cursor: hasCard ? 'pointer' : 'not-allowed',
                            opacity: hasCard ? 1 : 0.6,
                          }}
                          title={hasCard ? `Load: ${deck.join(', ')}` : 'Empty slot'}
                        >
                          Deck {slotIndex + 1}
                        </button>
                        <button
                          onClick={() => saveFavoriteDeck(slotIndex)}
                          disabled={selectedCards.length !== 6 || isSaving}
                          style={{
                            borderRadius: '6px',
                            fontWeight: 700,
                            fontSize: '11px',
                            padding: '4px 8px',
                            border: '1px solid rgba(237,232,222,.2)',
                            background: selectedCards.length === 6 && !isSaving ? 'rgba(237,232,222,.1)' : 'transparent',
                            color: selectedCards.length === 6 && !isSaving ? 'var(--ink-text)' : 'var(--ink-faint)',
                            cursor: selectedCards.length === 6 && !isSaving ? 'pointer' : 'not-allowed',
                            opacity: selectedCards.length === 6 && !isSaving ? 1 : 0.6,
                          }}
                        >
                          {isSaving ? 'Saving...' : 'Save'}
                        </button>
                      </div>
                    );
                  })}
                </>
              )}

              <button
                onClick={handleRandomize}
                disabled={isRandomizing}
                style={{
                  borderRadius: '6px',
                  fontWeight: 900,
                  fontSize: '13px',
                  whiteSpace: 'nowrap',
                  padding: 'var(--spacing-component-sm) var(--spacing-component-lg)',
                  border: 'none',
                  background: isRandomizing ? 'rgba(237,232,222,.15)' : 'var(--gold)',
                  color: isRandomizing ? 'var(--ink-faint)' : 'var(--desk-bottom)',
                  boxShadow: isRandomizing ? 'none' : '0 3px 0 rgba(0,0,0,.5)',
                  cursor: isRandomizing ? 'not-allowed' : 'pointer',
                }}
              >
                {isRandomizing ? 'Randomizing...' : 'Random Deck'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable Content - Split Layout */}
      <div className="max-w-7xl mx-auto" style={{ padding: 'var(--spacing-component-md)' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 'var(--spacing-component-lg)',
          }}
        >
          {/* Toys Column */}
          <div>
            <div
              style={{
                position: 'sticky',
                top: 0,
                zIndex: 5,
                background: 'var(--desk-top)',
                paddingTop: 'var(--spacing-component-xs)',
                paddingBottom: 'var(--spacing-component-xs)',
                marginBottom: 'var(--spacing-component-xs)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--gold)', flexShrink: 0 }} />
              <span style={{ fontFamily: 'var(--font-card-name)', fontSize: '20px' }}>
                Toys
              </span>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--ink-faint)' }}>
                {toyCards.filter(c => selectedCards.includes(c.name)).length}/{toyCards.length}
              </span>
            </div>
            {renderCardGrid(toyCards)}
          </div>

          {/* Actions Column */}
          <div>
            <div
              style={{
                position: 'sticky',
                top: 0,
                zIndex: 5,
                background: 'var(--desk-top)',
                paddingTop: 'var(--spacing-component-xs)',
                paddingBottom: 'var(--spacing-component-xs)',
                marginBottom: 'var(--spacing-component-xs)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--them)', flexShrink: 0 }} />
              <span style={{ fontFamily: 'var(--font-card-name)', fontSize: '20px' }}>
                Actions
              </span>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--ink-faint)' }}>
                {actionCards.filter(c => selectedCards.includes(c.name)).length}/{actionCards.length}
              </span>
            </div>
            {renderCardGrid(actionCards)}
          </div>
        </div>
      </div>
    </div>
  );
}
