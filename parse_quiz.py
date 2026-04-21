#!/usr/bin/env python3
"""Extract quiz blocks from Markdown and print JSON (see docs/QUIZ.md)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quiz_lib import parse_quizzes, quizzes_to_json


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "markdown",
        nargs="?",
        type=Path,
        default=None,
        help="Markdown file (default: stdin)",
    )
    args = p.parse_args()

    if args.markdown is None:
        text = sys.stdin.read()
    else:
        path = args.markdown.resolve()
        if not path.is_file():
            print(f"parse_quiz: not found: {path}", file=sys.stderr)
            sys.exit(2)
        text = path.read_text(encoding="utf-8")

    quizzes = parse_quizzes(text)
    sys.stdout.write(quizzes_to_json(quizzes))
    if not sys.stdout.isatty():
        pass
    else:
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
