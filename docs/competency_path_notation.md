# Competency observable path (slash notation)

Workshop tooling and the **[competency-framework](https://github.com/kevin-cazal/competency-framework)** API use a single **canonical path** for an observable inside a project workshop:

```text
DOMAIN / skill_nn / LEVEL / project_slug / obs_index
```

Example mapping from legacy **`cf_code`** (`metadata.yaml`):

| Legacy `cf_code` | Canonical slash path |
|------------------|------------------------|
| `PROG-01.A1.1`   | `PROG/01/A1/pypong/1`  |

- **`skill_nn`**: digits only (`01`, `2`, …), not the full `PROG-01` id.
- **`LEVEL`**: level code such as `A1`, `A2`.
- **`obs_index`**: 1-based index within that skill’s observables for the same **level** and **project** (same segment as `GET /api/v1/resolve/.../{obs_num}` in competency-framework).
- **`TRANS-*`** codes are not mapped in the framework tree yet; keep them as **`cf_code`** only until a TRANS domain exists.

## In `metadata.yaml` (this fork)

`metadata.schema.json` allows, on each TOC node:

- **`cf_code`**: legacy list `DOMAIN-SKILL.LEVEL.OBS_NUM` (unchanged).
- **`competency_path`**: list of slash strings (canonical); each path’s `project_slug` must equal `project.slug`.
- **`competency`**: list of structured objects `{ domain, skill, level, project, obs_index }` (same meaning as one slash path).

When **`observables`** is declared, **`cf_code`** still drives **`{project.slug}.N`** binding (last segment of each code → observable id). Use **`competency_path`** / **`competency`** alongside **`cf_code`** so tools and humans see the resolve path without duplicating observable prose.

Design discussion (upstream thread): [workshop-metadata-tools issue #1](https://github.com/Manta-Epitech-Academy/workshop-metadata-tools/issues/1).
