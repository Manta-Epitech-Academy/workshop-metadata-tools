# Changelog

## 1.5.0 (unreleased)

- **Breaking:** `metadata.toc` is only the multi-document array of `{ document, sections }`. Removed legacy flat `toc` validated against `project.entrypoint`.
- **Breaking:** Replaced recursive `TocNode.parts` with **`TocSection` → `parts` (`TocPart`) → `subparts` (`TocSubpart`)**, aligned to H1 / H2 / H3. Markdown H4+ are not reflected in `toc` (see `docs/TOC_RUNTIME.md`).
- Schema: optional **`observables`** (with `skill_path` + optional `id`) on section, part, or subpart alongside **`competency`**.
- `toc_lib.markdown_to_toc_sections`, `check_toc.py`, `sync_metadata_toc.py`, and `generate_readme.py` updated for the new shape.
