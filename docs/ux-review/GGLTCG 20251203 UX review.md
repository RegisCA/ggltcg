# GGLTCG UX Review - December 3, 2025

## Overview

This document captures UX observations, feedback, and improvement opportunities for the GGLTCG web application across multiple device types and screen sizes.

### Background

The number of UX components has grown as we’ve added more features, such as player authenticating through google and the ability to play 1vs1 online games.
While the current UX is pretty functional, there are inconsistencies in how things look and feel, but also in how they are implemented.

### Review Goals

- UX: optimize the game board for the different ways to play/interact with the app, keeping in mind that being able to read the stats and effect description of each card during gameplay is critical:
  - On a desktop/laptop, tablet, or phone
  - With a mouse/trackpad, keyboard, touch controls, or a combination of those
  - Interacting with the cards, using the action panel, or both
  
- UX: make all components visually cohesive (buttons to go back to the landing screen all have different labels!). The game needs to look complete and professional. This may require adding a Copyright notice and other key info.
- Accessibility - let's try to be smart where we can to make the game enjoyable for everyone:
  - Color contrast meets WCAG AA standards
  - Keyboard navigation functional
  - Screen reader friendly (semantic HTML)
  - Touch target sizes (minimum 44x44px)
- Front end code base quality: we need to ensure code and design principles are implemented and respected. There have been many iterations and bug fixes, but we have a lack of consistency in how things are done. Code maintainability is important as I’m planning to open source this code base.

### Review Scope

- **Date**: December 4, 2025
- **Version**: Production build (ggltcg.vercel.app)
- **Devices Tested**:
  - Laptop (1440x900) + Laptop (2880x1800)
  - Tablet Landscape (1024x768)
  - Tablet Portrait (768x1024)
  - Phone Portrait (390x844 - iPhone 13)
  - Phone Landscape (844x390 - iPhone 13)

### Screenshot Organization

Screenshots are organized by viewport size in `screenshots/` subdirectories:

- `laptop-1440x900/` - Automated screenshots at standard laptop resolution
- `laptop-2880x1800/` - **High-resolution manual screenshots** (2x scale) - detailed gameplay states
- `tablet-landscape-1024x768/`
- `tablet-portrait-768x1024/`
- `phone-portrait-390x844/`
- `phone-landscape-844x390/`

**Note**: The `laptop-2880x1800/` folder contains manually captured screenshots at high resolution (2880x1800), focusing on specific gameplay scenarios not captured in automated tests (target selection modals, cards in play/sleep zones, tussle states, activated abilities), lobby (create, join, wait), leaderboard and player stats, and victory screens.

---

## 1. Loading Screen

**Purpose**: First screen shown while connecting to backend server

### Loading Screen - Screenshots

- Laptop: ![Loading](screenshots/laptop-2880x1800/00-loading-screen.png)

### Loading Screen - Observations

- **Loading state**: Clean, minimal design with spinner animation
- **Branding**: Game title and subtitle clearly displayed
- **Wait time**: Can take up to 1 minute on free tier (Render cold start)
- **User feedback**: "Connecting to game server...." message provides context
- **Improvement**: Consider adding estimated wait time or progress indicator for long loads
- **Improvement**: Could add tips/hints about gameplay during wait

---

## 2. Landing/Load Screen

**Purpose**: First impression, branding, and initial user journey

### Landing/Load Screen - Screenshots

- Laptop: ![Landing](screenshots/laptop-2880x1800/20-landing-screen.png)

### Landing/Load Screen - Observations

- **Branding**: Missing Copyright notice. Privacy Policy and Terms of Service were just added.
- **New player onboarding**: no usage hints, no quick game reference/rules explanation
- **About**: Missing. need basic info about the game and link to repo
- **Profile**: link in top left corner is barely visible and white on grey.
- **Layout**: Functional, but icon choices cheapen the game?

---

## 3. Lobby: Create Game

**Purpose**: User initiates new game, selects options

### Lobby: Create Game - Screenshots

- Laptop: ![Create Game](screenshots/laptop-2880x1800/21-lobby-create-game.png)

### Lobby: Create Game - Observations

- simple and functional
- contrast of `Back to Menu` button not ideal

---

## 4. Lobby: Join Game

**Purpose**: User joins existing multiplayer game via code

### Lobby: Join Game - Screenshots

- Laptop: ![Join Game](screenshots/laptop-2880x1800/22-lobby-join-game.png)

### Lobby: Join Game - Observations

- functional

---

## 5. Lobby: Waiting for Opponent

**Purpose**: Hold state while waiting for second player to join

### Lobby: Waiting - Screenshots

- Laptop: ![Waiting](screenshots/laptop-2880x1800/23-lobby-wait.png)

### Lobby: Waiting - Observations

- functional
- would be nice to display player names (users have to be authenticated, we have that info, it's just a matter of polling once the 2nd player joins maybe?)

## 6. Leaderboard and Player Stats

**Purpose**: Leaderboard ranking and player stats

### Screenshots

- Laptop: ![Leaderboard](screenshots/laptop-2880x1800/24-leaderboard.png)
- Laptop: ![Player Stats](screenshots/laptop-2880x1800/25-leaderboard-player-stats.png)

### Observations

- Leaderboard's transparency should be adjusted - content hard to read
- Player Stats should probably be floating like the leaderboard component and not be squished to the right side like this. Great info, but hard to read!

---

## 7. Deck Selection

**Purpose**: Players select their decks before game starts

### Deck Selection - Screenshots

- Laptop (P1): ![Deck Selection P1](screenshots/laptop-1440x900/05-deck-selection-p1.png)
- Laptop (P2): ![Deck Selection P2](screenshots/laptop-1440x900/06-deck-selection-p2.png)

### Deck Selection - Observations

- Currently single deck option available (standard deck)
- Simple "Ready" confirmation screen
- Functional and clear for current use case with 17 cards.
- A future enhancement could be filtering by card type when more cards get added.

---

# GAME BOARD SECTION

## 8. Game Board: Overview & Layout

**Purpose**: Overall game board organization, responsive layout, and initial impressions

### Initial State Screenshots (Multiple Viewports)

- Laptop: ![Initial](screenshots/laptop-1440x900/07-game-initial-state.png)
- Tablet (Landscape): ![Initial](screenshots/tablet-landscape-1024x768/07-game-initial-state.png)
- Tablet (Portrait): ![Initial](screenshots/tablet-portrait-768x1024/07-game-initial-state.png)
- Phone (Portrait): ![Initial](screenshots/phone-portrait-390x844/07-game-initial-state.png)
- Phone (Landscape): ![Initial](screenshots/phone-landscape-844x390/07-game-initial-state.png)

### Full Page Layout Screenshots

- Laptop: ![Full Page](screenshots/laptop-1440x900/14-full-page-layout.png)
- Tablet (Landscape): ![Full Page](screenshots/tablet-landscape-1024x768/14-full-page-layout.png)
- Tablet (Portrait): ![Full Page](screenshots/tablet-portrait-768x1024/14-full-page-layout.png)
- Phone (Portrait): ![Full Page](screenshots/phone-portrait-390x844/14-full-page-layout.png)
- Phone (Landscape): ![Full Page](screenshots/phone-landscape-844x390/14-full-page-layout.png)

### Key Observations

**Information Hierarchy**:

- Phase indicator and turn information need more prominence
- Player indicators (you vs opponent) could be clearer
- CC (currency) display is small - may be hard to read on mobile

**Responsive Behavior**:

- Viewport utilization varies significantly across device sizes
- Need to verify scrolling behavior on smaller devices
- Breakpoint transitions should be tested more thoroughly

**Overall Layout**:

- Layout is functional but could benefit from more consistent spacing
- Fixed elements behavior needs review (headers, action panel)
- Consider whether full-page scrolling is optimal for all viewports

---

## 9. Game Board: Card Zones

**Purpose**: Organization and display of cards in different zones (Hand, Play, Sleep)

### Hand Zone Screenshots

- Laptop (Mid-game): ![Mid-Game](screenshots/laptop-1440x900/12-game-mid-game.png)
- Phone (Landscape): ![Mid-Game](screenshots/phone-landscape-844x390/12-game-mid-game.png)

### Play Zone and Sleep Zone Screenshots (High-Res)

![Cards in Play/Sleep - Turn 4](screenshots/laptop-2880x1800/01-cards-in-play-and-sleep-turn4.png)

### Game Board Key Observations

**Hand Zone**:

- Card size varies significantly across viewports
- Card details (name, cost, effect) visibility varies - needs improvement on mobile
- Multiple cards in hand: need to verify scrolling/overflow behavior
- Selection affordances could be clearer

**Play Zone**:

- Cards in play are laid out side-by-side without overlap - clear organization
- Card stats (speed/strength/stamina) are readable at high resolution but may be problematic on smaller screens
- Visual distinction between your cards and opponent's cards is adequate but could be stronger

**Sleep Zone**:

- Sleeped cards are visually distinct (appears grayed/faded)
- Cards in sleep zone overlap/stack to save space - can make individual cards harder to identify
- Zone label/header could be more prominent

**Zone Organization Overall**:

- All three zones are distinct but could benefit from clearer visual separation
- Spacing and layout could be optimized for different screen sizes
- Consider fixed/sticky positioning for zone headers

---

## 10. Game Board: Action Panel

**Purpose**: Primary interface for player actions (Play Card, Tussle, Activated Abilities, End Phase)

### Action Panel Screenshots

Main phase with actions available:

- Laptop: ![Main Phase](screenshots/laptop-1440x900/10-game-main-phase.png)
- Tablet (Landscape): ![Main Phase](screenshots/tablet-landscape-1024x768/10-game-main-phase.png)
- Tablet (Portrait): ![Main Phase](screenshots/tablet-portrait-768x1024/10-game-main-phase.png)
- Phone (Portrait): ![Main Phase](screenshots/phone-portrait-390x844/10-game-main-phase.png)
- Phone (Landscape): ![Main Phase](screenshots/phone-landscape-844x390/10-game-main-phase.png)

Complex board with four action types:

![Board - Turn 6 - Multiple Actions](screenshots/laptop-2880x1800/12-cards-turn6-four-action-types.png)

### Action Panel Key Observations

**Action Types & Clarity**:

- Four distinct action types: Play Card, Tussle, Activated Abilities, End Phase
- Visual hierarchy of actions could be improved
- Action availability indicators (enabled/disabled states) need better contrast

**Action Panel Layout**:

- Panel positioning varies across screen sizes - needs consistency
- Button sizing appropriate for desktop but may need adjustment for touch targets (44x44px minimum)
- Action descriptions/labels clear but could be more concise

**Interaction Flow**:

- Flow from selecting action → selecting target → confirming needs review
- Cancel/back options should be more prominent
- First-time user guidance missing (tutorial/hints)

**Priority Issues**:

- **CRITICAL**: Systemic typography/contrast issues throughout application
  - Blue-on-blue text in action panel
  - White-on-grey buttons with poor visibility
  - Inconsistent text colors and sizes
  - Requires comprehensive frontend typography audit
- Ensure disabled actions are clearly distinguished from enabled
- Add visual feedback for action selection
- Consider grouping related actions (e.g., all card-based actions together)

---

## 11. Game Board: Target Selection Modals

**Purpose**: Selecting targets for card effects (Wake, Sun, Copy, Twist) and combat (Tussle)

### Target Selection Modal Examples

**Twist Card Targeting**:

- No selection: ![Target Modal - Twist - No Selection](screenshots/laptop-2880x1800/02-target-modal-twist-no-selection.png)
- Knight selected: ![Target Modal - Twist - Knight Selected](screenshots/laptop-2880x1800/03-target-modal-twist-knight-selected.png)

**Copy Card Targeting**:

- No selection: ![Target Modal - Copy - No Selection](screenshots/laptop-2880x1800/05-target-modal-copy-no-selection.png)
- Archer selected: ![Target Modal - Copy - Archer Selected](screenshots/laptop-2880x1800/06-target-modal-copy-archer-selected.png)

**Wake Card Targeting**:

- No selection: ![Target Modal - Wake - No Selection](screenshots/laptop-2880x1800/10-target-modal-wake-no-selection.png)
- Ka selected: ![Target Modal - Wake - Ka Selected](screenshots/laptop-2880x1800/11-target-modal-wake-ka-selected.png)

**Tussle Targeting**:

![Tussle Selection - Knight](screenshots/laptop-2880x1800/09-target-selection-tussle-knight.png)

**Activated Ability Targeting** (Archer):

![Target Modal - Archer - Dream Selected](screenshots/laptop-2880x1800/13-target-modal-archer-dream-selected.png)

### Target Selection Key Observations

**Modal Design**:

- Modal presence is clear with darkened backdrop
- Instruction text explains what to select, but formatting could be improved
- Valid targets are highlighted - good pattern
- Confirm/Cancel buttons are present but could be more prominent

**Selection Feedback**:

- Selected cards have visual distinction (appears highlighted/bordered)
- Selection state is clear once a target is chosen
- Multi-step selection (if needed) should be better indicated

**Target Validity**:

- Only valid targets are selectable - excellent
- Invalid targets appear grayed/disabled - good pattern
- Target pools correctly filtered (e.g., Wake only shows sleeped cards)

**Responsive Behavior**:

- Need mobile screenshots to verify behavior on phone/tablet
- Touch targets for card selection need real device testing
- Modal sizing and layout on smaller screens needs verification

**Priority Issues**:

- Improve instruction text formatting and clarity
- Verify modal behavior on mobile devices (need screenshots)
- Ensure modal is accessible on all screen sizes

---

## 12. Game Board: Visual Feedback & Indicators

**Purpose**: Visual cues for available actions, card states, buffs/debuffs, and special effects

### Green Highlighting for Available Actions

![Cards - Tussle Available](screenshots/laptop-2880x1800/04-cards-green-tussle-available.png)

![Cards - Archer Abilities Available](screenshots/laptop-2880x1800/08-cards-green-action-archer-abilities.png)

### Copied Card Indication

![Board - Copied Archer](screenshots/laptop-2880x1800/07-cards-showing-copied-archer.png)

### Visual feedback and indicators Key Observations

**Action Availability Indicators**:

- Green highlighting used to indicate cards with available actions
- Clear visual pattern but may need accessibility review for colorblind users
- Highlighting is prominent and effective

**Card State Indicators**:

- Copied cards need better visual distinction from originals
- Buffed/modified stats should be more clearly indicated
- Sleeped cards use graying/fading - effective

**Accessibility Concerns**:

- **Critical**: Green highlighting may not be accessible for red-green colorblind users
- Consider adding additional visual cues (icons, borders, patterns) beyond color
- Ensure sufficient contrast ratios (WCAG AA standard)

**Consistency**:

- Visual feedback patterns should be consistent across all interactions
- Hover states, selection states, and disabled states need unified design language
- Animation/transitions should be purposeful and consistent

**Priority Issues**:

- Add alternative visual indicators beyond color (icons, borders, patterns)
- Test with colorblind simulation tools
- Ensure all interactive elements have clear hover/focus states
- Document visual design system for consistency

---

## 13. Game Board: Game Messages & Play-by-Play

**Purpose**: Game history, AI reasoning, and real-time action feedback

### Play-by-Play Log Screenshots

- Laptop: ![Log](screenshots/laptop-1440x900/13-game-play-by-play.png)
- Tablet (Landscape): ![Log](screenshots/tablet-landscape-1024x768/13-game-play-by-play.png)
- Tablet (Portrait): ![Log](screenshots/tablet-portrait-768x1024/13-game-play-by-play.png)
- Phone (Portrait): ![Log](screenshots/phone-portrait-390x844/13-game-play-by-play.png)
- Phone (Landscape): ![Log](screenshots/phone-landscape-844x390/13-game-play-by-play.png)

### Game Messages and Play-by-Play Key Observations

**Log Visibility**:

- Play-by-play log placement varies across screen sizes
- Log competes with game board for space on smaller screens
- Consider collapsible/expandable log panel

**Content & Readability**:

- Text size and contrast adequate on desktop but may be challenging on mobile
- AI reasoning messages are interesting but verbose - consider summary mode
- Recent actions are clearly summarized

**Scrolling & Navigation**:

- Log should scroll independently from game board
- Auto-scroll to latest message behavior needs verification
- Consider "jump to latest" button for long games

**Information Density**:

- Play-by-play provides valuable context but can be overwhelming
- Consider filtering options (show all vs. major actions only)
- Timestamps or turn indicators would improve context

**Priority Issues**:

- Optimize log layout for mobile devices
- Add toggle to show/hide AI reasoning
- Improve text contrast and sizing for mobile
- Consider adding icons/colors to different action types for scannability

---

## 14. Victory Screen

**Purpose**: End game experience, celebration, game summary, and replay options

### Victory Screen Screenshots (Multiple Viewports)

- Laptop: ![Victory](screenshots/laptop-1440x900/SPECIAL-victory-screen.png)
- Phone (Landscape): ![Victory](screenshots/phone-landscape-844x390/SPECIAL-victory-screen.png)

### Victory Screen Modes (High-Res)

**Factual Mode**:

![Victory Screen - Factual](screenshots/laptop-2880x1800/14-victory-screen-factual.png)

**Story Mode Loading**:

![Victory Screen - Story Loading](screenshots/laptop-2880x1800/15-victory-screen-story-loading.png)

**Story Mode**:

![Victory Screen - Story Mode](screenshots/laptop-2880x1800/16-victory-screen-story-mode.png)

### Victory Screen Key Observations

**Victory Celebration**:

- Victory screen provides clear outcome but celebration could be more rewarding
- Winner announcement is clear
- Consider adding more visual flair (animations, confetti, etc.)

**Game Summary**:

- Key stats are shown but could be expanded (turns played, cards used, etc.)
- Play-by-play history is accessible - excellent feature
- Stats presentation could be more visual (charts, graphs)

**Story Mode Feature**:

- AI-generated story is engaging and unique feature
- Loading state is clear with progress indicator
- Story text is readable and well-formatted
- Story mode adds significant replay value

**Next Actions**:

- Replay/New Game options are clear
- Return to menu option present
- Consider adding share/save options for story mode
- Social sharing features could enhance engagement

**Responsive Behavior**:

- Victory screen adapts reasonably to different screen sizes
- Story mode text readability needs verification on mobile
- Modal sizing appropriate across viewports

**Priority Issues**:

- Enhance victory celebration with animations/effects
- Add expanded game statistics
- Implement story sharing/saving features
- Optimize story text formatting for mobile devices

---

# SUMMARY & ACTION PLAN

## Screenshot Coverage Status

✅ **Complete Coverage**:

- Loading screen
- Landing screen
- Lobby screens (create, join, wait)
- Leaderboard and player stats
- Deck selection
- Game board layouts (all viewports)
- Card zones (hand, play, sleep)
- Action panel states (see screenshots 08, 12 in laptop-2880x1800)
- Target selection modals (desktop + mobile phone portrait)
- Visual feedback indicators
- Victory screens (all modes)

⚠️ **Partial Coverage** (lower priority):

- Target selection on tablet viewports (not critical - phone and desktop covered)
- Action panel on tablet viewports (can extrapolate from phone/desktop)

## Critical Issues (Must Fix)

### Accessibility

1. **Color Contrast & Colorblind Support**:
   - Green highlighting for available actions not accessible for colorblind users
   - Add icons, borders, or patterns in addition to color coding
   - Test with colorblind simulation tools
   - Ensure WCAG AA contrast standards met throughout

2. **Touch Target Sizes**:
   - Verify all interactive elements meet 44x44px minimum on mobile
   - Action panel buttons may need sizing adjustments for touch
   - Card selection on mobile needs verification

3. **Keyboard Navigation**:
   - Need to verify keyboard navigation works for all interactions
   - Tab order should be logical
   - Focus indicators should be clear

### Typography & Contrast (CRITICAL - Systemic Issue)

1. **Complete Typography/Contrast Audit Required**:
   - **CRITICAL**: Multiple instances of poor text contrast throughout the application
   - Blue-on-blue text in action panel buttons (mobile screenshots)
   - White text on grey backgrounds (buttons, profile link)
   - Profile link on landing screen barely visible (white on grey)
   - "Back to Menu" button low contrast in multiple locations
   - Likely violates WCAG AA standards in numerous places
   - **Action Required**: Conduct comprehensive review of ALL text/background combinations across entire frontend
   - **Action Required**: Document all font colors, sizes, and weights used
   - **Action Required**: Test all combinations with contrast checker tools
   - **Action Required**: Establish minimum contrast ratios (4.5:1 for normal text, 3:1 for large text)

2. **Typography System Missing**:
   - No consistent font sizing scale
   - No documented color palette for text
   - No clear hierarchy (heading levels, body text, labels, etc.)
   - Button text styling inconsistent across components
   - Need comprehensive typography design tokens

### Visual Consistency

1. **Button Labels & Styling**:
   - "Back to Menu" buttons have different labels/styles across screens
   - Inconsistent contrast across different button states
   - Standardize button design system (primary, secondary, tertiary styles)
   - Create consistent spacing and sizing
   - Define hover, active, disabled, and focus states with proper contrast

2. **Component Visual Hierarchy**:
   - Phase indicator and turn information need more prominence
   - CC (currency) display too small, especially on mobile
   - Player indicators (you vs opponent) could be clearer

3. **Zone Organization**:
   - Hand, Play Zone, Sleep Zone need stronger visual separation
   - Zone headers could be more prominent
   - Card overlap in zones needs better handling

### Mobile Optimization

1. **Card Readability**:
   - Card stats (speed/strength/stamina) may be too small on mobile
   - Card effect text likely unreadable on phone screens
   - Consider card detail modal/popover for mobile

2. **Layout Adaptation**:
   - Play-by-play log competes with game board on small screens
   - Consider collapsible panels or tabs for mobile
   - Verify scrolling behavior on all screen sizes

3. **Target Selection**:
   - No screenshots available for target selection on mobile
   - Touch interaction needs verification
   - Modal sizing and card selection on small screens

## Important Issues (Should Fix)

### User Experience

1. **Onboarding & Help**:
   - No tutorial or first-time user guidance
   - No quick reference for game rules
   - Add contextual hints for complex interactions

2. **Visual Feedback**:
   - Copied cards need better distinction from originals
   - Buffed/modified stats should be more clearly indicated
   - Add hover states and interaction feedback throughout

3. **Play-by-Play Log**:
   - AI reasoning is verbose - consider summary/detail modes
   - Add filtering options (all actions vs major actions only)
   - Improve mobile layout and readability

4. **Action Panel**:
   - Visual hierarchy of actions could be improved
   - Disabled states need better contrast
   - Consider grouping related actions

### Branding & Polish

1. **Landing Screen**:
   - Missing copyright notice
   - Add "About" section with game info and repo link
   - Profile link barely visible (white on grey)
   - Icon choices may cheapen the overall aesthetic

2. **Leaderboard & Stats**:
   - Leaderboard transparency makes content hard to read
   - Player Stats panel cramped on right side - consider floating modal
   - Improve visual design and readability

3. **Victory Screen**:
   - Add more celebration/reward feel (animations, effects)
   - Expand game statistics (turns, cards used, etc.)
   - Add social sharing for story mode

## Nice to Have (Future Enhancements)

1. **Advanced Visual Features**:
   - Combat outcome prediction display in tussle selection
   - Animations for card movements and state changes

2. **Enhanced Statistics**:
   - Visual statistics (charts, graphs) in victory screen
   - Historical game tracking
   - Personal achievement system

3. **Social Features**:
   - Story mode sharing/saving
   - Share victory screens
   - Game replay sharing

4. **Responsive Enhancements**:
   - Optimize each viewport independently
   - Consider PWA features for mobile
   - Offline mode support

## Code Quality Focus Areas

Based on the review goals, the frontend codebase should focus on:

1. **Design System**:
   - **Create comprehensive typography system first** (fonts, sizes, weights, colors)
   - **Establish WCAG-compliant color pairings** for all text/background combinations
   - Create unified component library
   - Document design tokens (colors, spacing, typography)
   - Establish consistent patterns for buttons, modals, panels

2. **Responsive Patterns**:
   - Implement consistent breakpoint strategy
   - Use modern CSS layout (Grid, Flexbox) consistently
   - Mobile-first approach

3. **Accessibility Infrastructure**:
   - Semantic HTML throughout
   - ARIA labels where needed
   - Keyboard navigation support
   - Screen reader testing

4. **Component Architecture**:
   - Separate presentation from logic
   - Reusable, composable components
   - Consistent prop interfaces
   - TypeScript strict mode

## Next Steps

1. **PRIORITY 1: Complete Typography & Contrast Audit**
   - Audit ALL text/background combinations across entire frontend
   - Use WCAG contrast checker tools on every component
   - Document all instances of insufficient contrast (< 4.5:1 for normal text, < 3:1 for large text)
   - Create comprehensive report of violations

2. **PRIORITY 2: Establish Typography Design System**
   - Define font families, sizes, weights, and line heights
   - Create color palette with WCAG-compliant pairings
   - Document all button states with proper contrast ratios
   - Create typography tokens/variables for consistent use

3. **PRIORITY 3: Fix Critical Contrast Issues**
   - Blue-on-blue action panel labels
   - White-on-grey buttons (landing screen, lobby screens)
   - Profile link visibility
   - Any text below WCAG AA standards

4. **Test on actual mobile devices** (not just browser simulation)
5. **Conduct full accessibility audit** (WCAG AA compliance, keyboard navigation, screen readers)
6. **Address colorblind support** (green highlighting needs alternative indicators)
7. **Plan incremental improvements** (don't try to fix everything at once)
