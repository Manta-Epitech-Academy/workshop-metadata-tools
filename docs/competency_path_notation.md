# Competency references in the TOC (`competency`)

Workshop metadata ties TOC sections to grading / API hooks using **structured objects only** (no legacy dot-codes, no parallel slash-string arrays).

Each TOC node may include:

```yaml
competency:
  - domain: PROG
    skill: "01"
    level: A1
    project: pypong
    obs_index: 1
    observable_id: pypong.1
```

## Fields

| Field | Meaning |
|-------|---------|
| `domain` | Uppercase domain (`PROG`, `TRANS`, …). |
| `skill` | Skill number as digits (`01`, `1`, …). |
| `level` | Level code (`A1`, `A2`, …). |
| `project` | Workshop slug; must equal `project.slug` in `metadata.yaml`. |
| `obs_index` | For **PROG** (and other framework-backed domains): the **`obs_num`** segment in `GET /api/v1/resolve/{domain}/{skill}/{level}/{project}/{obs_num}` from **[competency-framework](https://github.com/kevin-cazal/competency-framework)**. For **TRANS** (no API tree yet), use your workshop’s ordinal for that hook. |
| `observable_id` | Required when this file declares **`observables`**: must be one of the declared ids (typically `{project.slug}.N`). |

Equivalent **slash path** for display or URLs (PROG only):

```text
{domain}/{skill}/{level}/{project}/{obs_index}
```

Example: `PROG/01/A1/pypong/1` → `GET /api/v1/resolve/PROG/01/A1/pypong/1`.

## `observables` and `observable_id`

When `observables:` is present, **`check_toc.py`** requires every `competency` row to include **`observable_id`** and that id must appear in the `observables` list.

Design discussion (upstream): [workshop-metadata-tools issue #1](https://github.com/Manta-Epitech-Academy/workshop-metadata-tools/issues/1).
