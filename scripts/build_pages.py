#!/usr/bin/env python3
"""Build the deterministic static GitHub Pages site."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from pages_model import (
    WEB_FIELDS,
    calculate_stats,
    format_integer,
    read_locations,
    slugify,
)
from project_metadata import (
    BUILD_DATE,
    DATASET_VERSION,
    GEONAMES_REFERENCE_DATE,
    ISTAT_REFERENCE_DATE,
    OPERATIONAL_DATA_READINESS,
    RELEASE_STATUS,
    SCHEMA_VERSION,
    STRUCTURAL_QUALITY,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SITE = REPOSITORY_ROOT / "site"
CANONICAL_DATA = REPOSITORY_ROOT / "data" / "italian_locations.csv"
SOCIAL_PREVIEW = REPOSITORY_ROOT / "assets" / "social-preview.jpg"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "dist" / "pages"
RELEASE_VERSION = DATASET_VERSION
SITE_ROOT = "https://codewriter90x.github.io/Italian_Cities/"
REPOSITORY_URL = "https://github.com/Codewriter90x/Italian_Cities"
RELEASE_URL = f"{REPOSITORY_URL}/releases/tag/{RELEASE_VERSION}"
RELEASE_DOWNLOAD_ROOT = (
    f"{REPOSITORY_URL}/releases/download/{RELEASE_VERSION}"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_asset_url(name: str) -> str:
    return f"{RELEASE_DOWNLOAD_ROOT}/{name}"


def municipality_path(row: dict[str, Any]) -> str:
    return (
        f"comuni/{row['municipality_istat_code']}-"
        f"{slugify(row['name'])}/"
    )


def structured_data(stats: dict[str, Any]) -> str:
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{SITE_ROOT}#website",
                "url": SITE_ROOT,
                "name": "Italian Cities",
                "description": (
                    "Dataset open data di comuni italiani, CAP non ufficiali, "
                    "località e coordinate."
                ),
                "inLanguage": "it-IT",
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": {
                        "@type": "EntryPoint",
                        "urlTemplate": f"{SITE_ROOT}?q={{search_term_string}}#search",
                    },
                    "query-input": "required name=search_term_string",
                },
            },
            {
                "@type": "Dataset",
                "@id": f"{SITE_ROOT}#dataset",
                "name": "Italian Cities",
                "alternateName": "Dataset comuni italiani, CAP e coordinate",
                "description": (
                    f"Dataset open data {RELEASE_VERSION} con "
                    f"{format_integer(stats['municipalities'])} comuni ISTAT, "
                    f"{format_integer(stats['unique_postal_codes'])} CAP "
                    "GeoNames non ufficiali, località e coordinate."
                ),
                "url": SITE_ROOT,
                "version": RELEASE_VERSION.removeprefix("v"),
                "dateModified": BUILD_DATE,
                "inLanguage": "it-IT",
                "isAccessibleForFree": True,
                "license": "https://creativecommons.org/licenses/by/4.0/",
                "keywords": [
                    "comuni italiani",
                    "CAP italiani",
                    "codici ISTAT",
                    "coordinate geografiche",
                    "open data Italia",
                    "CSV",
                    "GeoNames",
                ],
                "spatialCoverage": "Italia",
                "creator": {
                    "@type": "Person",
                    "name": "Codewriter90x",
                    "url": "https://github.com/Codewriter90x",
                },
                "citation": [
                    "https://www.istat.it/",
                    "https://www.geonames.org/",
                ],
                "distribution": [
                    {
                        "@type": "DataDownload",
                        "encodingFormat": media_type,
                        "contentUrl": release_asset_url(filename),
                    }
                    for filename, media_type in (
                        ("italian_locations.csv", "text/csv"),
                        ("italian_locations.json", "application/json"),
                        (
                            "italian_locations.xlsx",
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet",
                        ),
                        ("italian_locations.sqlite", "application/vnd.sqlite3"),
                        ("italian_locations.sql", "application/sql"),
                        ("SHA256SUMS", "text/plain"),
                    )
                ],
            },
            {
                "@type": "FAQPage",
                "@id": f"{SITE_ROOT}#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "I CAP del dataset sono ufficiali?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": (
                                "No. I CAP provengono dal dump GeoNames e non "
                                "da Poste Italiane; non sono dati postali "
                                "certificati."
                            ),
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Quali formati sono disponibili?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": (
                                "La release offre CSV, JSON, XLSX, SQLite e "
                                "SQL, generati dalla stessa vista canonica."
                            ),
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Quali fonti usa Italian Cities?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": (
                                "I comuni e i codici amministrativi provengono "
                                "da ISTAT; località, CAP e coordinate da "
                                "GeoNames. Entrambe le fonti sono attribuite "
                                "CC BY 4.0."
                            ),
                        },
                    },
                ],
            },
        ],
    }
    return json.dumps(graph, ensure_ascii=False, separators=(",", ":"))


def render_homepage(output: Path, stats: dict[str, Any]) -> None:
    template_path = SOURCE_SITE / "index.html"
    source = template_path.read_text(encoding="utf-8")
    values = {
        "BUILD_DATE": BUILD_DATE,
        "DATASET_VERSION": RELEASE_VERSION,
        "GEONAMES_REFERENCE_DATE": GEONAMES_REFERENCE_DATE,
        "ISTAT_REFERENCE_DATE": ISTAT_REFERENCE_DATE,
        "JSON_LD": structured_data(stats),
        "MUNICIPALITIES": format_integer(stats["municipalities"]),
        "POSTAL_CODE_RELATIONS": format_integer(stats["postal_code_relations"]),
        "RELEASE_DOWNLOAD_ROOT": RELEASE_DOWNLOAD_ROOT,
        "RELEASE_STATUS_LABEL": (
            "prerelease pubblicata"
            if RELEASE_STATUS == "prerelease"
            else "release stabile"
        ),
        "RELEASE_URL": RELEASE_URL,
        "UNIQUE_POSTAL_CODES": format_integer(stats["unique_postal_codes"]),
        "WITH_COORDINATES": format_integer(stats["with_coordinates"]),
    }
    for name, value in values.items():
        source = source.replace(f"{{{{{name}}}}}", str(value))
    unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", source)))
    if unresolved:
        raise ValueError(f"Unresolved homepage template tokens: {unresolved}")
    (output / "index.html").write_text(source, encoding="utf-8")


def page_document(
    *,
    title: str,
    description: str,
    canonical_path: str,
    body: str,
    page_type: str = "WebPage",
    extra_structured_data: dict[str, Any] | None = None,
) -> str:
    canonical = f"{SITE_ROOT}{canonical_path}"
    page_entry: dict[str, Any] = {
        "@type": page_type,
        "@id": f"{canonical}#page",
        "url": canonical,
        "name": title,
        "description": description,
        "dateModified": BUILD_DATE,
        "inLanguage": "it-IT",
        "isPartOf": {"@id": f"{SITE_ROOT}#website"},
    }
    graph: list[dict[str, Any]] = [page_entry]
    if extra_structured_data:
        if page_type == "ProfilePage" and extra_structured_data.get("@id"):
            page_entry["mainEntity"] = {
                "@id": extra_structured_data["@id"]
            }
        graph.append(extra_structured_data)
    json_ld = json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    escaped_title = html.escape(title)
    escaped_description = html.escape(description, quote=True)
    return f"""<!doctype html>
<html lang="it">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escaped_title} — Italian Cities</title>
    <meta name="description" content="{escaped_description}">
    <meta name="robots" content="index, follow, max-image-preview:large">
    <meta name="theme-color" content="#081522">
    <meta property="og:type" content="website">
    <meta property="og:locale" content="it_IT">
    <meta property="og:site_name" content="Italian Cities">
    <meta property="og:title" content="{escaped_title}">
    <meta property="og:description" content="{escaped_description}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:image" content="{SITE_ROOT}assets/social-preview.jpg">
    <meta property="og:image:width" content="1280">
    <meta property="og:image:height" content="640">
    <meta property="og:image:alt" content="Italian Cities, open dataset geografico italiano">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="canonical" href="{canonical}">
    <link rel="icon" href="{SITE_ROOT}favicon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="{SITE_ROOT}assets/styles.css">
    <script type="application/ld+json">{json_ld}</script>
  </head>
  <body>
    <a class="skip-link" href="#content">Vai al contenuto</a>
    <header class="site-header">
      <a class="brand" href="{SITE_ROOT}">
        <span class="brand-mark" aria-hidden="true"></span>Italian Cities
      </a>
      <nav class="site-nav" aria-label="Navigazione principale">
        <a href="{SITE_ROOT}dataset/">Dataset</a>
        <a href="{SITE_ROOT}regioni/">Regioni</a>
        <a href="{REPOSITORY_URL}">GitHub</a>
      </nav>
    </header>
    <main class="content-page" id="content">
      {body}
    </main>
    <footer class="site-footer">
      <p>Italian Cities {RELEASE_VERSION} · dati ISTAT e GeoNames CC BY 4.0.</p>
      <p><a href="{REPOSITORY_URL}/issues/new/choose">Segnala una correzione</a></p>
    </footer>
  </body>
</html>
"""


def write_page(output: Path, relative_path: str, document: str) -> str:
    target = output / relative_path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return f"{relative_path}/"


def build_information_pages(
    output: Path,
    rows: list[dict[str, Any]],
    stats: dict[str, Any],
) -> list[str]:
    pages: list[str] = []
    version = html.escape(RELEASE_VERSION)
    dataset_body = f"""
      <nav class="breadcrumbs" aria-label="Percorso"><a href="{SITE_ROOT}">Home</a> / Dataset</nav>
      <p class="eyebrow">Open data geografici italiani</p>
      <h1>Dataset dei comuni italiani, CAP e coordinate</h1>
      <p class="content-lead">Italian Cities {version} raccoglie
        {format_integer(stats['municipalities'])} comuni ISTAT,
        {format_integer(stats['postal_code_relations'])} relazioni luogo–CAP e
        {format_integer(stats['with_coordinates'])} luoghi con coordinate.
        CAP e coordinate GeoNames non sono dati postali ufficiali.</p>
      <div class="content-grid">
        <article class="content-card"><h2>Cosa contiene</h2><p>Comuni, codici
          ISTAT, province, regioni, località GeoNames, CAP a cinque cifre,
          coordinate WGS84 e campi di provenienza.</p></article>
        <article class="content-card"><h2>Formati</h2><p>CSV, JSON, XLSX,
          SQLite e SQL sono prodotti dalla stessa pipeline deterministica.</p></article>
        <article class="content-card"><h2>Qualità dichiarata</h2><p>I controlli
          strutturali sono superati; l'idoneità operativa resta sperimentale e
          non ufficiale.</p></article>
      </div>
      <section class="content-section"><h2>Download della release {version}</h2>
        <p>Gli asset sono accompagnati da checksum SHA-256. La v2.0.0
          pubblicata precede l'abilitazione dell'immutabilità GitHub del 30
          luglio 2026; le release future usano il flusso
          draft–upload–publish.</p>
        <div class="download-actions">
          <a class="button" href="{release_asset_url('italian_locations.csv')}">CSV</a>
          <a class="button secondary" href="{release_asset_url('italian_locations.json')}">JSON</a>
          <a class="button secondary" href="{release_asset_url('italian_locations.xlsx')}">XLSX</a>
          <a class="button secondary" href="{release_asset_url('italian_locations.sqlite')}">SQLite</a>
          <a class="button secondary" href="{release_asset_url('italian_locations.sql')}">SQL</a>
          <a class="button secondary" href="{release_asset_url('SHA256SUMS')}">SHA256SUMS</a>
        </div>
      </section>
      <section class="content-section"><h2>Documentazione</h2>
        <ul class="resource-list">
          <li><a href="{SITE_ROOT}schema/">Schema delle colonne</a></li>
          <li><a href="{SITE_ROOT}fonti/">Fonti, licenze e limiti</a></li>
          <li><a href="{SITE_ROOT}regioni/">Copertura per regione</a></li>
          <li><a href="{RELEASE_URL}">Note della release {version}</a></li>
        </ul>
      </section>
    """
    pages.append(
        write_page(
            output,
            "dataset",
            page_document(
                title="Dataset comuni italiani, CAP e coordinate",
                description=(
                    "Scarica il dataset open data dei comuni italiani con "
                    "codici ISTAT, CAP GeoNames, località e coordinate in CSV, "
                    "JSON, XLSX, SQLite e SQL."
                ),
                canonical_path="dataset/",
                body=dataset_body,
                page_type="CollectionPage",
            ),
        )
    )

    schema_body = f"""
      <nav class="breadcrumbs" aria-label="Percorso"><a href="{SITE_ROOT}">Home</a> / Schema</nav>
      <p class="eyebrow">Schema {SCHEMA_VERSION}</p>
      <h1>Schema del dataset Italian Cities</h1>
      <p class="content-lead">La v2 separa comuni, località e relazioni CAP.
        Identificativi e CAP restano stringhe per preservare gli zeri iniziali.</p>
      <div class="content-grid">
        <article class="content-card"><h2>municipalities.csv</h2><p>Una riga
          per comune ISTAT, con codice amministrativo, territorio, coordinate
          opzionali e provenienza.</p></article>
        <article class="content-card"><h2>localities.csv</h2><p>Località
          GeoNames non riconciliate in modo univoco con un comune.</p></article>
        <article class="content-card"><h2>postal_codes.csv</h2><p>Relazioni
          molti-a-molti fra luogo e CAP; il CAP non è una chiave univoca.</p></article>
        <article class="content-card"><h2>italian_locations.*</h2><p>Vista
          unificata esportata in CSV, JSON, XLSX, SQLite e SQL.</p></article>
      </div>
      <section class="content-section"><h2>Campi principali</h2>
        <div class="table-scroll"><table class="schema-table">
          <thead><tr><th>Campo</th><th>Significato</th></tr></thead>
          <tbody>
            <tr><td><code>location_id</code></td><td>Identificativo stabile del comune o della località.</td></tr>
            <tr><td><code>municipality_istat_code</code></td><td>Codice ISTAT a sei cifre, presente sui comuni.</td></tr>
            <tr><td><code>postal_code</code></td><td>CAP GeoNames a cinque cifre oppure vuoto con stato missing.</td></tr>
            <tr><td><code>province_code</code></td><td>Sigla della provincia.</td></tr>
            <tr><td><code>latitude</code>, <code>longitude</code></td><td>Coordinate WGS84 opzionali.</td></tr>
            <tr><td><code>coordinate_verification</code></td><td>Origine e tipo di riconciliazione; non certifica l'accuratezza geografica.</td></tr>
            <tr><td><code>source_ids</code></td><td>Fonti canoniche che contribuiscono al record.</td></tr>
          </tbody>
        </table></div>
        <p><a href="{REPOSITORY_URL}/blob/main/SCHEMA.md">Consulta lo schema tecnico completo</a>.</p>
      </section>
    """
    pages.append(
        write_page(
            output,
            "schema",
            page_document(
                title="Schema CSV, JSON, SQLite e SQL",
                description=(
                    "Schema e significato delle colonne del dataset Italian "
                    "Cities: comuni ISTAT, località, CAP, coordinate e "
                    "provenienza."
                ),
                canonical_path="schema/",
                body=schema_body,
                page_type="TechArticle",
            ),
        )
    )

    sources_body = f"""
      <nav class="breadcrumbs" aria-label="Percorso"><a href="{SITE_ROOT}">Home</a> / Fonti e licenze</nav>
      <p class="eyebrow">Provenienza verificabile</p>
      <h1>Fonti, licenze e limiti del dataset</h1>
      <p class="content-lead">La build {version} usa fonti dichiarate e
        riproducibili. Il materiale pre-clean-room con provenienza irrisolta è
        stato ritirato e non contribuisce agli output correnti.</p>
      <p>Refs interne di pull request, cache e fork di terzi possono conservare
        copie storiche fuori dal controllo del maintainer. Non sono
        distribuzioni autorizzate dal progetto.</p>
      <div class="content-grid">
        <article class="content-card"><h2>ISTAT</h2><p>Elenco dei comuni e
          codici amministrativi, snapshot del {ISTAT_REFERENCE_DATE}, licenza
          CC BY 4.0.</p></article>
        <article class="content-card"><h2>GeoNames</h2><p>Località, CAP e
          coordinate dal dump italiano del {GEONAMES_REFERENCE_DATE}, licenza
          CC BY 4.0.</p></article>
      </div>
      <aside class="trust-banner content-warning"><strong>Limite importante.</strong>
        GeoNames non è Poste Italiane. CAP e coordinate non sono certificati e
        non devono essere usati per validare indirizzi o spedizioni.</aside>
      <section class="content-section"><h2>Attribuzione e riuso</h2>
        <p>Il riuso richiede l'attribuzione a ISTAT e GeoNames secondo CC BY
          4.0. Il repository documenta fonti, date, record sorgente e metodo di
          riconciliazione per rendere verificabile ogni build.</p>
        <ul class="resource-list">
          <li><a href="{REPOSITORY_URL}/blob/main/DATA_SOURCES.md">Registro delle fonti</a></li>
          <li><a href="{REPOSITORY_URL}/blob/main/DATA_LICENSE.md">Licenza del dataset</a></li>
          <li><a href="{REPOSITORY_URL}/blob/main/COORDINATE_ENRICHMENT.md">Politica sulle coordinate</a></li>
        </ul>
      </section>
    """
    pages.append(
        write_page(
            output,
            "fonti",
            page_document(
                title="Fonti e licenza del dataset",
                description=(
                    "Provenienza e licenze del dataset Italian Cities: comuni "
                    "ISTAT e località, CAP e coordinate GeoNames sotto CC BY "
                    "4.0, con limiti dichiarati."
                ),
                canonical_path="fonti/",
                body=sources_body,
            ),
        )
    )

    unique_locations = {row["location_id"]: row for row in reversed(rows)}
    region_rows: dict[str, list[dict[str, Any]]] = {}
    for row in unique_locations.values():
        region_rows.setdefault(row["region_name"], []).append(row)
    region_cards = []
    for region_name in sorted(region_rows):
        region_slug = slugify(region_name)
        values = region_rows[region_name]
        municipality_count = sum(
            item["location_kind"] == "municipality" for item in values
        )
        region_cards.append(
            f'<li><a href="{SITE_ROOT}regioni/{region_slug}/">'
            f"<strong>{html.escape(region_name)}</strong>"
            f"<span>{format_integer(municipality_count)} comuni ISTAT</span>"
            "</a></li>"
        )
    region_index_body = f"""
      <nav class="breadcrumbs" aria-label="Percorso"><a href="{SITE_ROOT}">Home</a> / Regioni</nav>
      <p class="eyebrow">Copertura territoriale</p>
      <h1>Comuni, CAP e coordinate per regione</h1>
      <p class="content-lead">Esplora la copertura delle 20 regioni italiane.
        Ogni pagina elenca i comuni ISTAT presenti e riassume CAP e coordinate
        disponibili nella release {version}.</p>
      <ul class="region-list">{''.join(region_cards)}</ul>
    """
    pages.append(
        write_page(
            output,
            "regioni",
            page_document(
                title="Comuni italiani per regione",
                description=(
                    "Copertura regionale del dataset Italian Cities: comuni "
                    "ISTAT, CAP GeoNames e coordinate per tutte le 20 regioni "
                    "italiane."
                ),
                canonical_path="regioni/",
                body=region_index_body,
                page_type="CollectionPage",
            ),
        )
    )

    for region_name in sorted(region_rows):
        region_slug = slugify(region_name)
        values = region_rows[region_name]
        municipalities = sorted(
            (
                row
                for row in values
                if row["location_kind"] == "municipality"
            ),
            key=lambda row: (
                row["province_name"],
                row["name"],
                row["municipality_istat_code"],
            ),
        )
        all_relations = [row for row in rows if row["region_name"] == region_name]
        postal_codes = {
            row["postal_code"] for row in all_relations if row["postal_code"]
        }
        with_coordinates = sum(row["latitude"] is not None for row in values)
        province_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for municipality in municipalities:
            key = (
                municipality["province_name"],
                municipality["province_code"],
            )
            province_groups.setdefault(key, []).append(municipality)
        province_sections = []
        for (province_name, province_code), items in sorted(province_groups.items()):
            links = []
            for municipality in items:
                links.append(
                    f'<li><a href="{SITE_ROOT}{municipality_path(municipality)}">'
                    f"{html.escape(municipality['name'])}</a>"
                    f" <small>ISTAT {html.escape(municipality['municipality_istat_code'])}</small></li>"
                )
            province_sections.append(
                f"<section class=\"municipality-group\"><h2>"
                f'<a href="{SITE_ROOT}province/{province_code.casefold()}/">'
                f"{html.escape(province_name)} "
                f"({html.escape(province_code)})</a>"
                f"</h2><ul class=\"municipality-list\">{''.join(links)}</ul></section>"
            )
        region_body = f"""
          <nav class="breadcrumbs" aria-label="Percorso"><a href="{SITE_ROOT}">Home</a> /
            <a href="{SITE_ROOT}regioni/">Regioni</a> / {html.escape(region_name)}</nav>
          <p class="eyebrow">Copertura regionale · {version}</p>
          <h1>Comuni, CAP e coordinate: {html.escape(region_name)}</h1>
          <p class="content-lead">La release contiene
            {format_integer(len(municipalities))} comuni ISTAT della
            {html.escape(region_name)}, {format_integer(len(postal_codes))} CAP
            GeoNames distinti e {format_integer(with_coordinates)} luoghi con
            coordinate.</p>
          <div class="content-grid region-summary">
            <article class="content-card"><strong>{format_integer(len(municipalities))}</strong><span>comuni ISTAT</span></article>
            <article class="content-card"><strong>{format_integer(len(postal_codes))}</strong><span>CAP distinti</span></article>
            <article class="content-card"><strong>{format_integer(with_coordinates)}</strong><span>luoghi con coordinate</span></article>
          </div>
          <aside class="trust-banner content-warning"><strong>Dati non postali ufficiali.</strong>
            I CAP e le coordinate provengono da GeoNames e possono essere
            incompleti o non aggiornati.</aside>
          <section class="content-section"><h2>Elenco dei comuni</h2>
            <p>Seleziona un comune per aprire la sua scheda statica.</p>
            {''.join(province_sections)}
          </section>
        """
        pages.append(
            write_page(
                output,
                f"regioni/{region_slug}",
                page_document(
                    title=f"Comuni, CAP e coordinate della {region_name}",
                    description=(
                        f"Elenco di {len(municipalities)} comuni ISTAT della "
                        f"{region_name}, con copertura CAP GeoNames e "
                        f"coordinate nella release {RELEASE_VERSION}."
                    ),
                    canonical_path=f"regioni/{region_slug}/",
                    body=region_body,
                    page_type="CollectionPage",
                    extra_structured_data={
                        "@type": "AdministrativeArea",
                        "@id": f"{SITE_ROOT}regioni/{region_slug}/#region",
                        "name": region_name,
                        "containedInPlace": {
                            "@type": "Country",
                            "name": "Italia",
                        },
                    },
                ),
            )
        )

    municipality_relations: dict[str, list[dict[str, Any]]] = {}
    municipalities_by_province: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = {}
    for row in rows:
        if row["location_kind"] != "municipality":
            continue
        municipality_relations.setdefault(row["location_id"], []).append(row)
    for relations in municipality_relations.values():
        municipality = relations[0]
        province_key = (
            municipality["province_code"],
            municipality["province_name"],
            municipality["region_name"],
        )
        municipalities_by_province.setdefault(province_key, []).append(
            municipality
        )

    for (
        province_code,
        province_name,
        region_name,
    ), municipalities in sorted(municipalities_by_province.items()):
        municipalities.sort(
            key=lambda row: (
                row["name"],
                row["municipality_istat_code"],
            )
        )
        province_links = "".join(
            f'<li><a href="{SITE_ROOT}{municipality_path(row)}">'
            f"{html.escape(row['name'])}</a> "
            f"<small>ISTAT "
            f"{html.escape(row['municipality_istat_code'])}</small></li>"
            for row in municipalities
        )
        province_body = f"""
          <nav class="breadcrumbs" aria-label="Percorso"><a href="{SITE_ROOT}">Home</a> /
            <a href="{SITE_ROOT}regioni/{slugify(region_name)}/">{html.escape(region_name)}</a> /
            {html.escape(province_name)}</nav>
          <p class="eyebrow">Provincia {html.escape(province_code)} · {version}</p>
          <h1>Comuni della provincia di {html.escape(province_name)}</h1>
          <p class="content-lead">Elenco di
            {format_integer(len(municipalities))} comuni ISTAT della provincia
            di {html.escape(province_name)}, nella regione
            {html.escape(region_name)}. CAP e coordinate associati nelle
            schede provengono da GeoNames e non sono dati postali ufficiali.</p>
          <section class="content-section"><h2>Elenco dei comuni</h2>
            <ul class="municipality-list">{province_links}</ul>
          </section>
        """
        pages.append(
            write_page(
                output,
                f"province/{province_code.casefold()}",
                page_document(
                    title=(
                        f"Comuni della provincia di {province_name} "
                        f"({province_code})"
                    ),
                    description=(
                        f"Elenco di {len(municipalities)} comuni ISTAT della "
                        f"provincia di {province_name}, con codici, CAP "
                        "GeoNames e stato delle coordinate."
                    ),
                    canonical_path=f"province/{province_code.casefold()}/",
                    body=province_body,
                    page_type="CollectionPage",
                    extra_structured_data={
                        "@type": "AdministrativeArea",
                        "@id": (
                            f"{SITE_ROOT}province/"
                            f"{province_code.casefold()}/#province"
                        ),
                        "name": province_name,
                        "containedInPlace": {
                            "@type": "AdministrativeArea",
                            "name": region_name,
                        },
                    },
                ),
            )
        )

    for _, relations in sorted(municipality_relations.items()):
        municipality = relations[0]
        municipality_postal_codes = sorted(
            {
                relation["postal_code"]
                for relation in relations
                if relation["postal_code"]
            }
        )
        postal_text = (
            ", ".join(
                html.escape(value) for value in municipality_postal_codes
            )
            if municipality_postal_codes
            else "non disponibile nello snapshot GeoNames"
        )
        if municipality["latitude"] is None:
            coordinate_text = "Coordinate non disponibili."
        else:
            coordinate_text = (
                f"Record GeoNames: {municipality['latitude']:.5f}, "
                f"{municipality['longitude']:.5f}; accuracy "
                f"{html.escape(municipality['coordinate_accuracy'])}. "
                "Il match anagrafico non certifica l'accuratezza geografica."
            )
        search_query = quote_plus(municipality["name"])
        body = f"""
          <nav class="breadcrumbs" aria-label="Percorso"><a href="{SITE_ROOT}">Home</a> /
            <a href="{SITE_ROOT}regioni/{slugify(municipality['region_name'])}/">{html.escape(municipality['region_name'])}</a> /
            <a href="{SITE_ROOT}province/{municipality['province_code'].casefold()}/">{html.escape(municipality['province_name'])}</a> /
            {html.escape(municipality['name'])}</nav>
          <p class="eyebrow">Comune ISTAT
            {html.escape(municipality['municipality_istat_code'])}</p>
          <h1>{html.escape(municipality['name'])}</h1>
          <p class="content-lead">{html.escape(municipality['name'])} è un
            comune della provincia di
            {html.escape(municipality['province_name'])}
            ({html.escape(municipality['province_code'])}), in
            {html.escape(municipality['region_name'])}.</p>
          <div class="content-grid">
            <article class="content-card"><h2>Codice ISTAT</h2><p>
              <code>{html.escape(municipality['municipality_istat_code'])}</code>
            </p></article>
            <article class="content-card"><h2>CAP GeoNames</h2><p>
              {postal_text}</p></article>
            <article class="content-card"><h2>Coordinate</h2><p>
              {coordinate_text}</p></article>
          </div>
          <aside class="trust-banner content-warning"><strong>Uso corretto.</strong>
            I CAP e le coordinate di questa scheda derivano dal dump GeoNames
            del {GEONAMES_REFERENCE_DATE}; non sono certificati da Poste
            Italiane né verificati sul territorio.</aside>
          <section class="content-section"><h2>Consulta e scarica</h2>
            <ul class="resource-list">
              <li><a href="{SITE_ROOT}?q={search_query}&amp;province={html.escape(municipality['province_code'])}#search">Apri nella ricerca interattiva</a></li>
              <li><a href="{release_asset_url('italian_locations.csv')}">Scarica il CSV completo {version}</a></li>
              <li><a href="{REPOSITORY_URL}/issues/new/choose">Segnala una correzione documentata</a></li>
            </ul>
          </section>
        """
        pages.append(
            write_page(
                output,
                municipality_path(municipality).rstrip("/"),
                page_document(
                    title=(
                        f"{municipality['name']}: codice ISTAT, CAP e "
                        "coordinate"
                    ),
                    description=(
                        f"Scheda del comune di {municipality['name']} "
                        f"({municipality['province_code']}): codice ISTAT "
                        f"{municipality['municipality_istat_code']}, CAP "
                        "GeoNames e stato delle coordinate."
                    ),
                    canonical_path=municipality_path(municipality),
                    body=body,
                    page_type="ProfilePage",
                    extra_structured_data={
                        "@type": "AdministrativeArea",
                        "@id": (
                            f"{SITE_ROOT}{municipality_path(municipality)}"
                            "#municipality"
                        ),
                        "name": municipality["name"],
                        "identifier": (
                            municipality["municipality_istat_code"]
                        ),
                        "containedInPlace": {
                            "@type": "AdministrativeArea",
                            "name": municipality["province_name"],
                        },
                    },
                ),
            )
        )
    return pages


def write_not_found_page(output: Path) -> None:
    document = page_document(
        title="Pagina non trovata",
        description="La pagina richiesta non esiste nel sito Italian Cities.",
        canonical_path="404.html",
        body=f"""
          <p class="eyebrow">Errore 404</p>
          <h1>Pagina non trovata</h1>
          <p class="content-lead">Il collegamento potrebbe essere cambiato.
            Torna alla <a href="{SITE_ROOT}">ricerca dei comuni</a> oppure
            consulta la <a href="{SITE_ROOT}regioni/">copertura regionale</a>.
          </p>
        """,
    ).replace(
        '<meta name="robots" content="index, follow, max-image-preview:large">',
        '<meta name="robots" content="noindex, follow">',
    )
    (output / "404.html").write_text(document, encoding="utf-8")


def write_sitemap(output: Path, paths: list[str]) -> None:
    urls = ["", *paths]
    entries = "".join(
        "  <url>\n"
        f"    <loc>{SITE_ROOT}{html.escape(path)}</loc>\n"
        f"    <lastmod>{BUILD_DATE}</lastmod>\n"
        "  </url>\n"
        for path in urls
    )
    (output / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n",
        encoding="utf-8",
    )


def prepare_output(output: Path) -> None:
    output = output.resolve()
    forbidden = {
        Path("/").resolve(),
        REPOSITORY_ROOT.resolve(),
        SOURCE_SITE.resolve(),
        CANONICAL_DATA.parent.resolve(),
    }
    if output in forbidden:
        raise ValueError(f"Refusing unsafe output directory: {output}")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SOURCE_SITE, output)


def build_site(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    prepare_output(output)

    rows = read_locations(CANONICAL_DATA)
    stats = calculate_stats(rows)
    payload = {
        "metadata": {
            "release": RELEASE_VERSION,
            "release_status": RELEASE_STATUS,
            "schema_version": SCHEMA_VERSION,
            "build_date": BUILD_DATE,
            "structural_quality": STRUCTURAL_QUALITY,
            "operational_data_readiness": OPERATIONAL_DATA_READINESS,
            "istat_reference_date": ISTAT_REFERENCE_DATE,
            "geonames_reference_date": GEONAMES_REFERENCE_DATE,
            "canonical_source_ids": [
                "istat_municipalities",
                "geonames_postal_codes",
            ],
            "attribution": {
                "istat": "ISTAT — CC BY 4.0",
                "geonames": (
                    "GeoNames postal code dump — CC BY 4.0 — "
                    "https://www.geonames.org/"
                ),
            },
            "warning": (
                "GeoNames is not Poste Italiane. CAP and coordinates are "
                "non-official and provided without warranty."
            ),
        },
        "stats": stats,
        "fields": list(WEB_FIELDS),
        "rows": [[row[field] for field in WEB_FIELDS] for row in rows],
    }

    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    locations_path = assets / "locations.json"
    locations_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    shutil.copy2(SOCIAL_PREVIEW, assets / "social-preview.jpg")
    render_homepage(output, stats)
    information_pages = build_information_pages(output, rows, stats)
    write_not_found_page(output)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n"
        "Sitemap: https://codewriter90x.github.io/Italian_Cities/sitemap.xml\n",
        encoding="utf-8",
    )
    write_sitemap(output, information_pages)

    manifest = {
        "release": RELEASE_VERSION,
        "canonical_rows": len(rows),
        "canonical_sha256": sha256(CANONICAL_DATA),
        "locations_json_sha256": sha256(locations_path),
        "page_count": 1 + len(information_pages),
        "stats": stats,
    }
    (output / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination directory (default: dist/pages)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_site(args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
