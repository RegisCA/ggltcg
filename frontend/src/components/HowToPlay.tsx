/**
 * HowToPlay Modal Component
 * 
 * Provides a quick overview of GGLTCG rules for new players.
 * Content adapted from the official rules document.
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
    <Modal isOpen={isOpen} onClose={onClose} title="How to Play">
      <div style={{ maxWidth: '600px', maxHeight: '70vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* Tab Navigation */}
        <div 
          className="flex border-b border-gray-600"
          style={{ marginBottom: 'var(--spacing-component-md)' }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex-1 py-2 px-3 text-sm font-medium transition-colors
                ${activeTab === tab.id 
                  ? 'text-white border-b-2 border-game-highlight bg-gray-700/50' 
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/30'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content - Scrollable */}
        <div 
          className="overflow-y-auto text-gray-200"
          style={{ 
            padding: 'var(--spacing-component-sm)',
            flex: 1,
          }}
        >
          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'cards' && <CardsTab />}
          {activeTab === 'tussling' && <TusslingTab />}
          {activeTab === 'tips' && <TipsTab />}
        </div>

        {/* Close Button */}
        <div 
          className="border-t border-gray-600 flex justify-end"
          style={{ paddingTop: 'var(--spacing-component-md)' }}
        >
          <button
            onClick={onClose}
            className="bg-game-highlight hover:bg-red-600 text-white font-bold rounded transition-colors"
            style={{ padding: 'var(--spacing-component-xs) var(--spacing-component-lg)' }}
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
    className="text-lg font-bold text-white"
    style={{ marginBottom: 'var(--spacing-component-xs)' }}
  >
    {children}
  </h3>
);

const Paragraph: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p 
    className="text-gray-300"
    style={{ marginBottom: 'var(--spacing-component-md)', lineHeight: '1.6' }}
  >
    {children}
  </p>
);

const BulletList: React.FC<{ items: string[] }> = ({ items }) => (
  <ul 
    className="text-gray-300 list-disc"
    style={{ 
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
  <span className="text-game-highlight font-semibold">{children}</span>
);

const StatBadge: React.FC<{ label: string; description: string }> = ({ label, description }) => (
  <div 
    className="bg-gray-700/50 rounded"
    style={{ padding: 'var(--spacing-component-xs)' }}
  >
    <span className="text-game-highlight font-bold">{label}</span>
    <span className="text-gray-300"> — {description}</span>
  </div>
);

function OverviewTab() {
  return (
    <>
      <SectionTitle>Objective</SectionTitle>
      <Paragraph>
        Put all of your opponent's cards into their <Highlight>Sleep Zone</Highlight> to win!
        This includes cards in their hand, in play, and any they draw.
      </Paragraph>

      <SectionTitle>Command Counters (CC)</SectionTitle>
      <Paragraph>
        CC is the resource you use to play cards and initiate tussles. 
        You gain <Highlight>4 CC</Highlight> at the start of each turn 
        (only 2 CC on the very first turn). Unspent CC carries over to your next turn, 
        up to a maximum of <Highlight>7 CC</Highlight>.
      </Paragraph>

      <SectionTitle>Turn Structure</SectionTitle>
      <BulletList items={[
        'Start Phase: Gain 4 CC (2 on Turn 1)',
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
        Toys are your fighters! They have three stats and stay in play until defeated:
      </Paragraph>
      <div className="flex flex-col" style={{ gap: 'var(--spacing-component-xs)', marginBottom: 'var(--spacing-component-md)' }}>
        <StatBadge label="Speed" description="Who strikes first in a tussle" />
        <StatBadge label="Strength" description="Damage dealt when striking" />
        <StatBadge label="Stamina" description="Health - when it hits 0, the Toy sleeps" />
      </div>

      <SectionTitle>Action Cards</SectionTitle>
      <Paragraph>
        Actions have immediate effects and then go to your Sleep Zone. 
        Use them to buff your Toys, disrupt opponents, or recover cards!
      </Paragraph>

      <SectionTitle>Zones</SectionTitle>
      <BulletList items={[
        'Hand: Cards you can play (hidden from opponent)',
        'In Play: Active Toys that can tussle',
        'Sleep Zone: Defeated or used cards (visible to both)',
      ]} />
    </>
  );
}

function TusslingTab() {
  return (
    <>
      <SectionTitle>How Tussles Work</SectionTitle>
      <Paragraph>
        Tussling is combat between Toys. It costs <Highlight>2 CC</Highlight> by default 
        (some cards can reduce this).
      </Paragraph>

      <SectionTitle>Tussle Resolution</SectionTitle>
      <BulletList items={[
        'The Toy with higher Speed strikes first',
        'Your Toys get +1 Speed during your turn (attacker advantage)',
        'Each Toy deals damage equal to its Strength',
        'If Speed is tied, both Toys strike simultaneously',
        'Toys at 0 Stamina go to Sleep Zone',
      ]} />

      <SectionTitle>Direct Attacks</SectionTitle>
      <Paragraph>
        If your opponent has no Toys in play, you can attack their hand directly!
        This sleeps a random card from their hand. You can do this <Highlight>twice per turn</Highlight>.
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
        'Save CC for key moments - banking resources can set up big plays',
        'Pay attention to Speed - striking first can win the game',
        'Buff cards like Ka and Demideca affect ALL your Toys',
        'Action cards go to Sleep Zone - this can help cards like Dream cost less',
        "Don't forget direct attacks when the opponent's field is empty!",
      ]} />

      <SectionTitle>Strategy Notes</SectionTitle>
      <BulletList items={[
        'Mix Toys and Actions in your deck for flexibility',
        'Consider card synergies when building your 6-card deck',
        'Watch your opponent\'s CC - they might be saving for something big',
        'Some cards have restrictions (e.g., Rush can\'t be played Turn 1)',
      ]} />

      <SectionTitle>Learn More</SectionTitle>
      <Paragraph>
        The best way to learn is to play! Start with "Play vs AI" to practice, 
        then challenge friends in multiplayer. Every card's effect is shown when you tap/hover on it.
      </Paragraph>
    </>
  );
}
