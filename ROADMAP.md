# Roadmap

Italian Cities evolves by improving provenance and reproducibility before
claiming broader coverage. The roadmap is public, but dates are intentionally
not promised until the required sources and licences are available.

## Current: v1.1.0 prerelease

The current line establishes the engineering baseline:

- one deterministic pipeline for CSV, JSON, XLSX, SQLite and SQL;
- schema, integrity, territory, coordinate, provenance and format validators;
- Ruff, mypy, coverage and Python 3.11–3.13 CI;
- CodeQL, artifact attestations and least-privilege release publishing;
- searchable GitHub Pages with shareable filters, ISTAT regional boundaries
  and an accessible coverage table.

It remains a prerelease because CAP and coordinate values inherited from the
legacy source are not operationally verified and upstream rights for part of
that source are unresolved.

## Next: [v1.2.0 — Source reliability](https://github.com/Codewriter90x/Italian_Cities/milestone/1)

The next milestone focuses on evidence, not record-count growth:

- make source acquisition and derivative checks easier to reproduce;
- define a reviewed, licensed process for postal-code corrections;
- add safe contributor tooling and examples for evidence-backed corrections;
- improve Pages accessibility and release discovery without adding runtime
  tracking or third-party geocoding calls;
- increase targeted tests around provenance and public data contracts.

Data corrections require an authoritative or appropriately licensed source,
reference date, attribution and a reproducible transformation. The public
Nominatim service is not an accepted bulk-enrichment source.

## Later: v2.0.0 stable

A stable release requires all of the following:

- a documented legal basis for every distributed data source;
- verified or explicitly scoped postal-code provenance;
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
- silently replacing legacy values without preserving provenance;
- manually editing generated CSV, JSON, XLSX, SQLite or SQL outputs;
- claiming official, complete or operationally verified coverage without
  evidence.
