# ADR-002: The bridge between the upstream dataset and this research repo

Status: accepted 2026-11-08.

## Decision

1. Two systems, two storage models, by design. The upstream dataset is maintained
   privately by the project owner. This repository is file-based (YAML, JSONL,
   hashed CSV snapshots, JSON results) so that anyone can reproduce a result with
   no infrastructure and a reviewer can verify every input by hash.
2. They connect through a **data contract and a ledger**, never through shared code
   or shared storage. This repository never imports from the upstream; the
   upstream never reads this repository at runtime.
3. Direction of flow:
   - Upstream to research: data bundles (countries, events, eclipses) exported on
     demand by tooling that lives outside this repository.
   - Research to upstream (later, optional): verified rules and candidate charts,
     pulled by the upstream at a pinned commit of this repository.
4. This repository knows that an upstream dataset owner exists and what the bundle
   looks like. It does not describe the upstream's internals.

## Public half

- "Some datasets in this repository are exported from a private upstream dataset
  maintained by the project owner. The upstream is not part of this repository and
  is not required to reproduce anything here."
- Bundle schema (fields and types for `countries.yaml`, `events.jsonl`,
  `eclipses.csv`) and the `UPSTREAM.yaml` stamp (`bundle_version`, `exported_at`,
  `row_counts`, `sha256`, `exporter_commit` as an opaque hash). Licence: CC BY 4.0
  for the bundle. All of this lives in `docs/UPSTREAM_CONTRACT.md`.
- What this repository promises back: rules in `rules/**` and candidate charts are
  the canonical open versions; the upstream may consume them at a pinned commit.
- A test (`tests/test_upstream_stamp.py`) that `UPSTREAM.yaml` hashes match the
  committed bundle files, so a stale or hand-edited bundle is caught.
- A pointer in `CONTRIBUTING.md`: do not add anything that describes the
  upstream's internals; see `docs/UPSTREAM_CONTRACT.md`.

## Why this shape

- A future agent finds one file that explains the other side and the rules of
  movement, without the public file leaking architecture.
- Hash stamps make the bundle verifiable without trusting the exporter.

## Work packages

| WP | Scope | Blocked on |
|---|---|---|
| B-1 | `docs/UPSTREAM_CONTRACT.md`, `UPSTREAM.yaml` for the current bundle, stamp test, contributor note | none |
