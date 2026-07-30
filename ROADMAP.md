# Roadmap

Italian Cities evolves by improving provenance and reproducibility before
claiming broader coverage. The roadmap is public, but dates are intentionally
not promised until the required sources and licences are available.

## Current: v2.0.0 clean-room prerelease

The current line replaces the unresolved legacy source with:

- all municipalities from the declared ISTAT snapshot;
- GeoNames Postal Codes IT with CC BY 4.0 attribution;
- conservative exact reconciliation and explicit unmatched/ambiguous states;
- one deterministic pipeline for CSV, JSON, XLSX, SQLite, SQL and Pages;
- schema, integrity, territory, coordinate, provenance and format validators;
- Ruff, mypy, coverage and Python 3.11–3.13 CI;
- CodeQL, artifact attestations and least-privilege release publishing;
- searchable GitHub Pages with shareable filters, ISTAT regional boundaries
  and an accessible coverage table.

It is published as a prerelease because GeoNames is not Poste Italiane and
CAP and coordinates are not operationally certified.

## Next: v2.1.0 — reviewed reconciliation

The next milestone focuses on evidence, not record-count growth:

- review unmatched and historical-province cases without fuzzy promotion;
- define an authorized process for postal-code corrections;
- add source-update tooling and migration aliases for changed identities;
- improve Pages accessibility and release discovery without adding runtime
  tracking or third-party geocoding calls;
- increase targeted tests around provenance and public data contracts.

Data corrections require an authoritative or appropriately licensed source,
reference date, attribution and a reproducible transformation. The public
Nominatim service is not an accepted bulk-enrichment source.

## Later: stable operational line

A stable release requires all of the following:

- a documented compatible official source for operational postal validation;
- a current and complete administrative reference, with migrations documented;
- coordinate provenance that distinguishes authoritative, derived and missing
  values;
- a published compatibility and deprecation policy for schema changes.

Until those gates are satisfied, prerelease status is a feature: it prevents
the repository from implying guarantees the data cannot support.

## Good first contributions

Beginner-friendly work is tracked with the
[`good first issue`](https://github.com/Codewriter90x/Italian_Cities/labels/good%20first%20issue)
label. These issues are deliberately limited to documentation, tests,
accessibility or tooling. Unsupervised bulk data edits are not beginner tasks.

For larger proposals, open a
[Discussion](https://github.com/Codewriter90x/Italian_Cities/discussions)
before implementing a new source or changing the schema.

## Out of scope

- scraping or bulk geocoding against services that prohibit systematic use;
- treating a CAP as a unique place identifier;
- silently replacing source values without preserving provenance;
- manually editing generated CSV, JSON, XLSX, SQLite or SQL outputs;
- claiming official, complete or operationally verified coverage without
  evidence.
