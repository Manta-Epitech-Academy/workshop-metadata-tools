# TOC runtime rules (markdown ↔ metadata)

When tooling builds or checks the table of contents from Markdown `#` headings, it uses the same rules as `toc_lib.markdown_to_toc_sections`:

| Markdown | YAML level |
|----------|------------|
| `#` (H1) | `sections[].title` |
| `##` (H2) | `sections[].parts[].title` |
| `###` (H3) | `sections[].parts[].subparts[].title` |

## Ignored headings

- **`####` and deeper (H4–H6)** are **not** represented in `metadata.yaml` `toc`. They may still exist in the `.md` file for local structure; generators **do not** nest them under `subparts`.
- **`##` (H2) before the first `#` (H1)** in a file is ignored (**orphan part**).
- **`###` (H3) before the first `##` (H2)** after the current H1 is ignored (**orphan subpart**).

These rules keep the authored `toc` aligned with a fixed **three-level** outline while allowing richer Markdown elsewhere.
