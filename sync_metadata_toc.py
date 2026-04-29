#!/usr/bin/env python3
"""Create or refresh `toc` in metadata.yaml from markdown headings.

- If metadata.yaml is missing, writes a schema-shaped default (including `documents`
  and generated `toc`).
- If it exists, rebuilds `toc` for every path in `documents` (or `project.entrypoint`
  when `documents` is absent), preserving existing `competency` and inline `observables`
  where the title path (section → part → subpart) still matches.

Generated shape: **sections** (H1) → **parts** (H2) → **subparts** (H3), same rules as
`toc_lib.markdown_to_toc_sections` (H4+ omitted; orphan H2/H3 omitted).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import Any

try:
    import yaml as pyyaml
except ImportError:
    print("sync_metadata_toc requires PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("sync_metadata_toc requires jsonschema: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

try:
    from ruamel.yaml import YAML
except ImportError:
    print("sync_metadata_toc requires ruamel.yaml: pip install ruamel.yaml", file=sys.stderr)
    sys.exit(1)

from toc_lib import markdown_to_toc_sections


def resolve_schema_path(repo_root: Path) -> Path | None:
    """Prefer `metadata.schema.json` in the workshop repo; else bundled in this package."""
    local = repo_root / "metadata.schema.json"
    if local.is_file():
        return local.resolve()
    bundled = Path(__file__).resolve().parent / "metadata.schema.json"
    if bundled.is_file():
        return bundled.resolve()
    return None


def resolve_repo_root(metadata_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    try:
        r = subprocess.run(
            ["git", "-C", str(metadata_path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(r.stdout.strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        return metadata_path.parent.resolve()


def discover_markdown_files(metadata_dir: Path) -> list[str]:
    """Top-level `*.md` next to metadata (not recursive), sorted.

    Used only when creating a default metadata file. Common auxiliary names
    (`obs.md`, `structure.md`) are skipped when other `.md` files exist so the
    default entrypoint is usually the workshop document. If you need those
    files in `documents`, add them after the file is created.
    """
    skip = {"obs.md", "structure.md", "readme.md"}
    rels = [
        p.relative_to(metadata_dir).as_posix()
        for p in sorted(metadata_dir.glob("*.md"))
    ]
    filtered = [r for r in rels if r.lower() not in skip]
    return filtered if filtered else rels


def default_slug(root: Path) -> str:
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        slug = env.split("/")[-1]
    else:
        slug = root.name
    slug = slug.lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
    return slug or "project"


def document_paths_from_metadata(data: dict[str, Any]) -> list[str]:
    docs = data.get("documents")
    paths: list[str] = []
    if isinstance(docs, list):
        for item in docs:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                p = item["path"].strip()
                if p:
                    paths.append(p)
    if paths:
        return paths
    project = data.get("project")
    if isinstance(project, dict):
        ep = project.get("entrypoint")
        if isinstance(ep, str) and ep.strip():
            return [ep.strip()]
    raise ValueError(
        "metadata must list non-empty `documents` or set `project.entrypoint`"
    )


def _copy_observables_list(raw: Any) -> list[Any] | None:
    if not isinstance(raw, list) or not raw:
        return None
    out: list[Any] = []
    for x in raw:
        if isinstance(x, dict):
            out.append(dict(x))
    return out or None


def collect_preserved_toc_fields(
    sections: list[Any], prefix: tuple[str, ...] = ()
) -> dict[tuple[str, ...], dict[str, Any]]:
    """Map title path -> preserved keys (competency, observables) for section/part/subpart."""
    out: dict[tuple[str, ...], dict[str, Any]] = {}
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = sec.get("title")
        if not isinstance(title, str):
            continue
        path = prefix + (title,)
        bag: dict[str, Any] = {}
        if isinstance(sec.get("competency"), list) and sec["competency"]:
            preserved: list[Any] = []
            for x in sec["competency"]:
                if isinstance(x, str) and x.strip():
                    preserved.append(x)
                elif isinstance(x, dict):
                    preserved.append(dict(x))
            if preserved:
                bag["competency"] = preserved
        obs = _copy_observables_list(sec.get("observables"))
        if obs:
            bag["observables"] = obs
        if bag:
            out[path] = bag
        for part in sec.get("parts") or []:
            if not isinstance(part, dict):
                continue
            pt = part.get("title")
            if not isinstance(pt, str):
                continue
            ppath = path + (pt,)
            pbag: dict[str, Any] = {}
            if isinstance(part.get("competency"), list) and part["competency"]:
                preserved_p: list[Any] = []
                for x in part["competency"]:
                    if isinstance(x, str) and x.strip():
                        preserved_p.append(x)
                    elif isinstance(x, dict):
                        preserved_p.append(dict(x))
                if preserved_p:
                    pbag["competency"] = preserved_p
            obs_p = _copy_observables_list(part.get("observables"))
            if obs_p:
                pbag["observables"] = obs_p
            if pbag:
                out[ppath] = pbag
            for sub in part.get("subparts") or []:
                if not isinstance(sub, dict):
                    continue
                st = sub.get("title")
                if not isinstance(st, str):
                    continue
                spath = ppath + (st,)
                sbag: dict[str, Any] = {}
                if isinstance(sub.get("competency"), list) and sub["competency"]:
                    preserved_s: list[Any] = []
                    for x in sub["competency"]:
                        if isinstance(x, str) and x.strip():
                            preserved_s.append(x)
                        elif isinstance(x, dict):
                            preserved_s.append(dict(x))
                    if preserved_s:
                        sbag["competency"] = preserved_s
                obs_s = _copy_observables_list(sub.get("observables"))
                if obs_s:
                    sbag["observables"] = obs_s
                if sbag:
                    out[spath] = sbag
    return out


def apply_preserved_toc_fields(
    sections: list[dict[str, Any]],
    bag_map: dict[tuple[str, ...], dict[str, Any]],
    prefix: tuple[str, ...] = (),
) -> None:
    for sec in sections:
        title = sec.get("title")
        if not isinstance(title, str):
            continue
        path = prefix + (title,)
        bag = bag_map.get(path)
        if bag:
            if "competency" in bag:
                sec["competency"] = bag["competency"]
            if "observables" in bag:
                sec["observables"] = bag["observables"]
        for part in sec.get("parts") or []:
            if not isinstance(part, dict):
                continue
            pt = part.get("title")
            if not isinstance(pt, str):
                continue
            ppath = path + (pt,)
            pbag = bag_map.get(ppath)
            if pbag:
                if "competency" in pbag:
                    part["competency"] = pbag["competency"]
                if "observables" in pbag:
                    part["observables"] = pbag["observables"]
            for sub in part.get("subparts") or []:
                if not isinstance(sub, dict):
                    continue
                st = sub.get("title")
                if not isinstance(st, str):
                    continue
                spath = ppath + (st,)
                sbag = bag_map.get(spath)
                if sbag:
                    if "competency" in sbag:
                        sub["competency"] = sbag["competency"]
                    if "observables" in sbag:
                        sub["observables"] = sbag["observables"]


def build_toc_for_documents(
    base_dir: Path,
    doc_paths: list[str],
    previous_toc: list[Any] | None,
) -> list[dict[str, Any]]:
    """Multi-document toc entries with merged toc bindings from previous_toc.

    `base_dir` is the directory that contains `metadata.yaml`; paths in `documents`
    are resolved relative to it (same as check_toc.py).
    """
    prev_by_doc: dict[str, dict[tuple[str, ...], dict[str, Any]]] = {}
    if isinstance(previous_toc, list):
        for item in previous_toc:
            if not isinstance(item, dict):
                continue
            doc = item.get("document")
            secs = item.get("sections")
            if isinstance(doc, str) and isinstance(secs, list):
                prev_by_doc[doc.strip()] = collect_preserved_toc_fields(secs)

    out: list[dict[str, Any]] = []
    for rel in doc_paths:
        md = (base_dir / rel).resolve()
        if not md.is_file():
            raise FileNotFoundError(
                f"markdown not found for documents entry: {rel} (looked under {base_dir})"
            )
        text = md.read_text(encoding="utf-8")
        sections = markdown_to_toc_sections(text)
        bag_map = prev_by_doc.get(rel, {})
        apply_preserved_toc_fields(sections, bag_map)
        out.append({"document": rel, "sections": sections})
    return out


def validate_against_schema(instance: Any, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(instance)


def load_yaml_roundtrip(path: Path, yaml_api: YAML) -> Any:
    text = path.read_text(encoding="utf-8")
    return yaml_api.load(StringIO(text))


def dump_yaml_roundtrip(data: Any, path: Path, yaml_api: YAML) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml_api.dump(data, f)


def validate_file(metadata_path: Path, schema_path: Path) -> None:
    instance = pyyaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    validate_against_schema(instance, schema_path)


def extract_comment_block_before_observables(text: str) -> str | None:
    """Return blank and `#` lines directly above top-level `observables:` (ruamel may drop these)."""
    lines = text.splitlines(keepends=True)
    obs_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("observables:"):
            obs_idx = i
            break
    if obs_idx is None or obs_idx == 0:
        return None
    chunk: list[str] = []
    j = obs_idx - 1
    while j >= 0:
        line = lines[j]
        if line.strip() == "":
            chunk.append(line)
            j -= 1
            continue
        if line.lstrip().startswith("#"):
            chunk.append(line)
            j -= 1
            continue
        break
    if not any(l.lstrip().startswith("#") for l in chunk):
        return None
    chunk.reverse()
    return "".join(chunk)


def restore_comment_block_before_observables(text: str, block: str | None) -> str:
    if not block:
        return text
    if block.strip() and block.strip() in text:
        return text
    return re.sub(
        r"^observables:\s*$",
        block.rstrip("\n") + "\nobservables:",
        text,
        count=1,
        flags=re.MULTILINE,
    )


def build_default_metadata(metadata_dir: Path, md_files: list[str]) -> dict[str, Any]:
    if not md_files:
        raise ValueError(
            "Cannot create default metadata.yaml: no .md files found next to the metadata file."
        )
    slug = default_slug(metadata_dir)
    entry = md_files[0]
    documents = [{"path": p} for p in md_files]
    toc = build_toc_for_documents(metadata_dir, md_files, None)
    return {
        "schema_version": "1.5",
        "project": {
            "name": slug.replace("-", " ").title(),
            "slug": slug,
            "summary": "Workshop metadata (auto-generated; edit as needed).",
            "entrypoint": entry,
        },
        "runtime": {"engine": "unknown", "language": "markdown"},
        "documents": documents,
        "toc": toc,
    }


def sync_existing(metadata_path: Path, schema_path: Path, yaml_api: YAML) -> None:
    original_text = metadata_path.read_text(encoding="utf-8")
    preserved_comments = extract_comment_block_before_observables(original_text)
    data = load_yaml_roundtrip(metadata_path, yaml_api)
    if not isinstance(data, dict):
        raise ValueError("metadata root must be a mapping")
    doc_paths = document_paths_from_metadata(data)
    prev_toc = data.get("toc")
    data["toc"] = build_toc_for_documents(
        metadata_path.parent,
        doc_paths,
        prev_toc if isinstance(prev_toc, list) else None,
    )
    dump_yaml_roundtrip(data, metadata_path, yaml_api)
    if preserved_comments:
        text = metadata_path.read_text(encoding="utf-8")
        text = restore_comment_block_before_observables(text, preserved_comments)
        metadata_path.write_text(text, encoding="utf-8")
    validate_file(metadata_path, schema_path)


def write_default(metadata_path: Path, schema_path: Path, yaml_api: YAML) -> None:
    md_files = discover_markdown_files(metadata_path.parent)
    default_data = build_default_metadata(metadata_path.parent, md_files)
    dump_yaml_roundtrip(default_data, metadata_path, yaml_api)
    validate_file(metadata_path, schema_path)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--metadata",
        type=Path,
        default=Path("metadata.yaml"),
        help="Path to metadata.yaml (default: ./metadata.yaml)",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of metadata file)",
    )
    args = p.parse_args()

    metadata_path = args.metadata.resolve()
    root = resolve_repo_root(metadata_path, args.root)
    schema_path = resolve_schema_path(root)
    if schema_path is None:
        print(
            "sync_metadata_toc: no metadata.schema.json in workshop root and no bundled schema",
            file=sys.stderr,
        )
        sys.exit(2)

    yaml_api = YAML()
    yaml_api.preserve_quotes = True
    yaml_api.default_flow_style = False
    yaml_api.allow_unicode = True
    yaml_api.indent(mapping=2, sequence=4, offset=2)
    yaml_api.width = 120

    try:
        if not metadata_path.is_file():
            write_default(metadata_path, schema_path, yaml_api)
            print(f"Created {metadata_path} with default content and generated toc.")
        else:
            sync_existing(metadata_path, schema_path, yaml_api)
            print(f"Updated toc in {metadata_path}.")
    except Exception as e:
        print(f"sync_metadata_toc: {e}", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
