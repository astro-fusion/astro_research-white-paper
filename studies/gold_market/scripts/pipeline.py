"""Gold-market study: run the shared, pre-registered market pipeline.

Usage::

    python studies/gold_market/scripts/pipeline.py --seed 42 [--offline]

Everything the study does is declared in ``studies/gold_market/hypothesis.yaml``;
the pipeline itself is :mod:`vedic_astrology_core.markets.study`.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO), str(REPO / "libs")]

from studies._paths import artifacts_dir, study_dir  # noqa: E402
from vedic_astrology_core.markets.study import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(
        main(
            study_dir("gold_market") / "hypothesis.yaml",
            artifacts_dir("gold_market"),
            REPO,
        )
    )
