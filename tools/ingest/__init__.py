"""Ingest validator for files produced by outside research agents (ADR-004 WP-10).

Nothing here fetches study data. It checks files in the quarantine folder
``research/incoming/`` against the contracts in docs/research/PAPER_ROADMAP.md
section 4.3, applies the machine-checkable rejection rules of section 4.4, and
promotes only person-verified rows to ``data/registry/<topic>/``.
"""
