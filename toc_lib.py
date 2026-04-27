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


def headings_to_toc_nodes(headings: list[tuple[int, str]]) -> list[dict[str, Any]]:
    """
    Build nested TOC nodes: {title, parts?: [...]} from ordered (level, title).
    Same rules as HTML outline: deeper heading nests under the nearest higher-level open section.
    """
    roots: list[dict[str, Any]] = []
    stack: list[tuple[int, dict[str, Any]]] = []

    for level, title in headings:
        node: dict[str, Any] = {"title": title}

        while stack and stack[-1][0] >= level:
            stack.pop()

        if not stack:
            roots.append(node)
            stack.append((level, node))
            continue

        parent_level, parent = stack[-1]
        if level <= parent_level:
            raise RuntimeError("invalid heading stack state")
        if "parts" not in parent:
            parent["parts"] = []
        parent["parts"].append(node)
        stack.append((level, node))

    return roots


def markdown_to_toc_nodes(text: str) -> list[dict[str, Any]]:
    """Heading tree for a single markdown document."""
    headings = extract_heading_lines(text)
    return headings_to_toc_nodes(headings)


def is_multi_document_toc(toc: list[Any] | None) -> bool:
    """True if `toc` uses `{ document, sections }` entries (not a flat legacy list)."""
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
    Supports multi-document `toc` or legacy flat list under `project.entrypoint`.
    """
    toc = metadata.get("toc")
    if not isinstance(toc, list) or not toc:
        raise ValueError("metadata has no toc list")

    if is_multi_document_toc(toc):
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

    entrypoint = (
        (metadata.get("project") or {}).get("entrypoint")
        if isinstance(metadata.get("project"), dict)
        else None
    )
    if not entrypoint or not isinstance(entrypoint, str):
        raise ValueError(
            "legacy flat toc requires project.entrypoint to name the markdown file"
        )
    return [(entrypoint.strip(), toc)]
