#!/usr/bin/env python3
"""Check that `toc` in metadata.yaml matches headings in each listed markdown file.

Also validates `competency` hooks on TOC nodes: slash paths `/DOMAIN/SKILL/LEVEL/PROJECT/OBSINDEX`
(see schema) or legacy structured objects; when `observables` is non-empty, path OBSINDEX must
match an observable id `{project.slug}.OBSINDEX`.
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

_COMP_PATH = re.compile(
    r"^/([A-Z]+)/([0-9]+)/([A-Z][0-9]+)/([a-z][a-z0-9_-]*)/([1-9][0-9]*)$"
)


def collect_competency(
    nodes: list[Any], out: list[tuple[str | dict[str, Any], str]]
) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title", "?")
        for item in node.get("competency") or []:
            if isinstance(item, (str, dict)):
                out.append((item, title))
        collect_competency(node.get("parts") or [], out)


def _obs_index_ok(raw: Any) -> tuple[bool, str]:
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        return False, f"obs_index must be an integer, got {type(raw).__name__}"
    if isinstance(raw, str):
        if not raw.isdigit() or int(raw) < 1:
            return False, "obs_index must be a positive integer"
        return True, ""
    if isinstance(raw, int) and raw >= 1:
        return True, ""
    return False, "obs_index must be a positive integer"


def _check_one_competency_dict(
    ref: dict[str, Any],
    location: str,
    project_slug: str,
    observable_ids: set[str],
    require_obs: bool,
) -> list[str]:
    errors: list[str] = []
    req = ("domain", "skill", "level", "project", "obs_index")
    missing = [k for k in req if k not in ref]
    if missing:
        errors.append(
            f"competency entry {ref!r} (in section {location!r}) missing keys: {', '.join(missing)}"
        )
        return errors
    dom, sk, lv, proj, oix = (
        ref["domain"],
        ref["skill"],
        ref["level"],
        ref["project"],
        ref["obs_index"],
    )
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
    ok, msg = _obs_index_ok(oix)
    if not ok:
        errors.append(f"competency.obs_index (in section {location!r}): {msg}")
    if isinstance(proj, str) and proj != project_slug:
        errors.append(
            f"competency.project {proj!r} (in section {location!r}) must match"
            f" metadata project.slug {project_slug!r}"
        )

    oid = ref.get("observable_id")
    if require_obs:
        if not isinstance(oid, str) or not oid.strip():
            errors.append(
                f"competency entry (in section {location!r}) must set observable_id"
                " when observables are declared"
            )
        else:
            if oid not in observable_ids:
                errors.append(
                    f"competency observable_id {oid!r} (in section {location!r}) is not"
                    " declared under observables"
                )
            exp_prefix = f"{project_slug}."
            if not oid.startswith(exp_prefix):
                errors.append(
                    f"competency observable_id {oid!r} (in section {location!r}) must start"
                    f" with {exp_prefix!r}"
                )
    elif observable_ids and isinstance(oid, str) and oid.strip() and oid not in observable_ids:
        errors.append(
            f"competency observable_id {oid!r} (in section {location!r}) is not declared"
            " under observables"
        )
    return errors


def _check_one_competency_path(
    path: str,
    location: str,
    project_slug: str,
    observable_ids: set[str],
    require_obs: bool,
) -> list[str]:
    errors: list[str] = []
    m = _COMP_PATH.fullmatch(path.strip())
    if not m:
        errors.append(
            f"competency path {path!r} (in section {location!r}) must match"
            " /DOMAIN/SKILL/LEVEL/PROJECT/OBSINDEX (see metadata schema)"
        )
        return errors
    dom, sk, lv, proj, obs_tail = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    if proj != project_slug:
        errors.append(
            f"competency path project segment {proj!r} (in section {location!r}) must match"
            f" metadata project.slug {project_slug!r}"
        )
    if require_obs:
        oid = f"{project_slug}.{obs_tail}"
        if oid not in observable_ids:
            errors.append(
                f"competency path {path!r} (in section {location!r}): observable {oid!r} is not"
                " declared under observables"
            )
    return errors


def check_competency_refs(
    entries: list[tuple[str, list[Any]]],
    project_slug: str,
    observable_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    collected: list[tuple[str | dict[str, Any], str]] = []
    for _doc, sections in entries:
        collect_competency(sections, collected)

    require_obs = bool(observable_ids)
    for ref, location in collected:
        if isinstance(ref, str):
            errors.extend(_check_one_competency_path(ref, location, project_slug, observable_ids, require_obs))
        elif isinstance(ref, dict):
            errors.extend(
                _check_one_competency_dict(ref, location, project_slug, observable_ids, require_obs)
            )
        else:
            errors.append(
                f"competency entry {ref!r} (in section {location!r}) must be a string path or mapping"
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

    errs = check_competency_refs(entries, project_slug, observable_ids)
    for err in errs:
        print(f"FAIL: {err}", file=sys.stderr)
    if errs:
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
