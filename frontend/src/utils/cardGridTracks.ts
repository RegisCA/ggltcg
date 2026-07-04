/**
 * Shared fluid-grid track sizing for card zones (HandZone, InPlayZone).
 *
 * Medium cards prefer a 150px track minimum (readability floor from the
 * density pass, PR #362), but on real phones the zone grid is a hair too
 * narrow for two 150px tracks plus the gap (~290px at 375pt, ~305px at
 * 390pt — only >=393pt fits 308px). Rather than dropping to one column,
 * a pair may squeeze to the 140px floor: the track minimum is
 *   min(150px, max(140px, half the row minus half the gap))
 * so wide layouts keep the 150px floor, phone rows stay 2-up down to
 * ~2*140px+gap containers, and anything narrower falls back to 1-up.
 * The extra 100% bound keeps a single track from overflowing zones
 * narrower than the squeeze floor (paired zones at phone widths).
 */

const MEDIUM_TRACK_MIN =
  'min(var(--spacing-card-medium-min-w), 100%, max(var(--spacing-card-medium-squeeze-w), calc(50% - var(--spacing-component-xs) / 2)))';

const SMALL_TRACK_MIN = 'min(var(--spacing-card-small-w), 100%)';

export function cardGridTemplateColumns(size: 'small' | 'medium'): string {
  return `repeat(auto-fill, minmax(${size === 'small' ? SMALL_TRACK_MIN : MEDIUM_TRACK_MIN}, 1fr))`;
}
