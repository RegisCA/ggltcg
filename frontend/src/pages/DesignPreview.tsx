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
import { useResponsive } from '../hooks/useResponsive';
import { DESIGN_FIXTURES, FIXTURE_AI_ID, FIXTURE_HUMAN_ID } from '../fixtures/designFixtures';

function fixtureFromHash(): string {
  const hash = window.location.hash.replace(/^#/, '');
  const match = DESIGN_FIXTURES.find((f) => f.id === `fixture-${hash}` || f.id === hash);
  return match?.id ?? DESIGN_FIXTURES[0].id;
}

export function DesignPreview() {
  const [fixtureId, setFixtureId] = useState<string>(fixtureFromHash);
  const { width, height, isMobile, isTablet } = useResponsive();

  // Keep the URL hash in sync so a specific fixture can be linked directly
  // (e.g. open /design.html#midgame on a phone).
  useEffect(() => {
    const onHashChange = () => setFixtureId(fixtureFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const selectFixture = (id: string) => {
    setFixtureId(id);
    window.history.replaceState(null, '', `#${id.replace(/^fixture-/, '')}`);
  };

  const fixture = DESIGN_FIXTURES.find((f) => f.id === fixtureId) ?? DESIGN_FIXTURES[0];
  const layoutName = isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop';

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
              onClick={() => selectFixture(f.id)}
              className={`text-xs rounded border transition-colors ${
                f.id === fixture.id
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
          {fixture.description} Actions are display-only.
        </p>
      </div>

      {/* key remounts the board on fixture switch so no UI state leaks across */}
      <GameBoard
        key={fixture.id}
        gameId={fixture.id}
        humanPlayerId={FIXTURE_HUMAN_ID}
        aiPlayerId={FIXTURE_AI_ID}
        onGameEnd={() => {}}
      />
    </div>
  );
}
