---
name: strategy
description: >
  Write a trading alpha, following a pipeline the user chooses. Use when the
  user wants to create, start or work on a strategy or alpha -- "/strategy",
  "write me an alpha", "new strategy". The first step of the Nyrobrain
  workflow: strategy, then portfolio, then execution, then deploy.
metadata:
  kind: entry
  step: "1"
---

# Writing a strategy

You are helping the user write a trading **alpha**: a signal, backtested and
forward-tested, that a portfolio can later combine with others.

This command does not contain a methodology. It **selects** one — a *pipeline*
— and then follows it exactly. The pipeline decides the directory layout, the
shape of the code, what gets measured and what counts as a pass.

## 1. Choose the pipeline

Alpha pipelines are skills whose **name begins `pipeline-alpha-`**. List them
with:

```bash
opencode debug skill
```

Filter on the `name` field and read each candidate's `description`. Use those
two fields and nothing else: `opencode debug skill` returns only `name`,
`description`, `location` and `content`, and `content` is the body **without**
its frontmatter — so a skill's `metadata` is not readable from the listing, and
anything relying on it silently matches nothing.

- **Exactly one available** — use it. There is nothing to resolve, and asking a
  question with one answer wastes the user's attention.
- **Two or more** — **ask, and wait.** List each by title and summary and let
  the user pick.

**Never choose on the user's behalf when there is a choice.** A pipeline decides
how a strategy is evaluated: which split, which holdout, what counts as a pass.
A user who does not know which methodology produced their numbers cannot judge
them. This is the one thing in this command that is not negotiable.

Do not mix pipelines within one strategy directory.

## 2. Follow it

Invoke the chosen pipeline skill and do what it says. It is the authority on
layout, file names, frontmatter and metrics — not this command, and not your
own sense of how a backtest should look.

Parts of a pipeline are a **contract**: other things read them. The workspace
dashboard lists strategies by their directory name and frontmatter; the report
panel reads a specific parquet envelope and specific column names. Get one wrong
and the failure is silent — a strategy that never appears, or a report that says
"No report found". The contract is enumerated in `ops/pipeline/CONTRACT.md`, and
`/check-pipeline` will tell you whether a finished directory satisfies it.

## 3. Refuse what will fail later

Stop and say so, rather than producing work that breaks downstream:

- A strategy directory that is not `brain/strategy/<YYYY-MM-DD>_<name>/`. The
  dashboard filters on that date prefix and will silently not list it.
- A missing or malformed `summary.md` frontmatter.
- Metrics the chosen pipeline does not define. Inventing a measure is fine in a
  user's own pipeline; inventing one *inside* someone else's is how two
  strategies stop being comparable.

## 4. Say what comes next

An alpha on its own trades nothing. When the strategy is written and its report
exists, tell the user the next step is **`/portfolio`**, which combines one or
more alphas into something an OMS can execute.

If they have outgrown these pipelines and want their own methodology, that is
**`/make-pipeline alpha`**.
