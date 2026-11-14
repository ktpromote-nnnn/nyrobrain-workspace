# Agents

## Before You Do Anything

Read and internalize `SOUL.md` at the root of this repository. It defines who you are, how you think, and what you believe. These are not guidelines — they are your operating identity. Adopt them before interacting with the human or writing any code.

## Project

This is a quant research repository using the `adrs` library for writing and backtesting trading strategies.

- Python 3.14, managed with `uv`
- Dependencies: `adrs`, `polars`, `matplotlib`

## Directory Structure

- `docs/` - Documents above internal tools or user defined instructions.
- `brain/` - Knowledge base. First subfolder = category: `brain/strategy/` (strategy outputs), `brain/concept/`, `brain/source/`. Files directly in `brain/` count as sources; new subfolders create new categories.

## Storage Paths

Read **`docs/conventions/storage-paths.md`** for the full convention.
Short version: code reads `$NYROBRAIN_WORKSPACE` for durable state and
`$NYROBRAIN_DATA_DIR` for the data-loader cache. Both env vars resolve
to the right path in both cloud pod and desktop local mode.

**Never write code, scripts, plots, images, reports, or any user-facing
files to `$NYROBRAIN_DATA_DIR`.** That directory is reserved exclusively
for the data caching layer and is off-limits to the file server —
anything placed there cannot be read back, rendered, or shown to the
user (image requests against `$NYROBRAIN_DATA_DIR` paths are blocked).

Write all generated artifacts under `brain/strategy/`, `brain/source/`,
`brain/concept/` (or any `brain/<category>/`), or another in-repo
directory inside `$NYROBRAIN_WORKSPACE`. If you find yourself reaching
for `$NYROBRAIN_DATA_DIR` as a scratch location, pick a project-relative
path under the current task's working directory instead.

## Writing Trading Code

Before writing any strategy or portfolio, read these resources:

1. **`docs/pipelines/README.md`** — Pipeline index. Follow the selection rule defined there exactly: one matching pipeline → use it; multiple → ask the user, listing each by title and one-line description. The chosen pipeline doc is the authoritative spec — follow it exactly (directory layout, file structure, code shape, summary template).
2. **`docs/adrs/`** — Full ADRS library docs. Start with `docs/adrs/guide/` for the writing guide. Online: https://docs.balaenaquant.com/docs/adrs/guide/writing-an-alpha
3. **`docs/datasources/README.md`** — How to form data topics from endpoint schemas.

Each pipeline doc embeds a full reference implementation (code + summary) at the bottom. Use it as the template for file structure, code style, and summary format.

NOTE: Backtests write their output as `report.parquet` (pyarrow/polars). Older strategies may still have `report.parquet.png` from a prior workaround — the UI reads that as a fallback, but new code should always write `report.parquet`.

### Strategies

Pick a strategy pipeline from `docs/pipelines/README.md` (pipelines that evaluate a single alpha). One pipeline → proceed; multiple → ask user.

### Portfolios

Pick a portfolio pipeline from `docs/pipelines/README.md` (pipelines whose scope is combining multiple alphas). One pipeline → proceed; multiple → ask user.

Additional constraints that apply across all portfolio pipelines:

- Load existing strategies **by file path** as specified in the pipeline doc — never import dated directory names as modules.
- Default allocator is `MeanWeightAllocator` (equal weight) unless explicitly specified.
- Every `base_asset` in the alpha registry must have a matching `Evaluator` entry; every alpha `id` must be unique within the portfolio.
- `summary.md` follows the same discipline as a strategy summary: YAML frontmatter + all plots embedded with commentary.
- **Backtest only.** Live execution and order routing are out of scope — never generate them.

## Datasource

When asked about what kind of data to use, you can refer to endpoints from [Glassnode](https://docs.glassnode.com/basic-api/endpoints) and [CryptoQuant](https://cryptoquant.com/docs). Then you can refer to [ADRS Data](https://docs.balaenaquant.com/docs/adrs/data#topic-format) for writing them according to the Topic format recognized by adrs.

Also, you can check for the endpoints in `docs/datasources/`.

### Inspecting Data Shape

Before writing any strategy that uses a datasource topic, **always query the topic directly** to see the actual column names, types, and sample values. Do not guess the response structure.

Use this script, replacing the `topic` with the one you want to inspect:

```python
import os
import asyncio
import cybotrade_datasource
import pandas as pd

DATASOURCE_PROXY_URL = os.environ["DATASOURCE_PROXY_URL"]
USER_ID = os.environ["USER_ID"]

async def main():
    data = await cybotrade_datasource.query_paginated(
        api_key=USER_ID,
        topic='cryptoquant|btc/inter-entity-flows/miner-to-miner?from_miner=f2pool&to_miner=all_miner&window=hour',
        limit=1000,
        api_url=DATASOURCE_PROXY_URL,
    )
    df = pd.DataFrame(data)
    print(df)

asyncio.run(main())
```

Run it with `uv run script.py` (or `python script.py` if the environment is already active). Inspect the printed DataFrame — note the column names, units, and any null patterns — then write the strategy accordingly.

## Showing images to the user

When you generate or want to display an image (plot, chart, screenshot, etc.) that lives in the workspace, emit
markdown image syntax referencing the relative path:

![Description](relative/path.png)

Do NOT call the `read` tool on image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`) just to display them
to the user. The frontend renders the image directly from the path. Reading wastes tokens (base64 inflates ~33%)
and adds latency.

Only call `read` on an image when you specifically need to inspect its contents yourself (e.g. count colored bars
in a chart, read text in a screenshot). In that case, after inspection, still emit `![](path)` for the user view.

## Knowledge Base

You have four KB tools available via MCP (`kb_list`, `kb_search`, `kb_graph`, `kb_reindex`). Call them as structured tools — no need to shell out to curl.

- `kb_list` — list all KB files (path, type, title, status, tags)
- `kb_search` — full-text + hybrid-embedding search; args: `query` (string), `k` (number, optional, default 10)
- `kb_graph` — return the full knowledge graph (nodes, edges)
- `kb_reindex` — force a full reindex from filesystem (rarely needed; watcher handles updates)

When a user asks about strategies, prior experiments, or trading ideas, first call `kb_list` (cheap, always) and `kb_search` for specifics; then `read` the top-k matched files before responding. Cite file paths in your response.

Knowledge lives under `brain/`, and a file's category is its first folder: `brain/strategy/<date>_<name>/summary.md`, `brain/concept/<slug>.md`, `brain/source/<date>_<slug>.md`. A file placed directly in `brain/` is a source; new folders become new categories.

When adding or updating a strategy, always write/overwrite the single `brain/strategy/<date>_<name>/summary.md` markdown — do not create auxiliary markdown files per strategy.

When ingesting an external source (paper, tweet, YouTube video, post) at user request, create `brain/source/<date>_<slug>.md` with frontmatter:
```yaml
---
type: source
source_type: paper|tweet|video|post
title: ...
url: ...
authors: [...]
date: YYYY-MM-DD
tags: [...]
---
```
and a concise summary in the body. Link related notes via frontmatter `links: [{ target: brain/<category>/<name>.md, kind: derives_from|related|contradicts }]` or inline `[[brain/<category>/<name>.md]]` — always use full `brain/`-rooted paths in link targets.

When the user asks for synthesis across sources, create `brain/concept/<slug>.md` capturing the recurring theme. Link it to the sources it emerged from.

## Compute Limits & OOM Handling

Every `bash` tool invocation runs inside a per-call cgroup v2 sub-cgroup with a hard `memory.max` fence and an RLIMIT_AS ceiling. The pod also has a fixed total RAM budget — exceeding it kills the offending process, not the workspace.

**How OOM surfaces in tool output:**
- Exit code `137` (SIGKILL by the OOM killer) or `139` (SIGSEGV after partial alloc)
- Stderr containing `Killed`, `MemoryError`, `Cannot allocate memory`, `std::bad_alloc`, `cgroup out of memory`, or polars/numpy/pyarrow allocator panics
- Process terminates abruptly with no traceback (cgroup kills are silent — no Python exception)

**When you see those signals, follow this order:**

1. **First failure** — assume transient or fixable. Retry with one of:
   - Stream / batch the input (process in chunks, write intermediate results to disk)
   - Drop unnecessary columns before loading (polars `select` / `scan_parquet` lazy + projection pushdown)
   - Use `polars.scan_*` lazy frames instead of eager `read_*`
   - Reduce numpy/pandas dtypes (`float64` → `float32`, `int64` → `int32`) where precision allows
   - Free intermediate variables explicitly + `gc.collect()`

2. **Second failure on the same step** — before running anything, tell the user: "The command ran out of memory. Checking workspace memory limits…". Then measure using this probe (no pipes — `cat | head` can stall the tool when the parent shell is still cleaning up after an OOM kill; `timeout 5` guards against a hung shell):
   ```bash
   timeout 5 bash -c 'echo "memory.max=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo unknown)"; grep -E "^(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree):" /proc/meminfo 2>&1 || echo "meminfo unavailable"'
   ```
   The `echo` wrappers guarantee at least one line on stdout even when the files are missing. Convert to GiB. Compare against your best estimate of the script's working-set (input file size × dtype expansion + intermediate frames). If the working set is anywhere near `memory.max`, do NOT retry blindly — the next attempt will OOM the same way.

3. **Third failure or estimate > limit** — stop retrying. Report to the user in this exact shape:
   > **Out of memory.** This workspace has roughly `<X> GiB` of usable RAM per command, and the script needs an estimated `<Y> GiB` to load the working dataset (`<reasoning>`). Options:
   > - Sample down the input (e.g. load only N most recent rows)
   > - Split the computation across multiple bash invocations
   > - Upgrade your compute tier for more RAM (settings → billing)

   Pick one of these recommendations and tell the user which you'll attempt next, or wait for their decision if the trade-off is material.

**Do not** silently shrink the dataset behind the user's back to "make it fit" — that changes the science. State the trade-off and let them choose.
