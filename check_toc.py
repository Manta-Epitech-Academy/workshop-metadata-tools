#!/usr/bin/env python3
"""Check that `toc` in metadata.yaml matches headings in each listed markdown file.

Also validates:
- Every cf_code entry matches the pattern DOMAIN-SKILL.LEVEL.OBS_NUM.
- Every OBS_NUM referenced in cf_code corresponds to a declared observable (when `observables` is non-empty).
- Optional competency_path strings: DOMAIN/skill_nn/LEVEL/project_slug/obs_index; project slug must match metadata.
- Optional structured competency[] objects: same contract as one slash path.
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
CANONICAL_PATH_RE = re.compile(
    r"^([A-Z]+)/([0-9]+)/([A-Z][0-9]+)/([a-z][a-z0-9_-]*)/([0-9]+)$"
)


def collect_cf_codes(nodes: list[Any], out: list[tuple[str, str]]) -> None:
    """Recursively collect (cf_code, location_title) pairs from a toc node tree."""
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title", "?")
        for code in node.get("cf_code") or []:
            out.append((code, title))
        collect_cf_codes(node.get("parts") or [], out)


def collect_competency_paths(nodes: list[Any], out: list[tuple[str, str]]) -> None:
    """Recursively collect (competency_path string, location_title)."""
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title", "?")
        for path in node.get("competency_path") or []:
            out.append((path, title))
        collect_competency_paths(node.get("parts") or [], out)


def collect_competency_struct(
    nodes: list[Any], out: list[tuple[dict[str, Any], str]]
) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title", "?")
        for item in node.get("competency") or []:
            if isinstance(item, dict):
                out.append((item, title))
        collect_competency_struct(node.get("parts") or [], out)


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


def check_competency_paths(
    entries: list[tuple[str, list[Any]]],
    project_slug: str,
) -> list[str]:
    errors: list[str] = []
    collected: list[tuple[str, str]] = []
    for _doc, sections in entries:
        collect_competency_paths(sections, collected)
    for path, location in collected:
        if not isinstance(path, str):
            errors.append(
                f"competency_path entry (in section {location!r}) must be a string, got {type(path).__name__}"
            )
            continue
        m = CANONICAL_PATH_RE.match(path)
        if not m:
            errors.append(
                f"competency_path {path!r} (in section {location!r}) does not match"
                " DOMAIN/skill_nn/LEVEL/project_slug/obs_index"
            )
            continue
        slug = m.group(4)
        if slug != project_slug:
            errors.append(
                f"competency_path {path!r} (in section {location!r}) uses project slug {slug!r}"
                f" but metadata project.slug is {project_slug!r}"
            )
    return errors


def _struct_obs_index_ok(raw: Any) -> tuple[bool, str]:
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        return False, f"obs_index must be an integer, got {type(raw).__name__}"
    if isinstance(raw, str):
        if not raw.isdigit() or int(raw) < 1:
            return False, "obs_index must be a positive integer"
        return True, ""
    if isinstance(raw, int) and raw >= 1:
        return True, ""
    return False, "obs_index must be a positive integer"


def check_competency_struct(
    entries: list[tuple[str, list[Any]]],
    project_slug: str,
) -> list[str]:
    errors: list[str] = []
    collected: list[tuple[dict[str, Any], str]] = []
    for _doc, sections in entries:
        collect_competency_struct(sections, collected)
    for ref, location in collected:
        req = ("domain", "skill", "level", "project", "obs_index")
        missing = [k for k in req if k not in ref]
        if missing:
            errors.append(
                f"competency entry {ref!r} (in section {location!r}) missing keys: {', '.join(missing)}"
            )
            continue
        dom, sk, lv, proj, oix = (ref["domain"], ref["skill"], ref["level"], ref["project"], ref["obs_index"])
        if not isinstance(dom, str) or not re.fullmatch(r"[A-Z]+", dom):
            errors.append(
                f"competency.domain (in section {location!r}) must be uppercase letters, got {dom!r}"
            )
        if not isinstance(sk, str) or not re.fullmatch(r"[0-9]+", sk):
            errors.append(
                f"competency.skill (in section {location!r}) must be digits, got {sk!r}"
            )
        if not isinstance(lv, str) or not re.fullmatch(r"[A-Z][0-9]+", lv):
            errors.append(
                f"competency.level (in section {location!r}) must match e.g. A1, got {lv!r}"
            )
        if not isinstance(proj, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", proj):
            errors.append(
                f"competency.project (in section {location!r}) must be a slug, got {proj!r}"
            )
        ok, msg = _struct_obs_index_ok(oix)
        if not ok:
            errors.append(f"competency.obs_index (in section {location!r}): {msg}")
        if isinstance(proj, str) and proj != project_slug:
            errors.append(
                f"competency.project {proj!r} (in section {location!r}) must match"
                f" metadata project.slug {project_slug!r}"
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
    path_errors = check_competency_paths(entries, project_slug)
    struct_errors = check_competency_struct(entries, project_slug)
    all_err = cf_errors + path_errors + struct_errors
    for err in all_err:
        print(f"FAIL: {err}", file=sys.stderr)
    if all_err:
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
