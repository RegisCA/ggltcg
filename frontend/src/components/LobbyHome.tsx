/**
 * Lobby Home Component
 *
 * Main entry point for multiplayer - Create or Join a game. Restyled to the
 * Paper & Ink language (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md): desk
 * gradient background, Gochi Hand title, gold primary card + dark
 * secondary cards with the board's button idiom.
 *
 * Decorative one-off emoji not sanctioned by §8 removed (🎮🔗🤖⚡🏆🃏📖); kept
 * none here since none of these are content-bearing state badges (same call
 * as VictoryScreen).
 */

import { useState } from 'react';
import { Leaderboard } from './Leaderboard';
import { PlayerStats } from './PlayerStats';
import { CardStats } from './CardStats';
import { Footer } from './ui/Footer';
import { HowToPlay } from './HowToPlay';

interface LobbyHomeProps {
  onCreateLobby: () => void;
  onJoinLobby: () => void;
  onPlayVsAI: (hiddenMode: boolean) => void;
  onQuickPlay: () => void;
  onShowPrivacyPolicy?: () => void;
  onShowTermsOfService?: () => void;
}

interface ModeCardProps {
  title: string;
  description: string;
  hint: string;
  onClick: () => void;
  hoverKey: string;
  hoveredButton: string | null;
  setHoveredButton: (key: string | null) => void;
  emphasis?: 'gold' | 'default';
}

function ModeCard({
  title,
  description,
  hint,
  onClick,
  hoverKey,
  hoveredButton,
  setHoveredButton,
  emphasis = 'default',
}: ModeCardProps) {
  const isHovered = hoveredButton === hoverKey;
  const isGold = emphasis === 'gold';

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHoveredButton(hoverKey)}
      onMouseLeave={() => setHoveredButton(null)}
      className="w-full text-left transition-all"
      style={{
        borderRadius: '8px',
        border: `2px solid ${isGold ? 'var(--gold)' : isHovered ? 'rgba(242,193,78,.45)' : 'rgba(237,232,222,.15)'}`,
        background: isGold ? 'rgba(242,193,78,.12)' : '#241E17',
        padding: 'var(--spacing-component-lg)',
        cursor: 'pointer',
        boxShadow: isHovered ? '0 4px 14px rgba(0,0,0,.35)' : 'none',
      }}
    >
      <div
        style={{
          fontFamily: 'var(--font-card-name)',
          fontSize: '26px',
          color: isGold ? 'var(--gold)' : 'var(--ink-text)',
          marginBottom: 'var(--spacing-component-xs)',
        }}
      >
        {title}
      </div>
      <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink-muted)' }}>{description}</div>
      <div style={{ fontSize: '12px', color: 'var(--ink-faint)', marginTop: '4px' }}>{hint}</div>
    </button>
  );
}

function SecondaryButton({
  label,
  hint,
  onClick,
  hoverKey,
  hoveredButton,
  setHoveredButton,
}: {
  label: string;
  hint: string;
  onClick: () => void;
  hoverKey: string;
  hoveredButton: string | null;
  setHoveredButton: (key: string | null) => void;
}) {
  const isHovered = hoveredButton === hoverKey;

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHoveredButton(hoverKey)}
      onMouseLeave={() => setHoveredButton(null)}
      className="flex-1 text-center transition-all"
      style={{
        borderRadius: '6px',
        border: `1px solid ${isHovered ? 'rgba(242,193,78,.45)' : 'rgba(237,232,222,.15)'}`,
        background: isHovered ? 'rgba(237,232,222,.08)' : 'rgba(237,232,222,.04)',
        padding: 'var(--spacing-component-md)',
        cursor: 'pointer',
      }}
    >
      <div style={{ fontWeight: 900, fontSize: '15px', color: 'var(--ink-text)', marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--ink-faint)' }}>{hint}</div>
    </button>
  );
}

export function LobbyHome({
  onCreateLobby,
  onJoinLobby,
  onPlayVsAI,
  onQuickPlay,
  onShowPrivacyPolicy,
  onShowTermsOfService,
}: LobbyHomeProps) {
  const [hoveredButton, setHoveredButton] = useState<string | null>(null);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [viewingPlayerId, setViewingPlayerId] = useState<string | null>(null);
  const [showHowToPlay, setShowHowToPlay] = useState(false);
  const [showCardStats, setShowCardStats] = useState(false);

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{
        padding: 'var(--spacing-component-md)',
        background: 'linear-gradient(180deg, var(--desk-top), var(--desk-bottom))',
        color: 'var(--ink-text)',
      }}
    >
      <div className="max-w-2xl w-full">
        {/* Title */}
        <div className="text-center" style={{ marginBottom: 'var(--spacing-component-xl)' }}>
          <h1
            style={{
              fontFamily: 'var(--font-card-name)',
              fontSize: 'clamp(48px, 10vw, 72px)',
              lineHeight: 1,
              color: 'var(--ink-text)',
              marginBottom: 'var(--spacing-component-sm)',
            }}
          >
            GGLTCG
          </h1>
          <p style={{ fontSize: 'clamp(16px, 3vw, 20px)', fontWeight: 700, color: 'var(--ink-muted)' }}>
            Choose Your Game Mode
          </p>
        </div>

        {/* Game Mode Options */}
        <div className="flex flex-col" style={{ gap: 'var(--spacing-component-md)' }}>
          <ModeCard
            title="Create Game"
            description="Host a new game and invite a friend"
            hint="Get a 6-character code to share"
            onClick={onCreateLobby}
            hoverKey="create"
            hoveredButton={hoveredButton}
            setHoveredButton={setHoveredButton}
            emphasis="gold"
          />

          <ModeCard
            title="Join Game"
            description="Enter a friend's game code"
            hint="Connect to an existing lobby"
            onClick={onJoinLobby}
            hoverKey="join"
            hoveredButton={hoveredButton}
            setHoveredButton={setHoveredButton}
          />

          <ModeCard
            title="Play vs AI"
            description="Practice against computer opponent"
            hint="Single-player mode"
            onClick={() => onPlayVsAI(false)}
            hoverKey="ai"
            hoveredButton={hoveredButton}
            setHoveredButton={setHoveredButton}
          />

          <ModeCard
            title="Quick Play"
            description="Jump straight into battle"
            hint="Random decks, instant action!"
            onClick={onQuickPlay}
            hoverKey="quick"
            hoveredButton={hoveredButton}
            setHoveredButton={setHoveredButton}
          />

          {/* Secondary buttons row */}
          <div className="flex" style={{ gap: 'var(--spacing-component-sm)', marginTop: 'var(--spacing-component-xs)' }}>
            <SecondaryButton
              label="Leaderboard"
              hint="View top players"
              onClick={() => setShowLeaderboard(true)}
              hoverKey="leaderboard"
              hoveredButton={hoveredButton}
              setHoveredButton={setHoveredButton}
            />
            <SecondaryButton
              label="Card Stats"
              hint="Win rates per card"
              onClick={() => setShowCardStats(true)}
              hoverKey="cardstats"
              hoveredButton={hoveredButton}
              setHoveredButton={setHoveredButton}
            />
            <SecondaryButton
              label="How to Play"
              hint="Learn the rules"
              onClick={() => setShowHowToPlay(true)}
              hoverKey="howtoplay"
              hoveredButton={hoveredButton}
              setHoveredButton={setHoveredButton}
            />
          </div>
        </div>

        {/* Footer */}
        <Footer
          variant="light"
          showTagline={true}
          onShowPrivacyPolicy={onShowPrivacyPolicy}
          onShowTermsOfService={onShowTermsOfService}
        />
      </div>

      {/* Leaderboard Modal */}
      {showLeaderboard && (
        <Leaderboard
          onClose={() => setShowLeaderboard(false)}
          onViewPlayer={(playerId) => {
            setShowLeaderboard(false);
            setViewingPlayerId(playerId);
          }}
        />
      )}

      {/* Player Stats Modal */}
      {viewingPlayerId && (
        <PlayerStats
          playerId={viewingPlayerId}
          onClose={() => {
            setViewingPlayerId(null);
            setShowLeaderboard(true);
          }}
        />
      )}

      {/* Card Stats Modal */}
      {showCardStats && (
        <CardStats onClose={() => setShowCardStats(false)} />
      )}

      {/* How to Play Modal */}
      <HowToPlay isOpen={showHowToPlay} onClose={() => setShowHowToPlay(false)} />
    </div>
  );
}
