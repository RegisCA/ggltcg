/**
 * Paper & Ink — card identity ("crayon") + ownership material helpers.
 *
 * Design system: docs/plans/DESIGN_SYSTEM_PAPER_AND_INK.md §2 (crayon set) and
 * §1/§4 (ownership materials). This is the load-bearing foundation every card
 * surface derives its colors from — see docs/plans/DESIGN_SYSTEM_IMPLEMENTATION.md.
 *
 * Two ideas live here, deliberately separate:
 *   1. IDENTITY — a card's backend `primary_color` snaps to one of seven crayons.
 *      Identity color is decoration only (frame border, cost box, brackets); it
 *      carries NO rules meaning (§2).
 *   2. MATERIAL — a card's surface is bound to its OWNER (`card.owner`, never
 *      `controller` — §1): the local player's cards are always cream paper, the
 *      opponent's always dark ink, in every zone. Stolen cards keep the original
 *      owner's material.
 */

/** The seven crayons (§2). No rules meaning — card identity only. */
export const CRAYONS = {
  red: '#C74444',
  orange: '#D98E1F',
  green: '#4C9A57',
  blue: '#4A7BB5',
  purple: '#8B5FA8',
  pink: '#D6559C',
  sky: '#6FA8C9',
} as const;

export type CrayonName = keyof typeof CRAYONS;

/**
 * Explicit identity mapping for every `primary_color` currently in
 * backend/data/cards.csv (keys lowercased). Hand-curated rather than purely
 * distance-based because several backend hexes are near-ties in RGB space where
 * Euclidean nearest picks the perceptually wrong crayon (e.g. the dark purple
 * #4a0e4e and the pale gold #ffeb99). Unknown/future colors fall back to
 * `nearestCrayon`.
 */
const KNOWN_COLOR_CRAYON: Record<string, CrayonName> = {
  '#c74444': 'red', // Beary, Knight, Archer, Umbruh, Ka, Ballaber
  '#cc5500': 'orange',
  '#eb9113': 'orange', // Drum, Violin, Gibbers, Belchaletta, Hind Leg Kicker
  '#ffeb99': 'orange', // Rush (pale gold, orange accent)
  '#8b5fa8': 'purple', // Wake, Sun, Toynado
  '#4a0e4e': 'purple', // Monster, MaBookBook (dark royal purple)
  '#d8c7fa': 'purple', // Dream (lavender)
  '#87ceeb': 'sky', // Bubble Blocker, Paper Plane
  '#ffb6c1': 'pink', // Clone, Glue, Stomp, Cake
  '#e612d0': 'pink', // Surge, Drop, Jumpscare, VeryVeryAppleJuice (magenta)
};

const DEFAULT_CRAYON: CrayonName = 'red';

/**
 * Cost-box numeral color (§4: "cost numeral in the face color"). The cost box is
 * filled with the identity crayon; the numeral reads as cut out of the face.
 * On paper that's always the cream face. On ink a dark numeral vanishes against a
 * dark crayon, so light crayons (orange/sky) keep the dark face color and dark
 * crayons (red/purple/…) flip to the light ink text — matching the mockup
 * (Ka red → light, Gibbers orange → dark).
 */
export function costNumeralColor(crayonHex: string, isOwn: boolean): string {
  if (isOwn) return 'var(--paper)';
  return relativeLuminance(crayonHex) > 0.3 ? 'var(--desk-bottom)' : 'var(--ink-text)';
}

/** WCAG relative luminance (0 dark – 1 light) of a hex color. */
function relativeLuminance(hex: string): number {
  const rgb = parseHex(hex);
  if (!rgb) return 0;
  const [r, g, b] = rgb.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function parseHex(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff];
}

/** Nearest crayon by Euclidean RGB distance — fallback for unmapped colors. */
function nearestCrayon(hex: string): CrayonName {
  const rgb = parseHex(hex);
  if (!rgb) return DEFAULT_CRAYON;
  let best: CrayonName = DEFAULT_CRAYON;
  let bestDist = Infinity;
  for (const [name, cray] of Object.entries(CRAYONS) as [CrayonName, string][]) {
    const c = parseHex(cray)!;
    const dist = Math.hypot(rgb[0] - c[0], rgb[1] - c[1], rgb[2] - c[2]);
    if (dist < bestDist) {
      bestDist = dist;
      best = name;
    }
  }
  return best;
}

/**
 * Snap a backend `primary_color` to its identity crayon name.
 * Known values use the curated table; anything else uses nearest-color.
 */
export function crayonNameForColor(primaryColor: string | null | undefined): CrayonName {
  if (!primaryColor) return DEFAULT_CRAYON;
  const key = primaryColor.trim().toLowerCase();
  return KNOWN_COLOR_CRAYON[key] ?? nearestCrayon(key);
}

/** Snap a backend `primary_color` to its identity crayon hex (§4 borders/brackets/cost box). */
export function crayonForColor(primaryColor: string | null | undefined): string {
  return CRAYONS[crayonNameForColor(primaryColor)];
}

/**
 * Ownership material (§1/§4). Returned values are `var(--token)` strings so they
 * resolve against the Paper & Ink palette in index.css and stay theme-correct.
 *
 * `isOwn` is derived from `cardOwner === localPlayerId` — pass the OWNER field,
 * never the controller, so a stolen card keeps its original owner's material.
 */
export interface CardMaterial {
  /** True when the local player owns this card (cream paper); false = opponent (ink). */
  isOwn: boolean;
  /** Card face surface. */
  surface: string;
  /** Primary text (name, stat values). */
  text: string;
  /** Effect text. */
  textMuted: string;
  /** Stat labels, metadata. */
  textFaint: string;
  /** Buffed stat numerals (AA-safe per surface). */
  buffed: string;
  /** Damaged / debuffed stat numerals + BROKEN stamp (AA-safe per surface). */
  danger: string;
}

const PAPER_MATERIAL: Omit<CardMaterial, 'isOwn'> = {
  surface: 'var(--paper)',
  text: 'var(--paper-ink-text)',
  textMuted: 'var(--paper-muted)',
  textFaint: 'var(--paper-faint)',
  buffed: 'var(--gold-on-paper)',
  danger: 'var(--danger-on-paper)',
};

const INK_MATERIAL: Omit<CardMaterial, 'isOwn'> = {
  surface: 'var(--ink)',
  text: 'var(--ink-text)',
  textMuted: 'var(--ink-muted)',
  textFaint: 'var(--ink-faint)',
  buffed: 'var(--gold)',
  danger: 'var(--danger)',
};

/** Material from an already-resolved ownership boolean (cream paper if own, ink if not). */
export function materialFor(isOwn: boolean): CardMaterial {
  return { isOwn, ...(isOwn ? PAPER_MATERIAL : INK_MATERIAL) };
}

export function materialForOwner(cardOwner: string, localPlayerId: string): CardMaterial {
  return materialFor(cardOwner === localPlayerId);
}
