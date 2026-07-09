/**
 * PostHog analytics wrapper.
 *
 * All functions no-op unless VITE_POSTHOG_KEY is set, so local dev, CI,
 * and tests emit nothing. Event names and properties are the contract
 * shared with the backend enrichment push (game_analyzed) — keep the
 * two vocabularies consistent.
 */

import posthog from 'posthog-js';
import type { User } from '../types/auth';

let initialized = false;

export function initAnalytics(): void {
  const key = import.meta.env.VITE_POSTHOG_KEY;
  if (!key) return;

  posthog.init(key, {
    api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com',
    // Only authenticated users play; profiles are created on identify()
    person_profiles: 'identified_only',
  });
  initialized = true;
}

/**
 * Tie events to the authenticated user. Uses the Google ID as distinct_id —
 * the same ID the backend uses for player_id, which is what lets the
 * server-side game_analyzed events join to the same person.
 */
export function identifyUser(user: User): void {
  if (!initialized) return;
  posthog.identify(user.google_id, {
    display_name: user.custom_display_name || user.display_name,
  });
}

/** Clear the identity on logout so a shared device doesn't cross-pollinate. */
export function resetAnalytics(): void {
  if (!initialized) return;
  posthog.reset();
}

export type OpponentType = 'ai' | 'human';

export function captureLobbyCreated(): void {
  capture('lobby_created');
}

export function captureLobbyJoined(): void {
  capture('lobby_joined');
}

export function captureGameStarted(props: {
  game_id: string;
  opponent_type: OpponentType;
  quick_play?: boolean;
  hidden_cards?: boolean;
}): void {
  capture('game_started', props);
}

export function captureGameCompleted(props: {
  game_id: string;
  opponent_type: OpponentType;
  turn_number: number;
  is_winner: boolean;
}): void {
  capture('game_completed', props);
}

function capture(event: string, props?: Record<string, unknown>): void {
  if (!initialized) return;
  posthog.capture(event, props);
}
