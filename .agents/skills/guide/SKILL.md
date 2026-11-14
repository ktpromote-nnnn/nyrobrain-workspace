---
name: guide
description: >
  Where to start in a Nyrobrain workspace, and what the commands do. Use when
  the user is new, asks how any of this works, says "/guide", "where do I
  start", "what can I do here", or seems unsure which command they want.
metadata:
  kind: entry
  step: "0"
---

# Where to start

Four commands, in this order:

    /strategy   →   /portfolio   →   /execution   →   /deploy
    write an        combine them     write the OMS    run it on
    alpha           into a           that trades      Prime compute
                    portfolio        them

Each one ends by naming the next, so a user who starts at `/strategy` is never
guessing.

## First, work out where they already are

Do not recite the list above at someone who is halfway through it. Look:

| What you find | Where they are |
|---|---|
| `brain/strategy/` empty or absent | The beginning. `/strategy`. |
| strategies but no `brain/portfolio/` | `/portfolio`. |
| a portfolio but no `brain/execution/` | `/execution`. |
| both | `/deploy` — but read the money section below first. |
| a `.prime_deployment*` file in a portfolio directory | Already deployed. `/monitor`. |

Say where they are and what is next, in a sentence. Offer the list only if they
ask what everything does.

## What each one is for

**`/strategy`** writes one alpha: a signal, backtested and forward-tested. It
asks which *pipeline* — the methodology — to follow, because that decides how
the strategy is judged and the user should know which one produced their
numbers.

**`/portfolio`** combines alphas into something weighted and backtested, which
produces the signals an OMS will trade. Also pipeline-driven.

**`/execution`** writes the OMS into `brain/execution/<date>_<oms_id>/`: three
files, and it matters which is which. `hooks.py` is the user's — the placement
strategy, the one thing the library exists to let them replace. `config.json` is
data. **`oms.py` is regenerated** whenever `/execution` runs again, which is how
it picks up library updates, so edits to it do not survive.

**`/deploy`** packages the portfolio and the OMS into one archive and runs both
on Prime compute, under a supervisor that exits if either dies.

**`/monitor`** comes after: it finds what the user has deployed, asks which
account, portfolio or alpha to look at, and shows its live PnL, drawdown,
positions and alpha health.

## Two more, off the path

**`/check-pipeline`** answers "why is my work not showing up". Nearly every way
a strategy can be malformed is silent — it simply never appears in the
dashboard, or the report says "No report found". This is the command that says
which one, and why.

**`/make-pipeline`** authors a new methodology as a skill, when the shipped
pipelines do not fit. **Not a beginner's command.** Writing a good pipeline is a
different skill from doing good research, and the defaults were considered. It
is for someone who has already outgrown them and can say exactly how.

## Money, before they get there

Say this early — at `/guide`, not at the moment of deploying, when a user is
committed and reading quickly.

- **`/deploy` can spend money.** Prime compute is billed per deployment.
- **The free tier covers one instance.** `shared` is free through a grant on the
  *first* deployment; a second one is charged.
- **Live means real capital.** `/deploy` asks, in plain language, and will not
  infer it from a flag or a tier. If the answer is not an unambiguous yes, it
  does not happen.
- Nothing accepts Prime's compute terms on the user's behalf. That waiver is
  only worth something if the person liable read it.

## What this command is not

It is a map, not a manual. The pipelines run to tens of thousands of words and
the library has its own documentation; restating either here would produce a
third version that drifts from both. Point, and let the command that owns a step
explain that step.
