/**
 * LocalPlayerContext — who "you" are on the board.
 *
 * Paper & Ink binds a card's material to its OWNER vs the local player (§1):
 * your cards are cream paper, the opponent's are dark ink, in every zone. A
 * card only carries `owner`, so any component rendering a card needs to know the
 * local player id to pick the material. GameBoard provides it once here (context
 * crosses React portals, so the target modal gets it too) instead of threading a
 * prop through every zone.
 *
 * Outside a game (deck builder, isolated previews) there's no provider; consumers
 * treat a null id as "own" (cream paper), the sensible default for card galleries.
 */
import { createContext, useContext } from 'react';

const LocalPlayerContext = createContext<string | null>(null);

export const LocalPlayerProvider = LocalPlayerContext.Provider;

/** The local player's id, or null when rendered outside a game board. */
export function useLocalPlayerId(): string | null {
  return useContext(LocalPlayerContext);
}
