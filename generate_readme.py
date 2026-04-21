#!/usr/bin/env python3
"""Write README.md from metadata.yaml (project, authors, runtime, documents, toc)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("generate_readme requires PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from toc_lib import is_multi_document_toc

BANNER = (
    "<!-- Generated from metadata.yaml by generate_readme.py — do not edit by hand. "
    "Run: PYTHONPATH=workshop-metadata-tools python workshop-metadata-tools/generate_readme.py -->\n\n"
)


def esc(s: str) -> str:
    return s.replace("\r\n", "\n").strip()


def md_file_link(path: str) -> str:
    """Markdown link to a workshop file (path as stored in metadata, relative to repo root)."""
    p = path.strip()
    if not p:
        return "—"
    return f"[{p}]({p})"


def render_section_tree(nodes: list[Any], depth: int = 0) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        indent = "  " * depth
        lines.append(f"{indent}- {title.strip()}")
        parts = node.get("parts")
        if isinstance(parts, list) and parts:
            lines.extend(render_section_tree(parts, depth + 1))
    return lines


def build_readme(data: dict[str, Any]) -> str:
    parts: list[str] = [BANNER]

    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    name = project.get("name", "Workshop")
    summary = project.get("summary", "")
    entrypoint = project.get("entrypoint", "")
    slug = project.get("slug", "")

    parts.append(f"# {esc(name)}\n")
    if summary:
        parts.append(f"{esc(summary)}\n")

    if slug or data.get("schema_version"):
        meta_bits = []
        if isinstance(data.get("schema_version"), str):
            meta_bits.append(f"Metadata schema **{data['schema_version']}**")
        if isinstance(slug, str) and slug.strip():
            meta_bits.append(f"slug `{esc(slug)}`")
        if meta_bits:
            parts.append("\n" + " · ".join(meta_bits) + ".\n")

    authors = data.get("authors")
    if isinstance(authors, list) and authors:
        parts.append("\n## Authors\n\n")
        for a in authors:
            if not isinstance(a, dict):
                continue
            nm = a.get("name", "")
            em = a.get("email", "")
            if em:
                parts.append(f"- **{esc(nm)}** — [{em}](mailto:{em})\n")
            else:
                parts.append(f"- **{esc(nm)}**\n")

    runtime = data.get("runtime") if isinstance(data.get("runtime"), dict) else {}
    if runtime:
        parts.append("\n## Runtime\n\n")
        eng = runtime.get("engine", "")
        lang = runtime.get("language", "")
        if eng:
            parts.append(f"- **Engine:** {esc(eng)}\n")
        if lang:
            parts.append(f"- **Language:** {esc(lang)}\n")

    docs = data.get("documents")
    if isinstance(docs, list) and docs:
        parts.append("\n## Documents\n\n")
        parts.append("| File | Notes |\n|------|-------|\n")
        for item in docs:
            if not isinstance(item, dict):
                continue
            path = item.get("path", "")
            dep = item.get("depends_on")
            note = ""
            if isinstance(path, str) and entrypoint and path == entrypoint:
                note = "entrypoint"
            if isinstance(dep, list) and dep:
                extra = "depends on: " + ", ".join(str(x) for x in dep)
                note = f"{note}; {extra}" if note else extra
            cell = note if note else "—"
            link = md_file_link(path) if isinstance(path, str) else "—"
            parts.append(f"| {link} | {cell} |\n")
    elif isinstance(entrypoint, str) and entrypoint.strip():
        parts.append("\n## Entrypoint\n\n")
        parts.append(f"Primary document: {md_file_link(entrypoint)}\n")

    toc = data.get("toc")
    if isinstance(toc, list) and toc:
        parts.append("\n## Table of contents\n\n")
        if is_multi_document_toc(toc):
            for item in toc:
                if not isinstance(item, dict):
                    continue
                doc = item.get("document", "")
                sections = item.get("sections")
                if not isinstance(sections, list):
                    continue
                parts.append(f"### {md_file_link(doc)}\n\n")
                for line in render_section_tree(sections):
                    parts.append(line + "\n")
                parts.append("\n")
        else:
            for line in render_section_tree(toc):
                parts.append(line + "\n")
            parts.append("\n")

    observables = data.get("observables")
    if isinstance(observables, list) and observables:
        parts.append("\n## Observables\n\n")
        for obs in observables:
            if not isinstance(obs, dict):
                continue
            oid = obs.get("id", "")
            otitle = obs.get("title", "")
            parts.append(f"- **{esc(oid)}** — {esc(otitle)}\n")

    parts.append(
        "\n---\n\n"
        "Validation tooling: "
        "[workshop-metadata-tools](https://github.com/Manta-Epitech-Academy/workshop-metadata-tools).\n"
    )

    return "".join(parts)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "metadata",
        nargs="?",
        default=Path("metadata.yaml"),
        type=Path,
        help="Path to metadata.yaml (default: ./metadata.yaml)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write README here (default: README.md next to metadata.yaml)",
    )
    args = p.parse_args()

    meta_path = args.metadata.resolve()
    if not meta_path.is_file():
        print(f"generate_readme: not found: {meta_path}", file=sys.stderr)
        sys.exit(2)

    out_arg = args.output if args.output is not None else Path("README.md")
    if not out_arg.is_absolute():
        out_path = (meta_path.parent / out_arg).resolve()
    else:
        out_path = out_arg.resolve()

    try:
        raw = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"generate_readme: cannot read YAML: {e}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(raw, dict):
        print("generate_readme: metadata root must be a mapping", file=sys.stderr)
        sys.exit(2)

    text = build_readme(raw)
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
