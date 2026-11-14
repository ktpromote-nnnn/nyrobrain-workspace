# Agents

**Always read `@AGENTS-core.md` first.** It is the authoritative source for
project conventions, strategy-writing rules, datasource access, knowledge-base
usage, and compute / OOM limits. Treat it as binding for every task.

`AGENTS-core.md` is admin-managed and updated on every pod start. The file
you are reading now (`AGENTS.md`) is yours — edit it freely. Use the section
below to record project-specific notes, ad-hoc instructions, working
preferences, or context you want the AI to carry across sessions.

## Keep adrs at >= 1.14.0

Work in this repo needs **adrs>=1.14.0** — the release whose portfolio
publisher writes its targets to Prime, which is what the execution path reads. A workspace seeded
before that may still be on an older version, so check and upgrade before any
adrs work:

```bash
uv run python -c "import adrs,sys; v=tuple(int(x) for x in adrs.__version__.split('.')[:3]); sys.exit(0 if v>=(1, 14, 0) else 1)" \
  || uv add "adrs>=1.14.0"
```

`uv add "adrs>=1.14.0"` updates `pyproject.toml`, re-locks, and syncs the venv.
If the installed version already satisfies the constraint the check is a no-op.

Compare as a tuple, not as a string: `"1.5.3" > "1.13.0"` lexicographically, so
a string comparison would silently leave an old workspace un-upgraded — which is
precisely the case this check exists to catch.

## My notes

<!-- Add your own instructions, preferences, or context below. -->
