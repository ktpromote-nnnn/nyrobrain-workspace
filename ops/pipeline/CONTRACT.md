# The pipeline contract

**Generated from `ops/pipeline/contract.json` — do not edit.**
Run `python ops/pipeline/check.py --emit-doc > ops/pipeline/CONTRACT.md`.

These are the things other code reads. Everything else in a pipeline is
methodology, and yours to change.

Each rule names its consumer, because that is what makes it a contract
rather than a preference.

## Strategies

### `strategy-dir-dated`

- **Breaks:** The dashboard filters on the date prefix. Without it the strategy is never listed.
- **Read by:** `apps/web/.../StrategyDashboardPane.tsx:19,152`
- **Fails silently:** yes

### `report-parquet-present`

- **Breaks:** The report panel reports 'No report found'.
- **Read by:** `ReportPanel.tsx:56-57,83-84,1047,1057`
- **Fails silently:** yes

## Portfolios

### `portfolio-entrypoint`

- **Breaks:** The publisher cannot start. A synchronous def fails before the helpful error in call_setup_portfolio and reports something less useful.
- **Read by:** `nyrobrain.portfolio.run:74,77-107 (load_setup_portfolio, call_setup_portfolio); nyrobrain.prime.bundle:117 (nyrobrain_alpha_files)`
- **Fails silently:** no

### `portfolio-alpha-literals`

- **Breaks:** Deployment selects alpha files by regex-scraping quoted brain/strategy/... literals out of the source. A literal is found whether it sits at the call site or in a variable; a path composed at runtime (Path(...) / name, os.path.join) matches nothing and that alpha silently does not ship, and an f-string matches the literal text brain/strategy/{name}/alpha.py so the bundler hunts a file that cannot exist.
- **Read by:** `nyrobrain.prime.bundle:41 (_STRATEGY_REF_RE)`
- **Fails silently:** yes

## Both

### `summary-present`

- **Breaks:** The dashboard has nothing to show and wikilinks to this directory do not resolve.
- **Read by:** `StrategyDashboardPane.tsx:159,162,232; WorkspacePage.tsx:418; remark-wikilink.ts:95`
- **Fails silently:** yes

### `summary-frontmatter`

- **Breaks:** A missing key drops the entry from the dashboard listing or the knowledge-base index.
- **Read by:** `StrategyDashboardPane.tsx; apps/mcp/src/indexer.ts:33,48,95-96`
- **Fails silently:** yes

### `summary-status-value`

- **Breaks:** An unrecognised status is dropped from the dashboard filter entirely.
- **Read by:** `StrategyDashboardPane.tsx:38-52 (STATUS_ALIASES)`
- **Fails silently:** yes
- **Note:** The shipped pipelines assert in bold that success/fail/review must NOT be used. That is false: STATUS_ALIASES accepts all thirteen spellings above. The prohibition over-restricts, so obeying it is harmless, but it is not the contract.

## Yours to change

- The train/test split, and its ratio.
- Which metrics are computed and what counts as a pass.
- The narrative structure and prose of summary.md.
- File names inside the directory: alpha.py, backtest.py, plot.py, assets/.
- Every chart and its filename. No code reads any PNG name.
- The four portfolio parquets. No reader was found for any of them.
- The frontmatter keys author and revision. No reader.

