#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Missing virtualenv python at $PY"
  exit 1
fi

PROFILE="${1:-generic_journal}"
FORCE="${FORCE:-0}"

render_one() {
  local profile="$1"
  echo "==> Rendering reports with profile: $profile"
  QUARTO_PYTHON="$PY" quarto render "$ROOT/use_cases/numerology/research_paper/numerology_astrology_correlation.qmd" --to pdf --profile "$profile"
  QUARTO_PYTHON="$PY" quarto render "$ROOT/docs/research/track_2_earthquake_prediction/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd" --to pdf --profile "$profile"
  QUARTO_PYTHON="$PY" quarto render "$ROOT/docs/research/track_3_gold_market/GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.qmd" --to pdf --profile "$profile"
}

run_if_missing() {
  local target="$1"
  local script="$2"
  if [[ "$FORCE" == "1" || ! -f "$target" ]]; then
    echo "==> Generating $target"
    "$PY" "$script"
  fi
}

echo "==> Preparing Numerology datasets"
run_if_missing "$ROOT/data/vedic_principles_catalog.csv" \
  "$ROOT/scripts/generate_vedic_principles_catalog.py"
run_if_missing "$ROOT/use_cases/numerology/research_paper/data/numerology_catalog.csv" \
  "$ROOT/use_cases/numerology/research_paper/scripts/generate_numerology_catalog.py"
run_if_missing "$ROOT/use_cases/numerology/research_paper/data/numerology_daily_metrics.csv" \
  "$ROOT/use_cases/numerology/research_paper/scripts/generate_numerology_metrics.py"
run_if_missing "$ROOT/use_cases/numerology/research_paper/data/athletes_sample.csv" \
  "$ROOT/use_cases/numerology/research_paper/scripts/fetch_athletes_sample.py"
run_if_missing "$ROOT/use_cases/numerology/research_paper/data/name_numerology_metrics.csv" \
  "$ROOT/use_cases/numerology/research_paper/scripts/generate_name_numerology_metrics.py"
run_if_missing "$ROOT/use_cases/numerology/research_paper/data/personal_numerology_metrics.csv" \
  "$ROOT/use_cases/numerology/research_paper/scripts/generate_personal_numerology_metrics.py"

"$PY" "$ROOT/use_cases/numerology/research_paper/scripts/compute_athlete_name_birth_correlation.py"


echo "==> Preparing Earthquake datasets"
run_if_missing "$ROOT/docs/research/track_2_earthquake_prediction/data/daily_astro_base.csv" \
  "$ROOT/docs/research/track_2_earthquake_prediction/scripts/generate_daily_astro_features.py"
run_if_missing "$ROOT/docs/research/track_2_earthquake_prediction/data/combination_catalog.csv" \
  "$ROOT/docs/research/track_2_earthquake_prediction/scripts/generate_combination_catalog.py"
"$PY" "$ROOT/docs/research/track_2_earthquake_prediction/scripts/compute_combination_metrics.py"


echo "==> Preparing Gold datasets"
run_if_missing "$ROOT/docs/research/track_3_gold_market/data/gold_prices.csv" \
  "$ROOT/docs/research/track_3_gold_market/scripts/fetch_gold_data.py"
run_if_missing "$ROOT/docs/research/track_3_gold_market/data/gold_astro_catalog.csv" \
  "$ROOT/docs/research/track_3_gold_market/scripts/generate_gold_astro_catalog.py"
run_if_missing "$ROOT/docs/research/track_3_gold_market/data/gold_astro_features.csv" \
  "$ROOT/docs/research/track_3_gold_market/scripts/generate_gold_astro_features.py"
"$PY" "$ROOT/docs/research/track_3_gold_market/scripts/compute_gold_astro_metrics.py"

echo "==> Building Vedic coverage matrix"
"$PY" "$ROOT/scripts/generate_vedic_principles_coverage.py"

if [[ "$PROFILE" == "all" ]]; then
  PROFILES=("generic_journal" "ieee_like" "springer_like" "elsevier_like" "nature_like")
  for prof in "${PROFILES[@]}"; do
    render_one "$prof"
  done
else
  render_one "$PROFILE"
fi

echo "==> Done"
