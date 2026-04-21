# workshop-metadata-tools

Shared Python tooling for [Epitech Academy](https://epitech.academy) workshop repositories: validate `metadata.yaml`, keep the **`toc`** in sync with Markdown headings, generate **`README.md`** from metadata, and check competency codes (`cf_code`) against observables.

Workshop repositories hold **`metadata.yaml`**, generated **`README.md`**, and workshop **`.md`** files only. The JSON Schema lives **here** (`metadata.schema.json`); editors point at it via the `$schema` URL in `metadata.yaml` (see the workshop template). **CI checks out this repository** next to the workshop and runs the scripts from here.

## Scripts

| Script | Role |
|--------|------|
| `sync_metadata_toc.py` | Creates a default `metadata.yaml` if missing, or regenerates **`toc`** from `documents` / headings; validates against `metadata.schema.json`. |
| `generate_readme.py` | Writes **`README.md`** from `metadata.yaml` (title, summary, authors, runtime, documents, toc outline, observables). |
| `check_toc.py` | Ensures `toc` matches headings and validates `cf_code` / observables. |
| `generate_toc.py` | Prints a `toc` YAML fragment from one or more `.md` files (optional helper). |
| `parse_quiz.py` | Prints quiz blocks in a Markdown file as JSON (see `docs/QUIZ.md`). |
| `toc_lib.py` | Heading extraction, TOC tree, and `strip_quiz_blocks` (quizzes excluded from TOC). |
| `quiz_lib.py` | Parse quizzes; used by `toc_lib` and `parse_quiz.py`. |

## Local use (from a workshop repository)

Clone this repo **next to** your workshop (or anywhere), then from the **workshop root** (where `metadata.yaml` lives):

```bash
git clone https://github.com/Manta-Epitech-Academy/workshop-metadata-tools.git
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
`https://raw.githubusercontent.com/Manta-Epitech-Academy/workshop-metadata-tools/main/metadata.schema.json`).

## Documentation

- [`docs/STRUCTURE.md`](docs/STRUCTURE.md) — metadata model, diagrams (Mermaid), and layout.
- [`docs/QUIZ.md`](docs/QUIZ.md) — quiz blocks in Markdown (not in `metadata.yaml` / `toc`).
- [`docs/structure-diagrams.html`](docs/structure-diagrams.html) — same diagrams as STRUCTURE in a browser (open locally).

## CI

Workshop repositories call the reusable workflow:

`Manta-Epitech-Academy/workshop-metadata-tools/.github/workflows/verify-metadata-reusable.yml@main`

See the workshop template (`TEMPLATE.md` / `README.md`) for the exact workflow snippet.
