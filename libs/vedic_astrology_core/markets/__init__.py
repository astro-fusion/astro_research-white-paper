"""Market series versus astrological indicators (ADR-001, review section 6).

* :mod:`.fetch`: FRED and Yahoo adapters returning one tidy frame
  (``date, close, source, series_id, is_futures``) and hashed snapshots.
* :mod:`.align`: one calendar for prices and indicators; windows in bars.
* :mod:`.features`: engine-computed daily indicator frames and rule firings.
* :mod:`.event_study`: forward returns after events with block-bootstrap bands.
* :mod:`.overlay`: the tidy overlay frame and the standard overlay figure.
* :mod:`.study`: the shared study pipeline driven by ``hypothesis.yaml``.

Submodules are imported explicitly, e.g.
``from vedic_astrology_core.markets import fetch``.
"""
