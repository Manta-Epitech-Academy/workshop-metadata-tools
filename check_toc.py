#!/usr/bin/env python3
"""Check that `toc` in metadata.yaml matches headings in each listed markdown file.

Also validates:
- Every cf_code entry matches the pattern DOMAIN-SKILL.LEVEL.OBS_NUM.
- Every OBS_NUM referenced in cf_code corresponds to a declared observable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("check_toc requires PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from toc_lib import markdown_to_toc_nodes, toc_entries_from_metadata

CF_CODE_RE = re.compile(r"^[A-Z]+-\d+\.[A-Z]\d+\.(\d+)$")


def collect_cf_codes(nodes: list[Any], out: list[tuple[str, str]]) -> None:
    """Recursively collect (cf_code, location_title) pairs from a toc node tree."""
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title", "?")
        for code in node.get("cf_code") or []:
            out.append((code, title))
        collect_cf_codes(node.get("parts") or [], out)


def check_cf_codes(
    entries: list[tuple[str, list[Any]]],
    observable_ids: set[str],
    project_slug: str,
) -> list[str]:
    """Return a list of error messages (empty = all good)."""
    errors: list[str] = []
    all_codes: list[tuple[str, str]] = []
    for _doc, sections in entries:
        collect_cf_codes(sections, all_codes)

    for code, location in all_codes:
        m = CF_CODE_RE.match(code)
        if not m:
            errors.append(
                f"cf_code {code!r} (in section {location!r}) does not match"
                " DOMAIN-SKILL.LEVEL.OBS_NUM format"
            )
            continue
        obs_num = m.group(1)
        expected_id = f"{project_slug}.{obs_num}"
        if observable_ids and expected_id not in observable_ids:
            errors.append(
                f"cf_code {code!r} (in section {location!r}) references observable"
                f" {expected_id!r} which is not declared in observables"
            )
    return errors


def normalize_toc_node(node: Any) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise ValueError(f"toc entry must be a mapping, got {type(node).__name__}")
    if "title" not in node:
        raise ValueError("toc entry missing 'title'")
    title = node["title"]
    if not isinstance(title, str):
        raise ValueError("'title' must be a string")
    parts_raw = node.get("parts", [])
    if parts_raw is None:
        parts_raw = []
    if not isinstance(parts_raw, list):
        raise ValueError("'parts' must be a list")
    parts = [normalize_toc_node(p) for p in parts_raw]
    return {"title": title, "parts": parts}


def trees_equal(
    a: list[dict[str, Any]],
    b: list[dict[str, Any]],
    path: str = "toc",
) -> tuple[bool, str]:
    if len(a) != len(b):
        return (
            False,
            f"{path}: expected {len(a)} top-level section(s), found {len(b)}",
        )
    for i, (left, right) in enumerate(zip(a, b)):
        sub = f"{path}[{i}]"
        if left["title"] != right["title"]:
            return (
                False,
                f"{sub}: title mismatch — markdown: {left['title']!r}, yaml: {right['title']!r}",
            )
        lp = left.get("parts", [])
        rp = right.get("parts", [])
        ok, msg = trees_equal(lp, rp, f"{sub}.parts")
        if not ok:
            return False, msg
    return True, ""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "metadata",
        nargs="?",
        default=Path("metadata.yaml"),
        type=Path,
        help="YAML with `toc:` (default: metadata.yaml)",
    )
    args = p.parse_args()

    try:
        raw = yaml.safe_load(args.metadata.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"check_toc: cannot read metadata: {e}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(raw, dict):
        print("check_toc: metadata root must be a mapping", file=sys.stderr)
        sys.exit(2)

    base = args.metadata.resolve().parent

    try:
        entries = toc_entries_from_metadata(raw)
    except ValueError as e:
        print(f"check_toc: invalid toc: {e}", file=sys.stderr)
        sys.exit(2)

    project_slug = (raw.get("project") or {}).get("slug", "")
    observables_raw = raw.get("observables") or []
    observable_ids: set[str] = {
        obs["id"] for obs in observables_raw if isinstance(obs, dict) and "id" in obs
    }

    cf_errors = check_cf_codes(entries, observable_ids, project_slug)
    for err in cf_errors:
        print(f"FAIL: {err}", file=sys.stderr)
    if cf_errors:
        sys.exit(1)

    for doc_rel, yaml_sections in entries:
        md_path = (base / doc_rel).resolve()
        if not md_path.is_file():
            print(f"FAIL: missing markdown file: {doc_rel} (resolved: {md_path})", file=sys.stderr)
            sys.exit(1)

        md_text = md_path.read_text(encoding="utf-8")
        expected = markdown_to_toc_nodes(md_text)
        for n in expected:
            n["parts"] = n.get("parts", [])

        try:
            got = [normalize_toc_node(x) for x in yaml_sections]
        except ValueError as e:
            print(f"check_toc: invalid toc for {doc_rel}: {e}", file=sys.stderr)
            sys.exit(2)

        ok, msg = trees_equal(expected, got)
        if not ok:
            print(f"FAIL ({doc_rel}): {msg}", file=sys.stderr)
            sys.exit(1)

    obs_info = f", {len(observable_ids)} observable(s)" if observable_ids else ""
    print(f"OK: toc matches markdown headings ({len(entries)} document(s){obs_info}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
