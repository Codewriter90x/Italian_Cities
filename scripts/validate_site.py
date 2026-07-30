#!/usr/bin/env python3
"""Validate built Pages links, accessibility basics and performance budgets."""

from __future__ import annotations

import argparse
import gzip
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

MAX_HOMEPAGE_BYTES = 30_000
MAX_SEARCH_DATA_BYTES = 4_500_000
MAX_SEARCH_DATA_GZIP_BYTES = 900_000
MAX_FIRST_PARTY_CODE_BYTES = 80_000


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links: list[str] = []
        self.controls: list[tuple[str, str]] = []
        self.label_targets: set[str] = set()
        self.images_without_alt: list[str] = []
        self.button_texts: list[str] = []
        self._current_button: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag in {"input", "select", "textarea"} and element_id:
            self.controls.append((tag, element_id))
        if tag == "label" and values.get("for"):
            self.label_targets.add(values["for"] or "")
        if tag == "img" and "alt" not in values:
            self.images_without_alt.append(values.get("src", "<unknown>") or "")
        if tag == "button":
            self._current_button = []

    def handle_data(self, data: str) -> None:
        if self._current_button is not None:
            self._current_button.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._current_button is not None:
            self.button_texts.append("".join(self._current_button).strip())
            self._current_button = None


def resolve_local_link(
    site: Path,
    page: Path,
    href: str,
) -> tuple[Path, str] | None:
    parsed = urlparse(href)
    if href.startswith("mailto:"):
        return None
    if (parsed.scheme or parsed.netloc) and (
            parsed.scheme not in {"http", "https"}
            or parsed.netloc != "codewriter90x.github.io"
            or not parsed.path.startswith("/Italian_Cities/")
    ):
        return None
    path = unquote(parsed.path)
    if not path:
        target = page
    elif path.startswith("/Italian_Cities/"):
        target = site / path.removeprefix("/Italian_Cities/")
    elif path.startswith("/"):
        return None
    else:
        target = page.parent / path
    if (not path or path.endswith("/")) and (
        target.is_dir() or path.endswith("/")
    ):
        target /= "index.html"
    return target.resolve(), unquote(parsed.fragment)


def validate_site(site: Path) -> dict[str, object]:
    site = site.resolve()
    errors: list[str] = []
    html_files = sorted(site.rglob("*.html"))
    if not html_files:
        errors.append("site contains no HTML pages")
    inspectors: dict[Path, PageInspector] = {}
    for page in html_files:
        inspector = PageInspector()
        inspector.feed(page.read_text(encoding="utf-8"))
        inspectors[page.resolve()] = inspector
        duplicate_ids = sorted(
            identifier
            for identifier in set(inspector.ids)
            if inspector.ids.count(identifier) > 1
        )
        if duplicate_ids:
            errors.append(f"{page}: duplicate ids {duplicate_ids}")
        missing_labels = sorted(
            control_id
            for _, control_id in inspector.controls
            if control_id not in inspector.label_targets
        )
        if missing_labels:
            errors.append(f"{page}: controls without labels {missing_labels}")
        if inspector.images_without_alt:
            errors.append(
                f"{page}: images without alt {inspector.images_without_alt}"
            )
        if any(not text for text in inspector.button_texts):
            errors.append(f"{page}: button without accessible text")
    for page, inspector in inspectors.items():
        for href in inspector.links:
            resolved = resolve_local_link(site, page, href)
            if resolved is None:
                continue
            target, fragment = resolved
            if not target.is_file():
                errors.append(f"{page}: broken local link {href!r}")
                continue
            if fragment:
                target_inspector = inspectors.get(target)
                if (
                    target_inspector is None
                    or fragment not in target_inspector.ids
                ):
                    errors.append(
                        f"{page}: broken local fragment {href!r}"
                    )

    homepage = site / "index.html"
    locations = site / "assets/locations.json"
    code_bytes = sum(
        path.stat().st_size
        for path in (site / "assets").iterdir()
        if path.suffix in {".css", ".js", ".mjs"}
    )
    budgets = {
        "homepage_bytes": homepage.stat().st_size,
        "search_data_bytes": locations.stat().st_size,
        "search_data_gzip_bytes": len(
            gzip.compress(
                locations.read_bytes(),
                compresslevel=9,
                mtime=0,
            )
        ),
        "first_party_code_bytes": code_bytes,
    }
    limits = {
        "homepage_bytes": MAX_HOMEPAGE_BYTES,
        "search_data_bytes": MAX_SEARCH_DATA_BYTES,
        "search_data_gzip_bytes": MAX_SEARCH_DATA_GZIP_BYTES,
        "first_party_code_bytes": MAX_FIRST_PARTY_CODE_BYTES,
    }
    for name, value in budgets.items():
        if value > limits[name]:
            errors.append(f"{name} exceeds budget: {value} > {limits[name]}")
    app_source = (site / "assets/app.js").read_text(encoding="utf-8")
    if "IntersectionObserver" not in app_source:
        errors.append("search data is not guarded by lazy loading")
    if 'id="map-fallback-body"' not in homepage.read_text(encoding="utf-8"):
        errors.append("canvas map lacks the accessible tabular fallback")
    not_found = site / "404.html"
    if not not_found.is_file():
        errors.append("custom 404.html is missing")
    elif 'content="noindex, follow"' not in not_found.read_text(
        encoding="utf-8"
    ):
        errors.append("custom 404.html must be noindex")

    report: dict[str, object] = {
        "status": "passed" if not errors else "failed",
        "pages": len(html_files),
        "budgets": budgets,
        "limits": limits,
        "errors": errors,
    }
    if errors:
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    return parser.parse_args()


def main() -> None:
    report = validate_site(parse_args().site)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
