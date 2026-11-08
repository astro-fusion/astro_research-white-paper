"""Statistics for testing astrological indicators against event and price series.

Every study uses these modules instead of writing its own tests, so the rigor
contract in ``docs/adr/ADR-001-flagship-research-repo.md`` is enforced in one
place:

* :mod:`.stationarity` gates any regression on ADF and KPSS.
* :mod:`.nulls` builds autocorrelation-preserving null surrogates.
* :mod:`.permutation` runs a permutation test against one of those nulls.
* :mod:`.multiplicity` corrects one family of tests (BH, BY, Bonferroni).
* :mod:`.rates` compares event rates during and outside an indicator.
* :mod:`.molchan` builds Molchan error diagrams with binomial bounds.
* :mod:`.granger` tests astro series as exogenous regressors (ADL + HAC).
* :mod:`.walk_forward` splits by time and runs Hansen's SPA test.
* :mod:`.spectral` runs Lomb-Scargle at pre-specified periods.
* :mod:`.manifest` writes the provenance ``manifest.json`` for any artifact.
* :mod:`.plots` saves figures in the house style with a provenance footer.

Every random procedure takes ``rng=np.random.default_rng(seed)``.
Submodules are imported explicitly (``from vedic_astrology_core.stats import
rates``) so importing the package does not import statsmodels.
"""
