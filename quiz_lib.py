"""Parse workshop quiz blocks in Markdown and strip them for TOC extraction.

Quizzes are blockquotes starting with ``> QUIZ.<level>.<q_id>``. They are not part of
``metadata.yaml`` / ``toc``; ``strip_quiz_blocks`` removes them before heading extraction.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

# First line: "> QUIZ.<level>.<q_id> Title text"
QUIZ_HEADER_RE = re.compile(
    r"^\s*>\s*QUIZ\.(?P<level>[^.\s]+)\.(?P<qid>[^.\s]+)\s+(?P<title>.+?)\s*$"
)

HEADING_ATX_RE = re.compile(r"^\s*#{1,6}\s")
LIST_ITEM_RE = re.compile(r"^\s*([-*])\s+(.+)$")
# Free form: exactly one list row — prompt in brackets, line ends with ':'
FREE_FORM_PROMPT_RE = re.compile(r"^\s*-\s+\[(.+)\]\s*:\s*$")

QuizType = Literal["single", "multiple", "match", "freeform"]


def _find_quiz_block_end(lines: list[str], start: int) -> int:
    """Index of first line *after* the quiz block that starts at ``start``."""
    n = len(lines)
    if start >= n or not QUIZ_HEADER_RE.match(lines[start]):
        return start + 1

    i = start + 1
    while i < n:
        line = lines[i]
        if QUIZ_HEADER_RE.match(line):
            return i
        if line.lstrip().startswith(">"):
            i += 1
            continue
        break

    while i < n and not lines[i].strip():
        i += 1

    if i >= n:
        return n

    if HEADING_ATX_RE.match(lines[i]):
        return i

    line = lines[i]
    if line.lstrip().startswith(">"):
        return i

    if FREE_FORM_PROMPT_RE.match(line):
        return i + 1

    if LIST_ITEM_RE.match(line):
        return _consume_list_body(lines, i)

    return i


def _consume_list_body(lines: list[str], start: int) -> int:
    n = len(lines)
    i = start
    while i < n:
        line = lines[i]
        if QUIZ_HEADER_RE.match(line):
            return i
        if HEADING_ATX_RE.match(line):
            return i
        if not line.strip():
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and LIST_ITEM_RE.match(lines[j]):
                i += 1
                continue
            return i
        if LIST_ITEM_RE.match(line):
            i += 1
            continue
        return i
    return n


def strip_quiz_blocks(text: str) -> str:
    """Remove all quiz blocks so ATX headings inside quizzes never affect the TOC."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if QUIZ_HEADER_RE.match(lines[i]):
            i = _find_quiz_block_end(lines, i)
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def _parse_list_line(line: str) -> dict[str, str] | None:
    m = LIST_ITEM_RE.match(line)
    if not m:
        return None
    marker, rest = m.group(1), m.group(2).strip()
    lm = re.match(r"^([A-Za-z])\.\s+(.*)$", rest)
    if not lm:
        return {"marker": marker, "letter": "", "text": rest}
    return {"marker": marker, "letter": lm.group(1), "text": lm.group(2)}


def _classify_list_type(items: list[dict[str, str]]) -> QuizType:
    if not items:
        return "freeform"
    markers = {it["marker"] for it in items}
    if "*" in markers and "-" not in markers:
        return "multiple"
    letters = [it.get("letter", "") for it in items if it["marker"] == "-"]
    has_upper = any(len(x) == 1 and x.isupper() for x in letters)
    has_lower = any(len(x) == 1 and x.islower() for x in letters)
    if has_upper and has_lower:
        return "match"
    return "single"


def _parse_quiz_block(block: list[str]) -> dict[str, Any]:
    if not block:
        return {}
    hm = QUIZ_HEADER_RE.match(block[0])
    if not hm:
        return {}
    level = hm.group("level")
    qid = hm.group("qid")
    title = hm.group("title").strip()

    i = 1
    q_lines: list[str] = []
    while i < len(block):
        line = block[i]
        if QUIZ_HEADER_RE.match(line):
            break
        if line.lstrip().startswith(">"):
            q_lines.append(line.lstrip()[1:].lstrip())
            i += 1
        else:
            break

    while i < len(block) and not block[i].strip():
        i += 1

    if i >= len(block):
        return _quiz_dict(level, qid, title, q_lines, "freeform", [], "", None)

    fm = FREE_FORM_PROMPT_RE.match(block[i])
    if fm:
        return _quiz_dict(
            level,
            qid,
            title,
            q_lines,
            "freeform",
            [],
            "",
            fm.group(1).strip(),
        )

    if LIST_ITEM_RE.match(block[i]):
        items: list[dict[str, str]] = []
        j = i
        while j < len(block):
            line = block[j]
            if not line.strip():
                k = j + 1
                while k < len(block) and not block[k].strip():
                    k += 1
                if k < len(block) and LIST_ITEM_RE.match(block[k]):
                    j += 1
                    continue
                break
            parsed = _parse_list_line(line)
            if parsed:
                items.append(parsed)
                j += 1
                continue
            break
        qtype = _classify_list_type(items)
        entry = _quiz_dict(level, qid, title, q_lines, qtype, items, "", None)
        if qtype == "match":
            entry["match_left"] = [
                it for it in items if len(it.get("letter", "")) == 1 and it["letter"].isupper()
            ]
            entry["match_right"] = [
                it for it in items if len(it.get("letter", "")) == 1 and it["letter"].islower()
            ]
        return entry

    return _quiz_dict(level, qid, title, q_lines, "freeform", [], "", None)


def _quiz_dict(
    level: str,
    qid: str,
    title: str,
    q_lines: list[str],
    qtype: QuizType,
    items: list[dict[str, str]],
    body: str,
    freeform_prompt: str | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "level": level,
        "qid": qid,
        "title": title,
        "question": "\n".join(q_lines),
        "type": qtype,
        "items": items,
        "freeform_body": body,
        "freeform_prompt": freeform_prompt,
    }
    if freeform_prompt is None:
        del out["freeform_prompt"]
    if not body:
        del out["freeform_body"]
    return out


def parse_quizzes(text: str) -> list[dict[str, Any]]:
    """Return one dict per ``QUIZ`` block (see docs/QUIZ.md)."""
    lines = text.splitlines()
    out: list[dict[str, Any]] = []
    i = 0
    n = len(lines)
    while i < n:
        if not QUIZ_HEADER_RE.match(lines[i]):
            i += 1
            continue
        end = _find_quiz_block_end(lines, i)
        block = lines[i:end]
        out.append(_parse_quiz_block(block))
        i = end
    return out


def quizzes_to_json(quizzes: list[dict[str, Any]]) -> str:
    return json.dumps(quizzes, ensure_ascii=False, indent=2)
