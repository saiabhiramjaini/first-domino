---
paths:
  - "packages/fd-scripts/**"
---

# fd-scripts rules

- Each script is a module run with `python -m fd_scripts.<name>` and has a `main()` with a `click` command.
- Scripts may import any package. Nothing imports `fd-scripts`.
- `print` is allowed here for command output; use the logger for everything else.
- Output locations are fields on `ScriptsSettings`, defaulting to `../api/openapi.json`, `data/datasets/` and `data/benchmarks/`. Never write outside the repo.
- The benchmark scores every method on the same labelled runs with the same model, and records cost and time next to accuracy.
