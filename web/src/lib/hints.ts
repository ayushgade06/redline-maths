/** Hints unlock strictly in order: 1 (nudge) → 2 (concept) → 3 (parallel example). */
export function nextHintLevel(revealed: Partial<Record<1 | 2 | 3, unknown>>): 1 | 2 | 3 | null {
  for (const lvl of [1, 2, 3] as const) if (!revealed[lvl]) return lvl;
  return null;
}

export const HINT_LABELS = { 1: "Nudge", 2: "Explain the idea", 3: "Show a similar example" } as const;
