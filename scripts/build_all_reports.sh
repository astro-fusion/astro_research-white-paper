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
  QUARTO_PYTHON="$PY" quarto render "$ROOT/studies/numerology_vs_astrology/paper/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.qmd" --to pdf --profile "$profile"
  QUARTO_PYTHON="$PY" quarto render "$ROOT/studies/earthquake/paper/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd" --to pdf --profile "$profile"
  QUARTO_PYTHON="$PY" quarto render "$ROOT/studies/gold_market/paper/manuscript.qmd" --to pdf --profile "$profile"
  QUARTO_PYTHON="$PY" quarto render "$ROOT/studies/silver_market/paper/manuscript.qmd" --to pdf --profile "$profile"

  if [[ "$profile" == "generic_journal" ]]; then
    echo "==> Syncing PDFs to $ROOT/pdfs"
    mkdir -p "$ROOT/pdfs"
    cp -f "$ROOT/_site/studies/numerology_vs_astrology/paper/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.pdf" \
      "$ROOT/pdfs/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.pdf"
    cp -f "$ROOT/_site/studies/earthquake/paper/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.pdf" \
      "$ROOT/pdfs/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.pdf"
    cp -f "$ROOT/_site/studies/gold_market/paper/manuscript.pdf" \
      "$ROOT/pdfs/GOLD_MARKET_MANUSCRIPT.pdf"
    cp -f "$ROOT/_site/studies/silver_market/paper/manuscript.pdf" \
      "$ROOT/pdfs/SILVER_MARKET_MANUSCRIPT.pdf"
  fi
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
run_if_missing "$ROOT/studies/numerology_vs_astrology/data/numerology_catalog.csv" \
  "$ROOT/studies/numerology_vs_astrology/scripts/generate_numerology_catalog.py"
run_if_missing "$ROOT/studies/numerology_vs_astrology/data/numerology_daily_metrics.csv" \
  "$ROOT/studies/numerology_vs_astrology/scripts/generate_numerology_metrics.py"
run_if_missing "$ROOT/studies/numerology_vs_astrology/data/athletes_sample.csv" \
  "$ROOT/studies/numerology_vs_astrology/scripts/fetch_athletes_sample.py"
run_if_missing "$ROOT/studies/numerology_vs_astrology/data/name_numerology_metrics.csv" \
  "$ROOT/studies/numerology_vs_astrology/scripts/generate_name_numerology_metrics.py"
run_if_missing "$ROOT/studies/numerology_vs_astrology/data/personal_numerology_metrics.csv" \
  "$ROOT/studies/numerology_vs_astrology/scripts/generate_personal_numerology_metrics.py"

"$PY" "$ROOT/studies/numerology_vs_astrology/scripts/compute_athlete_name_birth_correlation.py"


echo "==> Preparing Earthquake datasets"
run_if_missing "$ROOT/studies/earthquake/data/daily_astro_base.csv" \
  "$ROOT/studies/earthquake/scripts/generate_daily_astro_features.py"
run_if_missing "$ROOT/studies/earthquake/data/combination_catalog.csv" \
  "$ROOT/studies/earthquake/scripts/generate_combination_catalog.py"
"$PY" "$ROOT/studies/earthquake/scripts/compute_combination_metrics.py"


echo "==> Running the gold and silver market pipelines"
"$PY" "$ROOT/studies/gold_market/scripts/pipeline.py" --seed 42
"$PY" "$ROOT/studies/silver_market/scripts/pipeline.py" --seed 42

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
