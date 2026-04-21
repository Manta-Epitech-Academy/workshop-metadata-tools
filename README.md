# workshop-metadata-tools

Shared Python tooling for [Epitech Academy](https://epitech.academy) workshop repositories: validate `metadata.yaml`, keep the **`toc`** in sync with Markdown headings, and check competency codes (`cf_code`) against observables.

Workshop repos (created from the subject template) only contain `metadata.yaml`, `metadata.schema.json`, and `.md` sources. **CI checks out this repository** next to the workshop and runs the scripts from here.

## Scripts

| Script | Role |
|--------|------|
| `sync_metadata_toc.py` | Creates a default `metadata.yaml` if missing, or regenerates **`toc`** from `documents` / headings; validates against `metadata.schema.json`. |
| `check_toc.py` | Ensures `toc` matches headings and validates `cf_code` / observables. |
| `generate_toc.py` | Prints a `toc` YAML fragment from one or more `.md` files (optional helper). |
| `toc_lib.py` | Shared heading extraction and TOC tree logic. |

## Local use (from a workshop repository)

Clone this repo **next to** your workshop (or anywhere), then from the **workshop root** (where `metadata.yaml` lives):

```bash
git clone https://github.com/Manta-Epitech-Academy/workshop-metadata-tools.git
pip install -r workshop-metadata-tools/requirements.txt
export PYTHONPATH="$PWD/workshop-metadata-tools"
python workshop-metadata-tools/sync_metadata_toc.py
python workshop-metadata-tools/check_toc.py
```

Or with an absolute path to `workshop-metadata-tools` and `PYTHONPATH` set to that directory.

## CI

Workshop repositories call the reusable workflow:

`Manta-Epitech-Academy/workshop-metadata-tools/.github/workflows/verify-metadata-reusable.yml@main`

See the workshop template README for the exact snippet.
