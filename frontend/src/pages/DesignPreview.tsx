/**
 * Design Preview Page (/design.html)
 *
 * Renders the real GameBoard against canned fixture game states so layout and
 * UX changes can be evaluated at any viewport width — on real devices via
 * Vercel preview deploys — without a backend, an account, or playing turns to
 * reach a given state.
 *
 * Actions are display-only: gameService short-circuits every call for
 * `fixture-` game IDs (see src/api/gameService.ts). Target-selection modals
 * still open normally since that flow is client-side.
 */

import { useEffect, useState } from 'react';
import { GameBoard } from '../components/GameBoard';
import { DeckSelection } from '../components/DeckSelection';
import { VictoryScreen } from '../components/VictoryScreen';
import { LobbyHome } from '../components/LobbyHome';
import { LobbyCreate } from '../components/LobbyCreate';
import { LobbyJoin } from '../components/LobbyJoin';
import { LobbyWaiting } from '../components/LobbyWaiting';
import { useResponsive } from '../hooks/useResponsive';
import {
  DECK_SELECTION_CARD_POOL,
  DESIGN_FIXTURES,
  FIXTURE_AI_ID,
  FIXTURE_HUMAN_ID,
  VICTORY_FIXTURE,
  DEFEAT_FIXTURE,
  VICTORY_AI_LOGS_FIXTURE,
  LOBBY_FIXTURE_GAME_ID,
  LOBBY_FIXTURE_GAME_CODE,
} from '../fixtures/designFixtures';

// Non-GameBoard screens get their own fixture ids (no `fixture-` game state
// behind them) — routed separately from the GameState-backed board fixtures.
const SCREEN_FIXTURES = [
  { id: 'deck-selection', label: 'Deck selection', description: 'DeckSelection screen: full card pool, no backend.' },
  { id: 'victory', label: 'Victory', description: 'VictoryScreen: you win, full recap with AI plans/reasoning.' },
  { id: 'defeat', label: 'Defeat', description: 'VictoryScreen: opponent wins, same recap content.' },
  { id: 'lobby-home', label: 'Lobby: Home', description: 'LobbyHome screen: mode picker, no backend.' },
  { id: 'lobby-create', label: 'Lobby: Create', description: 'LobbyCreate screen: create-game form, no backend.' },
  { id: 'lobby-join', label: 'Lobby: Join', description: 'LobbyJoin screen: join-game code entry, no backend.' },
  { id: 'lobby-waiting', label: 'Lobby: Waiting', description: 'LobbyWaiting screen: waiting room with both players present, polling disabled.' },
];

type RouteMatch = { kind: 'board'; id: string } | { kind: 'screen'; id: string };

function routeFromHash(): RouteMatch {
  const hash = window.location.hash.replace(/^#/, '');
  const screen = SCREEN_FIXTURES.find((f) => f.id === hash);
  if (screen) return { kind: 'screen', id: screen.id };
  const board = DESIGN_FIXTURES.find((f) => f.id === `fixture-${hash}` || f.id === hash);
  return { kind: 'board', id: board?.id ?? DESIGN_FIXTURES[0].id };
}

export function DesignPreview() {
  const [route, setRoute] = useState<RouteMatch>(routeFromHash);
  const { width, height, isMobile, isTablet } = useResponsive();

  // Keep the URL hash in sync so a specific fixture can be linked directly
  // (e.g. open /design.html#midgame or /design.html#deck-selection on a phone).
  useEffect(() => {
    const onHashChange = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const selectRoute = (next: RouteMatch) => {
    setRoute(next);
    const hash = next.kind === 'screen' ? next.id : next.id.replace(/^fixture-/, '');
    window.history.replaceState(null, '', `#${hash}`);
  };

  const boardFixture = DESIGN_FIXTURES.find((f) => f.id === route.id) ?? DESIGN_FIXTURES[0];
  const screenFixture = SCREEN_FIXTURES.find((f) => f.id === route.id);
  const layoutName = isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop';
  const activeDescription = route.kind === 'screen' ? screenFixture?.description : boardFixture.description;

  return (
    <div className="min-h-screen bg-game-bg">
      {/* Harness chrome — deliberately visually distinct from the game UI */}
      <div
        className="border-b-2 border-purple-500 bg-purple-950/60"
        style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-sm)' }}
      >
        <div className="flex flex-wrap items-center" style={{ gap: 'var(--spacing-component-xs)' }}>
          <span className="text-xs font-bold text-purple-300 whitespace-nowrap">
            🎨 DESIGN PREVIEW
          </span>
          {DESIGN_FIXTURES.map((f) => (
            <button
              key={f.id}
              onClick={() => selectRoute({ kind: 'board', id: f.id })}
              className={`text-xs rounded border transition-colors ${
                route.kind === 'board' && f.id === boardFixture.id
                  ? 'bg-purple-600 border-purple-300 text-white font-bold'
                  : 'bg-gray-800 border-gray-600 text-gray-300 hover:bg-gray-700'
              }`}
              style={{ padding: '2px var(--spacing-component-xs)' }}
            >
              {f.label}
            </button>
          ))}
          <span className="text-xs text-purple-300/60" style={{ margin: '0 4px' }}>|</span>
          {SCREEN_FIXTURES.map((f) => (
            <button
              key={f.id}
              onClick={() => selectRoute({ kind: 'screen', id: f.id })}
              className={`text-xs rounded border transition-colors ${
                route.kind === 'screen' && f.id === route.id
                  ? 'bg-purple-600 border-purple-300 text-white font-bold'
                  : 'bg-gray-800 border-gray-600 text-gray-300 hover:bg-gray-700'
              }`}
              style={{ padding: '2px var(--spacing-component-xs)' }}
            >
              {f.label}
            </button>
          ))}
          <span className="text-xs text-purple-300/80 font-mono whitespace-nowrap ml-auto">
            {Math.round(width)}×{Math.round(height)} · {layoutName}
          </span>
        </div>
        <p className="text-xs text-gray-400" style={{ marginTop: '2px' }}>
          {activeDescription} Actions are display-only.
        </p>
      </div>

      {route.kind === 'screen' && route.id === 'deck-selection' ? (
        <DeckSelection
          key="deck-selection"
          cardsOverride={DECK_SELECTION_CARD_POOL}
          onDeckSelected={() => {}}
          onBack={() => {}}
          defaultPlayerName="You"
        />
      ) : route.kind === 'screen' && route.id === 'victory' ? (
        <VictoryScreen key="victory" gameState={VICTORY_FIXTURE.state} onPlayAgain={() => {}} aiLogsOverride={VICTORY_AI_LOGS_FIXTURE} localPlayerId={FIXTURE_HUMAN_ID} />
      ) : route.kind === 'screen' && route.id === 'defeat' ? (
        <VictoryScreen key="defeat" gameState={DEFEAT_FIXTURE.state} onPlayAgain={() => {}} aiLogsOverride={VICTORY_AI_LOGS_FIXTURE} localPlayerId={FIXTURE_HUMAN_ID} />
      ) : route.kind === 'screen' && route.id === 'lobby-home' ? (
        <LobbyHome
          key="lobby-home"
          onCreateLobby={() => {}}
          onJoinLobby={() => {}}
          onPlayVsAI={() => {}}
          onQuickPlay={() => {}}
        />
      ) : route.kind === 'screen' && route.id === 'lobby-create' ? (
        <LobbyCreate key="lobby-create" onLobbyCreated={() => {}} onBack={() => {}} />
      ) : route.kind === 'screen' && route.id === 'lobby-join' ? (
        <LobbyJoin key="lobby-join" onLobbyJoined={() => {}} onBack={() => {}} />
      ) : route.kind === 'screen' && route.id === 'lobby-waiting' ? (
        <LobbyWaiting
          key="lobby-waiting"
          gameId={LOBBY_FIXTURE_GAME_ID}
          gameCode={LOBBY_FIXTURE_GAME_CODE}
          actualPlayerId="fixture-you"
          currentPlayerId="player1"
          currentPlayerName="You"
          otherPlayerName="Gemiknight"
          onGameStarted={() => {}}
          onBack={() => {}}
          initialPhaseOverride="waiting-for-decks"
          currentPlayerReadyOverride={true}
        />
      ) : (
        // key remounts the board on fixture switch so no UI state leaks across
        <GameBoard
          key={boardFixture.id}
          gameId={boardFixture.id}
          humanPlayerId={FIXTURE_HUMAN_ID}
          aiPlayerId={FIXTURE_AI_ID}
          onGameEnd={() => {}}
        />
      )}
    </div>
  );
}
