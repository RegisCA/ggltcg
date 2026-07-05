/**
 * HowToPlay Modal Component
 *
 * Provides a quick overview of GGLTCG rules for new players.
 * Content adapted from the official rules document.
 *
 * Restyled to Paper & Ink (docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md): dark
 * panel + gold hairline (the settled Leaderboard/CardDetailModal idiom),
 * Gochi Hand section headers, gold accents for emphasis/tabs, 16px body text
 * for readability. Copy audited against the redesigned board + target modal
 * so visual/interaction descriptions match what players actually see now
 * (ownership materials, gold ready-bolt, single-select-replaces /
 * multi-select-toggles-up-to-max / Cancel-clears targeting).
 */

import React, { useState } from 'react';
import { Modal } from './ui/Modal';

interface HowToPlayProps {
  isOpen: boolean;
  onClose: () => void;
}

type TabId = 'overview' | 'cards' | 'tussling' | 'tips';

interface TabContent {
  id: TabId;
  label: string;
}

const TABS: TabContent[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'cards', label: 'Cards' },
  { id: 'tussling', label: 'Tussling' },
  { id: 'tips', label: 'Tips' },
];

export const HowToPlay: React.FC<HowToPlayProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="How to Play"
      panelStyle={{
        width: '640px',
        maxWidth: '100%',
        maxHeight: '85vh',
        background: '#241E17',
        borderRadius: '8px',
        border: '1px solid var(--gold)',
        boxShadow: '0 8px 24px rgba(0,0,0,.4)',
        padding: 0,
      }}
    >
      <div style={{ maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        {/* Tab Navigation */}
        <div
          className="flex flex-shrink-0"
          style={{ borderBottom: '1px solid rgba(237,232,222,.15)' }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex-1 font-bold transition-colors"
              style={{
                padding: 'var(--spacing-component-sm) var(--spacing-component-xs)',
                fontSize: 'var(--font-size-sm)',
                minHeight: 'var(--size-touch-target-min)',
                background: activeTab === tab.id ? 'rgba(242,193,78,.12)' : 'transparent',
                color: activeTab === tab.id ? 'var(--gold)' : 'var(--ink-faint)',
                borderBottom: activeTab === tab.id ? '2px solid var(--gold)' : '2px solid transparent',
                border: 'none',
                borderBottomWidth: '2px',
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content - Scrollable */}
        <div
          className="overflow-y-auto"
          style={{
            padding: 'var(--spacing-component-lg)',
            flex: 1,
            color: 'var(--ink-text)',
          }}
        >
          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'cards' && <CardsTab />}
          {activeTab === 'tussling' && <TusslingTab />}
          {activeTab === 'tips' && <TipsTab />}
        </div>

        {/* Close Button */}
        <div
          className="flex-shrink-0 flex justify-end"
          style={{
            padding: 'var(--spacing-component-md) var(--spacing-component-lg)',
            borderTop: '1px solid rgba(237,232,222,.15)',
          }}
        >
          <button
            onClick={onClose}
            className="font-bold"
            style={{
              minHeight: 'var(--size-touch-target-button)',
              padding: 'var(--spacing-component-xs) var(--spacing-component-lg)',
              borderRadius: '6px',
              border: 'none',
              background: 'var(--gold)',
              color: 'var(--desk-bottom)',
              boxShadow: '0 3px 0 rgba(0,0,0,.5)',
              cursor: 'pointer',
            }}
          >
            Got it!
          </button>
        </div>
      </div>
    </Modal>
  );
};

const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3
    style={{
      fontFamily: 'var(--font-card-name)',
      fontSize: '22px',
      color: 'var(--ink-text)',
      marginBottom: 'var(--spacing-component-xs)',
    }}
  >
    {children}
  </h3>
);

const Paragraph: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p
    style={{
      color: 'var(--ink-muted)',
      fontSize: 'var(--font-size-md)',
      marginBottom: 'var(--spacing-component-md)',
      lineHeight: '1.6',
    }}
  >
    {children}
  </p>
);

const BulletList: React.FC<{ items: string[] }> = ({ items }) => (
  <ul
    className="list-disc"
    style={{
      color: 'var(--ink-muted)',
      fontSize: 'var(--font-size-md)',
      marginBottom: 'var(--spacing-component-md)',
      paddingLeft: 'var(--spacing-component-lg)',
      lineHeight: '1.6',
    }}
  >
    {items.map((item, i) => (
      <li key={i} style={{ marginBottom: '4px' }}>{item}</li>
    ))}
  </ul>
);

const Highlight: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: 'var(--gold)', fontWeight: 700 }}>{children}</span>
);

const StatBadge: React.FC<{ label: string; description: string }> = ({ label, description }) => (
  <div
    style={{
      padding: 'var(--spacing-component-xs) var(--spacing-component-sm)',
      background: 'rgba(237,232,222,.06)',
      borderRadius: '6px',
      border: '1px solid rgba(237,232,222,.12)',
    }}
  >
    <span style={{ color: 'var(--gold)', fontWeight: 900 }}>{label}</span>
    <span style={{ color: 'var(--ink-muted)' }}> — {description}</span>
  </div>
);

function OverviewTab() {
  return (
    <>
      <SectionTitle>Objective</SectionTitle>
      <Paragraph>
        Put all of your opponent's cards into their <Highlight>Break Zone</Highlight> to win!
        This includes cards in their hand, in play, and any they draw.
      </Paragraph>

      <SectionTitle>Charge</SectionTitle>
      <Paragraph>
        Charge is the resource you use to play cards and initiate tussles.
        You gain <Highlight>4 Charge</Highlight> at the start of each turn
        (only 2 Charge on the very first turn). Unspent Charge carries over to your next turn,
        up to a maximum of <Highlight>7 Charge</Highlight>.
      </Paragraph>

      <SectionTitle>Turn Structure</SectionTitle>
      <BulletList items={[
        'Start Phase: Gain 4 Charge (2 on Turn 1)',
        'Main Phase: Play cards, initiate tussles, use abilities',
        'End Phase: Your turn ends, opponent begins theirs',
      ]} />
    </>
  );
}

function CardsTab() {
  return (
    <>
      <SectionTitle>Toy Cards</SectionTitle>
      <Paragraph>
        Toys are your fighters! They have three stats and stay in play until broken:
      </Paragraph>
      <div className="flex flex-col" style={{ gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-md)' }}>
        <StatBadge label="Speed" description="Who strikes first in a tussle" />
        <StatBadge label="Strength" description="Damage dealt when striking" />
        <StatBadge label="Stamina" description="Health — when it hits 0, the Toy breaks" />
      </div>

      <SectionTitle>Action Cards</SectionTitle>
      <Paragraph>
        Actions have immediate effects and then go to your Break Zone.
        Use them to buff your Toys, disrupt opponents, or recover cards!
      </Paragraph>

      <SectionTitle>Your Cards vs. Their Cards</SectionTitle>
      <Paragraph>
        Your own cards always appear on cream paper; your opponent's always appear in dark ink —
        this holds everywhere: in play, in the Break Zone, and in targeting screens. A gold bolt
        marks a Toy that's ready to act on your turn.
      </Paragraph>

      <SectionTitle>Zones</SectionTitle>
      <BulletList items={[
        'Hand: Cards you can play (hidden from opponent)',
        'In Play: Active Toys that can tussle',
        'Break Zone: Broken or used cards (visible to both)',
      ]} />
    </>
  );
}

function TusslingTab() {
  return (
    <>
      <SectionTitle>How Tussles Work</SectionTitle>
      <Paragraph>
        Tussling is combat between Toys. It costs <Highlight>2 Charge</Highlight> by default
        (some cards can reduce this).
      </Paragraph>

      <SectionTitle>Tussle Resolution</SectionTitle>
      <BulletList items={[
        'The Toy with higher Speed strikes first',
        'Your Toys get +1 Speed during your turn (attacker advantage)',
        'Each Toy deals damage equal to its Strength',
        'If Speed is tied, both Toys strike simultaneously',
        'Toys at 0 Stamina go to the Break Zone',
      ]} />

      <SectionTitle>Direct Attacks</SectionTitle>
      <Paragraph>
        If your opponent has no Toys in play, you can attack their hand directly!
        This breaks a random card from their hand. You can do this <Highlight>twice per turn</Highlight>.
      </Paragraph>

      <SectionTitle>Choosing Targets</SectionTitle>
      <Paragraph>
        When a card asks you to pick a target, tap a card to select it — a gold outline and
        checkmark show your pick. Effects that need just one target replace your pick each time
        you tap a different card; effects that need several let you tap up to the limit shown.
        <Highlight> Cancel</Highlight> clears your selection and backs out of the choice.
      </Paragraph>

      <SectionTitle>Special Abilities</SectionTitle>
      <Paragraph>
        Some cards have powerful abilities. <Highlight>Knight</Highlight> automatically wins any tussle
        on its controller's turn. <Highlight>Beary</Highlight> is immune to opponent's card effects.
        Read card abilities carefully!
      </Paragraph>
    </>
  );
}

function TipsTab() {
  return (
    <>
      <SectionTitle>Beginner Tips</SectionTitle>
      <BulletList items={[
        'Save Charge for key moments — banking resources can set up big plays',
        'Pay attention to Speed — striking first can win the game',
        'Buff cards like Ka and Demideca affect ALL your Toys',
        'Action cards go to the Break Zone — this can help cards like Dream cost less',
        "Don't forget direct attacks when the opponent's field is empty!",
      ]} />

      <SectionTitle>Strategy Notes</SectionTitle>
      <BulletList items={[
        'Mix Toys and Actions in your deck for flexibility',
        'Consider card synergies when building your 6-card deck',
        'Watch your opponent\'s Charge — they might be saving for something big',
        'Some cards have restrictions (e.g., Rush can\'t be played Turn 1)',
      ]} />

      <SectionTitle>Learn More</SectionTitle>
      <Paragraph>
        The best way to learn is to play! Start with "Play vs AI" to practice,
        then challenge friends in multiplayer. Every card's effect is shown when you tap or hover on it.
      </Paragraph>
    </>
  );
}
