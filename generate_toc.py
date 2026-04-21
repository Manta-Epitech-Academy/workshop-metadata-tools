#!/usr/bin/env python3
"""Generate a YAML `toc` from markdown headings (code fences excluded).

Each input file becomes one `{ document, sections }` entry under `toc`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("generate_toc requires PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from toc_lib import markdown_to_toc_nodes


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "markdown",
        type=Path,
        nargs="+",
        help="One or more .md paths (stored as given in `document`, e.g. WORKSHOP.md part2.md)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write YAML here (default: stdout)",
    )
    p.add_argument(
        "--wrap-key",
        default="toc",
        help="Emit YAML under this top-level key (default: toc). Use empty string for bare list.",
    )
    args = p.parse_args()

    cwd = Path.cwd().resolve()

    toc_entries: list[dict] = []
    for path in args.markdown:
        text = path.read_text(encoding="utf-8")
        nodes = markdown_to_toc_nodes(text)
        resolved = path.resolve()
        try:
            doc_id = resolved.relative_to(cwd).as_posix()
        except ValueError:
            doc_id = path.as_posix()
        toc_entries.append(
            {
                "document": doc_id,
                "sections": nodes,
            }
        )

    if args.wrap_key:
        payload = {args.wrap_key: toc_entries}
    else:
        payload = toc_entries

    out = yaml.safe_dump(
        payload,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )

    if args.output:
        args.output.write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
