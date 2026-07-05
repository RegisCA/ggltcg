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
import LoginPage from '../components/LoginPage';
import { Leaderboard } from '../components/Leaderboard';
import { LoadingScreen } from '../components/LoadingScreen';
import { PlayerStats } from '../components/PlayerStats';
import { UserMenu } from '../components/UserMenu';
import { ProfileEditModal } from '../components/ProfileEditModal';
import { CardDetailModal } from '../components/CardDetailModal';
import { HowToPlay } from '../components/HowToPlay';
import { useResponsive } from '../hooks/useResponsive';
import { useAuth } from '../contexts/AuthContext';
import { LocalPlayerProvider } from '../contexts/LocalPlayerContext';
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
  LEADERBOARD_FIXTURE_ENTRIES,
  LEADERBOARD_VIEWER_ID,
  PLAYER_STATS_FIXTURE,
  USER_MENU_FIXTURE_USER,
  CARD_DETAIL_FIXTURE_CARD,
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
  { id: 'login', label: 'Login', description: 'LoginPage: signed-out entry screen, no backend.' },
  { id: 'leaderboard', label: 'Leaderboard', description: 'Leaderboard: canned top-10 standings via entriesOverride, no backend fetch. Click the viewer row (Régis) to open Player Stats.' },
  { id: 'player-stats', label: 'Player stats', description: 'PlayerStats: canned drill-in stats via statsOverride, no backend fetch.' },
  { id: 'loading', label: 'Loading', description: 'LoadingScreen: cold-start waking state (forced via coldStartOverride).' },
  { id: 'user-menu', label: 'User menu', description: 'UserMenu over the desk background, canned signed-in user.' },
  { id: 'profile-edit', label: 'Profile edit', description: 'ProfileEditModal over the desk background, canned signed-in user. Save no-ops offline (API call will fail/reject; expected in the harness).' },
  { id: 'card-detail', label: 'Card detail', description: 'CardDetailModal over the desk background: Archer (longest effect text) with an action button.' },
  { id: 'how-to-play', label: 'How to play', description: 'HowToPlay over the desk background: rules modal with tab navigation, no backend.' },
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
  const { user, login, logout } = useAuth();

  // UserMenu reads its user from AuthContext (no override prop on the
  // component itself) — the harness logs in a canned fixture user with a
  // never-expiring fake JWT so #user-menu can render the real component
  // against the real context. No network call: login() only sets local
  // state + localStorage. Signed out again on route change so other screens
  // (e.g. #login) aren't affected by a lingering session.
  useEffect(() => {
    if (route.kind === 'screen' && (route.id === 'user-menu' || route.id === 'profile-edit')) {
      if (!user) {
        const fakeJwt = `fixture.${btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))}.sig`;
        login(fakeJwt, USER_MENU_FIXTURE_USER);
      }
    } else if (user?.google_id === USER_MENU_FIXTURE_USER.google_id) {
      logout();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route]);

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
      ) : route.kind === 'screen' && route.id === 'login' ? (
        <LoginPage key="login" onShowPrivacyPolicy={() => {}} onShowTermsOfService={() => {}} />
      ) : route.kind === 'screen' && route.id === 'leaderboard' ? (
        <LocalPlayerProvider key="leaderboard" value={LEADERBOARD_VIEWER_ID}>
          {/* Closing a modal fixture has to go somewhere — route back to the
              lobby home fixture so X / backdrop / Esc visibly work in preview */}
          <Leaderboard
            entriesOverride={LEADERBOARD_FIXTURE_ENTRIES}
            onClose={() => selectRoute({ kind: 'screen', id: 'lobby-home' })}
            onViewPlayer={() => selectRoute({ kind: 'screen', id: 'player-stats' })}
          />
        </LocalPlayerProvider>
      ) : route.kind === 'screen' && route.id === 'player-stats' ? (
        <LocalPlayerProvider key="player-stats" value={LEADERBOARD_VIEWER_ID}>
          {/* Closing routes back to the leaderboard fixture, mirroring the
              real LobbyHome handoff (Leaderboard -> PlayerStats -> back). */}
          <PlayerStats
            playerId={LEADERBOARD_VIEWER_ID}
            statsOverride={PLAYER_STATS_FIXTURE}
            onClose={() => selectRoute({ kind: 'screen', id: 'leaderboard' })}
          />
        </LocalPlayerProvider>
      ) : route.kind === 'screen' && route.id === 'loading' ? (
        <LoadingScreen key="loading" onReady={() => {}} coldStartOverride />
      ) : route.kind === 'screen' && route.id === 'user-menu' ? (
        <div
          key="user-menu"
          className="min-h-screen"
          style={{ background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))' }}
        >
          <UserMenu />
        </div>
      ) : route.kind === 'screen' && route.id === 'profile-edit' ? (
        <div
          key="profile-edit"
          className="min-h-screen"
          style={{ background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))' }}
        >
          <ProfileEditModal isOpen={true} onClose={() => selectRoute({ kind: 'screen', id: 'user-menu' })} />
        </div>
      ) : route.kind === 'screen' && route.id === 'card-detail' ? (
        <div
          key="card-detail"
          className="min-h-screen"
          style={{ background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))' }}
        >
          <CardDetailModal
            card={CARD_DETAIL_FIXTURE_CARD}
            isOpen={true}
            onClose={() => selectRoute({ kind: 'screen', id: 'lobby-home' })}
            onAction={() => {}}
            actionLabel="Select"
          />
        </div>
      ) : route.kind === 'screen' && route.id === 'how-to-play' ? (
        <div
          key="how-to-play"
          className="min-h-screen"
          style={{ background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))' }}
        >
          <HowToPlay isOpen={true} onClose={() => selectRoute({ kind: 'screen', id: 'lobby-home' })} />
        </div>
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
