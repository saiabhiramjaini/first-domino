# fd-scripts

Command-line tools: OpenAPI export, labelled dataset builder and the benchmark.

- **Layer:** Tooling
- **May import:** any package
- **Must never import:** (nothing imports this package)
- **Rules:** [`.claude/rules/scripts.md`](../../.claude/rules/scripts.md)

## Modules

| Module | Job |
| --- | --- |
| `export_openapi` | Write ../api/openapi.json from the API app. |
| `make_dataset` | Build labelled failed runs by planting bugs into successful runs. |
| `benchmark` | Score First Domino and the baseline judge on the labelled runs. |

Status: layout only. Modules hold a docstring that states their job; no code yet.
