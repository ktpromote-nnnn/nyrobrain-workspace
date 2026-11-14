---
name: portfolio
description: >
  Combine alphas into a portfolio and backtest it, following a pipeline the
  user chooses. Use when the user wants to create or work on a portfolio --
  "/portfolio", "build a portfolio", "combine my alphas". The second step of
  the Nyrobrain workflow, after /strategy and before /execution.
metadata:
  kind: entry
  step: "2"
---

# Building a portfolio

You are helping the user combine one or more **alphas** into a **portfolio**:
weighted, backtested, and producing the signal history an OMS will later trade.

As with `/strategy`, this command selects a *pipeline* and follows it. It is not
itself a methodology.

## 1. Check there is something to combine

A portfolio needs alphas. If `brain/strategy/` is empty, stop and point the user
at **`/strategy`** — building a portfolio out of nothing is a longer way to
discover the same thing.

## 2. Choose the pipeline

Portfolio pipelines are skills whose **name begins `pipeline-portfolio-`**.
List them with `opencode debug skill`, filter on the `name` field and read each
`description`. Those two fields are all the listing exposes — `metadata` is not
readable from it, so do not try to match on one.

- **Exactly one available** — use it.
- **Two or more** — **ask, and wait.**

The same rule as `/strategy`, for the same reason: the pipeline decides how the
portfolio is evaluated, and a user who does not know which one ran cannot read
their own results.

## 3. Follow it

Invoke the chosen pipeline skill and do what it says.

Two parts of the result are load-bearing beyond the dashboard, because the
execution path reads them:

- **`portfolio.py` must export an `async setup_portfolio`** returning
  `(portfolio, alphas, evaluator, datamap)`. The OMS entrypoint unpacks exactly
  that shape; a three-tuple, or a synchronous function, fails at run time rather
  than here.
- **Alpha paths must appear as quoted `brain/strategy/...` literals** inside
  `portfolio.py`. Deployment picks which alpha files to package by scanning the
  source text for them. A literal works whether it sits at the call site or in a
  variable — what fails is *composing* the path (`Path(...) / name`,
  `os.path.join(...)`), which ships without that alpha, or an **f-string**,
  which is worse: it matches as the literal `brain/strategy/{name}/alpha.py`, so
  the bundler looks for a file that cannot exist.

Both are in `ops/pipeline/CONTRACT.md`. Run **`/check-pipeline`** on the finished
directory rather than trusting a reading.

## 4. Say what comes next

A portfolio produces signals; it does not place orders. When the backtest is
done, tell the user the next step is **`/execution`**, which writes the OMS that
trades those signals.

For their own methodology: **`/make-pipeline portfolio`**.
