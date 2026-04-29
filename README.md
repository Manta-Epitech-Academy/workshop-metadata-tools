# workshop-metadata-tools

Shared Python tooling for [Epitech Academy](https://epitech.academy) workshop repositories: validate `metadata.yaml`, keep the **`toc`** in sync with Markdown headings, generate **`README.md`** from metadata, and check structured **`competency`** hooks against **`observables`** when declared.

Workshop repositories hold **`metadata.yaml`**, generated **`README.md`**, and workshop **`.md`** files only. The JSON Schema lives **here** (`metadata.schema.json`); editors point at it via the `$schema` URL in `metadata.yaml` (see the workshop template). **CI checks out this repository** next to the workshop and runs the scripts from here.

## Scripts

| Script | Role |
|--------|------|
| `sync_metadata_toc.py` | Creates a default `metadata.yaml` if missing, or regenerates **`toc`** from `documents` / headings; validates against `metadata.schema.json`. |
| `generate_readme.py` | Writes **`README.md`** from `metadata.yaml` (title, summary, authors, runtime, documents, toc outline, observables). |
| `check_toc.py` | Ensures `toc` matches headings and validates `competency` / `observables`. |
| `generate_toc.py` | Prints a `toc` YAML fragment from one or more `.md` files (optional helper). |
| `parse_quiz.py` | Prints quiz blocks in a Markdown file as JSON (see `docs/QUIZ.md`). |
| `toc_lib.py` | Heading extraction, TOC tree, and `strip_quiz_blocks` (quizzes excluded from TOC). |
| `quiz_lib.py` | Parse quizzes; used by `toc_lib` and `parse_quiz.py`. |

## Local use (from a workshop repository)

Clone this repo **next to** your workshop (or anywhere), then from the **workshop root** (where `metadata.yaml` lives):

```bash
git clone https://github.com/kevin-cazal/workshop-metadata-tools.git
pip install -r workshop-metadata-tools/requirements.txt
export PYTHONPATH="$PWD/workshop-metadata-tools"
python workshop-metadata-tools/sync_metadata_toc.py
python workshop-metadata-tools/generate_readme.py
python workshop-metadata-tools/check_toc.py
python workshop-metadata-tools/parse_quiz.py WORKSHOP.md   # optional: list quizzes as JSON
```

Or with an absolute path to `workshop-metadata-tools` and `PYTHONPATH` set to that directory.

You may add a copy of `metadata.schema.json` at the workshop root to override the bundled schema for local experiments; otherwise `sync_metadata_toc.py` uses the schema from this repo.

## JSON Schema

Canonical file: [`metadata.schema.json`](metadata.schema.json) (published at  
`https://raw.githubusercontent.com/kevin-cazal/workshop-metadata-tools/main/metadata.schema.json`).

**Schema 1.5** introduces a fixed-depth `toc`: each document has **`sections`** (H1) → **`parts`** (H2) → **`subparts`** (H3). Legacy flat `toc` (single file without `document` / `sections`) is no longer accepted. Workshop repos should set `schema_version: "1.5"` when adopting this shape. Inline **`observables`** on a toc node use **`skill_path`** and an optional **`id`** as a **positive integer** only (ordinal `N` for `{project.slug}.N` in the top-level `observables` list).

## Documentation

- [`docs/STRUCTURE.md`](docs/STRUCTURE.md) — metadata model, diagrams (Mermaid), and layout.
- [`docs/TOC_RUNTIME.md`](docs/TOC_RUNTIME.md) — how headings map to `toc` (H4+ and orphan rules).
- [`docs/QUIZ.md`](docs/QUIZ.md) — quiz blocks in Markdown (not in `metadata.yaml` / `toc`).
- [`docs/structure-diagrams.html`](docs/structure-diagrams.html) — same diagrams as STRUCTURE in a browser (open locally).

## CI

Workshop repositories call the reusable workflow:

`kevin-cazal/workshop-metadata-tools/.github/workflows/verify-metadata-reusable.yml@main`

See the workshop template (`TEMPLATE.md` / `README.md`) for the exact workflow snippet.
