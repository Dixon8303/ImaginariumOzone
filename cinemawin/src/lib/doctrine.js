// Doctrine constants, read from the same doctrine.json the Python backend
// loads. Changing a number there changes it in both places.
import doctrine from "../../doctrine.json";

export const SCORE_CATEGORIES = doctrine.score_categories;
export const VERDICT_THRESHOLDS = doctrine.verdict_thresholds;
export const MATURITY_LABELS = doctrine.maturity_labels;
export const CAPITAL_LAYERS = doctrine.capital_layers;
export const EQUITY_GAP_LAYER = doctrine.equity_gap_layer;
export const BUDGET_TIERS = doctrine.budget_tiers;
export const DECK_SLIDE_TITLES = doctrine.deck_slide_titles;
export const WATERFALL_STEPS = doctrine.waterfall_steps;
export const STRUCTURE_SEQUENCE_COUNT = doctrine.structure_sequence_count;
export const PLANS = doctrine.plans;
export const TRACKS = doctrine.tracks;

export function verdictForTotal(total) {
  for (const [min, verdict, label] of VERDICT_THRESHOLDS) {
    if (total >= min) return { verdict, label };
  }
  const [, verdict, label] = VERDICT_THRESHOLDS[VERDICT_THRESHOLDS.length - 1];
  return { verdict, label };
}

export function tierForCeiling(ceiling) {
  for (const [upper, tier] of BUDGET_TIERS) {
    if (upper === null || ceiling < upper) return tier;
  }
  return BUDGET_TIERS[BUDGET_TIERS.length - 1][1];
}

export default doctrine;
