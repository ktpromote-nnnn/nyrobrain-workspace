# Pipelines have moved to skills

The two pipelines that used to live here — the Back/Forward 73-Split alpha
pipeline and the Portfolio Backtest — are now **skills**, and you reach them by
running a command rather than by finding a file:

| Instead of reading | Run |
| --- | --- |
| `1-backforward-73split.md` | `/strategy` |
| `2-portfolio.md` | `/portfolio` |

Each command asks which pipeline you want and then follows it. New here? Start
with **`/guide`**.

## Why

A pipeline is a methodology — how your work is split, what is measured, what
counts as a pass — and methodology is yours. As skills, pipelines can be
authored (`/make-pipeline`), listed, and chosen, instead of being documentation
you were expected to find and follow by hand.

It also fixed a real problem: this folder could not tell an *alpha* pipeline
from a *portfolio* one, so anything counting the files here would offer you the
portfolio pipeline when you asked to write a strategy.

## Your own files are untouched

**Nothing here has been deleted.** If you wrote your own pipeline in this folder
it is exactly where you left it, and it still works as a document you follow by
hand.

To make it selectable by `/strategy` or `/portfolio` — listed alongside the
shipped ones, with the contract checked — run **`/make-pipeline alpha`** or
**`/make-pipeline portfolio`** and tell it you are porting an existing one.

If you still see `1-backforward-73split.md` or `2-portfolio.md` here, those are
superseded copies from before the move. They are safe to delete, and nothing
reads them any more.

## The parts other code reads

Some of what a pipeline prescribes is a **contract** — the dashboard, the report
panel and the deployment bundler all read specific names — and most violations
are silent, showing up as work that simply never appears.

That contract is now written down and checkable:

- `ops/pipeline/CONTRACT.md` — what is contract and, just as usefully, what is
  yours to change.
- **`/check-pipeline`** — run it on a strategy or portfolio directory and it
  tells you which consumer breaks, and why.
