# Quiz blocks in workshop Markdown

Quizzes are written in **Markdown** using blockquotes. They are **not** reflected in `metadata.yaml` or the generated **table of contents** (`toc`): tooling strips quiz blocks before extracting `#` headings.

## Syntax overview

1. **Start** — one line:

   ```markdown
   > QUIZ.<level>.<q_id> <short title>
   ```

   - `<level>` and `<q_id>` are non-empty tokens without spaces (e.g. `A1`, `1`, `B1`, `3`).
   - The rest of the line is a human-readable title.

2. **Question** — one or more blockquote lines:

   ```markdown
   > Full question text (can span several `> ` lines).
   ```

3. **Body** — exactly one of:

   | Kind | Markdown | Parsed `type` |
   |------|----------|----------------|
   | Single choice | List with **`-`** and `Letter.` prefixes | `single` |
   | Multiple choice | List with **`*`** and `Letter.` prefixes | `multiple` |
   | Match pairs | List with **`-`** and **uppercase** `Letter.` rows plus **lowercase** `letter.` rows | `match` |
   | Free form | **One** list item: **`- [prompt]:`** | `freeform` |

4. **Correct answers** — **not** specified in this version (reserved for a later format).

## Single correct answer

Use **hyphen** list items (`-`):

```markdown
> QUIZ.A1.1 Area of a square
> What is the side length of a square with area 100?

- A. 5
- B. 10
- C. -8
```

## Multiple correct answers

Use **asterisk** list items (`*`):

```markdown
> QUIZ.A2.2 Sums
> Which expressions equal 42?

* A. 30+12
* B. 0x2a
* C. 84 / 2
* D. 67
```

## Match (propositions)

Use **hyphen** lists: **uppercase** letters label one column, **lowercase** the other (same letter pairs match, e.g. `A` ↔ `a`):

```markdown
> QUIZ.B1.3 Match
> Match each animal to an OS mascot.

- A. Gnou
- B. Manchot
- C. Démon
- a. FreeBSD
- b. Linux
- c. GNU
```

## Free form

Exactly **one** list line in this shape (prompt may be any text; it must not contain `]`):

```markdown
- [Your prompt or label here]:
```

Example:

```markdown
> QUIZ.C1.1 Essay
> Name the main designer of the C language.

- [Short paragraph]:
```

JSON output includes `freeform_prompt` with the text inside the brackets.

## End of a quiz block

A quiz ends when the next line starts:

- another quiz (`> QUIZ.…`), or
- an ATX heading (`#` … `######`), or
- end of file.

For list-based bodies (single / multiple / match), the block ends at the first blank line **not** followed by another list item. For **free form**, the body is **only** the single `- […]:` line.

## Tooling

From the workshop root (with `workshop-metadata-tools` on `PYTHONPATH`):

```bash
python workshop-metadata-tools/parse_quiz.py path/to/WORKSHOP.md
```

Prints a JSON array of quiz objects (`level`, `qid`, `title`, `question`, `type`, `items`, `freeform_prompt` for free-form quizzes, etc.).

`toc_lib.strip_quiz_blocks` removes quizzes before heading extraction so quizzes never appear in `metadata.yaml` / `toc`.
