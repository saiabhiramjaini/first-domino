# fd-scripts

Command-line tools: OpenAPI export, labelled dataset builder and the benchmark.

- **Layer:** Tooling
- **May import:** any package
- **Must never import:** (nothing imports this package)
- **Rules:** [`.claude/rules/scripts.md`](../../.claude/rules/scripts.md)

## Modules

| Module | Job |
| --- | --- |
| `settings` | ScriptsSettings: output folders, clean runs per call, doom samples and concurrency. |
| `dataset` | The labelled dataset models, with save and load. |
| `convert` | Converts the demo agent's OpenAI message params to and from `fd-shared` models. |
| `make_dataset` | Builds labelled failed runs by planting bugs into successful runs, keeping only doomed ones. |
| `in_process` | Engine port adapters that replay the demo agent in this process, for the benchmark. |
| `scoring` | Per-case results and the scores computed from them. |
| `benchmark` | Scores First Domino and the read-the-trace judge on the same labelled runs. |

## Run, from `backend/`

```bash
uv run python -m fd_scripts.make_dataset
uv run python -m fd_scripts.benchmark --limit 3 --no-db
uv run python -m fd_scripts.benchmark
```

Both need `OPENAI_API_KEY`, `FD_DEMO_AGENT_MODEL` and `FD_ENGINE_STRONG_MODEL`; the benchmark also needs Postgres unless `--no-db`. Output goes to `data/datasets/` and `data/benchmarks/` (not tracked).

A label is the planted step only when the run is doomed there: the clean run it came from passed with the steps before it, and `doom_samples` replays from the planted step all fail.
