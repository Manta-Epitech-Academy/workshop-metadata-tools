"""Shared helpers: extract markdown headings (excluding fenced code) and build a TOC tree."""

from __future__ import annotations

import re
from typing import Any

from quiz_lib import strip_quiz_blocks

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def strip_fenced_blocks(text: str) -> str:
    """Remove fenced ``` ... ``` blocks so headings inside them are ignored."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "".join(out)


def extract_heading_lines(text: str) -> list[tuple[int, str]]:
    """Return (level, title) for each ATX heading, in order. Level is 1..6."""
    clean = strip_fenced_blocks(text)
    clean = strip_quiz_blocks(clean)
    result: list[tuple[int, str]] = []
    for line in clean.splitlines():
        m = HEADING_RE.match(line.rstrip())
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        result.append((level, title))
    return result


def headings_to_toc_sections(headings: list[tuple[int, str]]) -> list[dict[str, Any]]:
    """
    Build sections (H1) → parts (H2) → subparts (H3).

    - Headings deeper than H3 are ignored when building this tree (they may still
      exist in the markdown for prose structure).
    - An H2 before any H1 is ignored (orphan part).
    - An H3 before any H2 under the current H1 is ignored (orphan subpart).
    """
    sections: list[dict[str, Any]] = []
    cur_section: dict[str, Any] | None = None
    cur_part: dict[str, Any] | None = None

    for level, title in headings:
        if level == 1:
            cur_section = {"title": title}
            sections.append(cur_section)
            cur_part = None
        elif level == 2:
            if cur_section is None:
                continue
            cur_part = {"title": title}
            if "parts" not in cur_section:
                cur_section["parts"] = []
            cur_section["parts"].append(cur_part)
        elif level == 3:
            if cur_part is None:
                continue
            sub = {"title": title}
            if "subparts" not in cur_part:
                cur_part["subparts"] = []
            cur_part["subparts"].append(sub)
        # level >= 4: ignored for toc generation

    return sections


def markdown_to_toc_sections(text: str) -> list[dict[str, Any]]:
    """Heading tree for a single markdown document (H1 / H2 / H3 only)."""
    headings = extract_heading_lines(text)
    return headings_to_toc_sections(headings)


def is_multi_document_toc(toc: list[Any] | None) -> bool:
    """True if `toc` uses `{ document, sections }` entries."""
    if not toc or not isinstance(toc, list):
        return False
    first = toc[0]
    return (
        isinstance(first, dict)
        and "document" in first
        and "sections" in first
    )


def toc_entries_from_metadata(metadata: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    """
    Return (document_path, section_tree) for each TOC entry.

    Only the multi-document shape is supported: each item must have `document` and `sections`.
    """
    toc = metadata.get("toc")
    if not isinstance(toc, list) or not toc:
        raise ValueError("metadata has no toc list")

    if not is_multi_document_toc(toc):
        raise ValueError(
            'metadata.toc must be a list of { "document", "sections" } objects '
            "(legacy flat toc under project.entrypoint is no longer supported)"
        )

    out: list[tuple[str, list[dict[str, Any]]]] = []
    for item in toc:
        if not isinstance(item, dict):
            raise ValueError("toc entry must be a mapping")
        doc = item.get("document")
        sections = item.get("sections")
        if not isinstance(doc, str) or not doc.strip():
            raise ValueError('each toc entry must have a non-empty "document" string')
        if not isinstance(sections, list):
            raise ValueError('each toc entry must have a "sections" list')
        out.append((doc.strip(), sections))
    return out
