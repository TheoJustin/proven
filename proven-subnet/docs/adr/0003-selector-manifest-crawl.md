# ADR-0003: Feature-flagged Selector Manifest crawl

## Status
Accepted.

## Context
Miners waste effort guessing/probing the DOM for selectors. Broadcasting a
Selector Manifest removes that need and lets DOM crawling become a pure red flag.
But broadcasting selectors means reading the app's DOM, which a future
private-audit mode must be able to avoid.

## Decision
The validator builds a behaviour-first Selector Manifest
(`verification/selector_manifest.py`). Its source of truth is the Feature Area
catalogue; when enabled, a live Playwright crawl of the Reference app enriches
each element with the observed role / accessible name / attributes / state. The
crawl is feature-flagged via `--neuron.disable_selector_manifest_crawl`; when
disabled, an **empty** manifest is broadcast and no DOM is read (no selectors
exposed) — the private-audit posture. When enabled, the catalogue selectors are
enriched with the crawl's observed values; if the crawl fails, the static
catalogue manifest is the safe fallback.

## Consequences
- Miners test behaviour instead of mining selectors; probing is penalised via
  `E_i` (`verification/probing.py`).
- The crawl is injected (`run_crawl`) so the builder is unit-testable and the
  Playwright import stays lazy (module stays import-safe in CI).
- A future private-audit mode disables the crawl without code changes.
