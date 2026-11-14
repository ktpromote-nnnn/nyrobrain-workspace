---
name: monitor
description: >
  Show how a deployed portfolio, trading account or alpha is doing, from live
  Aegis data. Use when the user says "/monitor", asks how a deployment, paper
  or live account, or their strategies are doing, or asks about PnL, drawdown,
  positions, trades or misbehaving alphas on Prime.
metadata:
  kind: entry
  step: "5"
---

# Monitoring a deployment

Everything here is read-only and comes through `aegis_call`. Each result
renders as its own card in the chat — chart, table or calendar — so the cards
carry the numbers and your prose carries the verdict.

## 1. Connect

Call `aegis_list_tools`. A `no_api_key` answer means Aegis has never been set
up in this workspace: ask the user for their Nyrobrain API key, pass it to
`aegis_set_key`, and continue. `unauthorized` means the stored key was revoked;
ask for a fresh one the same way.

Done when `aegis_list_tools` returns the catalogue.

## 2. Find what is deployed

Call `aegis_accounts` with `include_alphas: "1"` and no `name` filter. It
returns every portfolio and account the user can see, with the ids exactly as
Prime stores them. **These ids are the only ones you use.** The workspace's
`config.json` files hold bare names, and deployed ids are usually namespaced by
the deployer (`{user_id}_{bare name}`) — but not always — so any id you build
yourself is a guess. A portfolio's displayed `name` is the bare name; its
`portfolioId` is the namespaced one, and only the id goes into later calls. When
the user names something ("my delta1 portfolio"), match it against this list;
if several match, that is a question for step 3, not a pick for you.

An empty list means this key has no grant on anything. Say so and stop; do not
try name variants.

Done when you hold the list, and every portfolio the user mentioned is either
matched to an entry or reported as not found.

## 3. Ask what to monitor

Skip this step when the user already named exactly one target and a window.
Otherwise ask with the `question` tool, one call, up to two questions:

- **What** — one option per active account (label it by portfolio name, account
  label or exchange, and paper/live if the label says so), one per portfolio
  whose *strategies* they may want checked, plus "All accounts combined" —
  total equity and the month's daily PnL summed across accounts. Stopped and
  archived accounts go last. Offer at most six options; the free-text answer
  covers the rest.
- **Window** — Last 24 hours · Last 7 days · Month to date · Last 30 days.
  Default to the last 7 days if they skip it.

Get the current UTC time with `date -u +%Y-%m-%dT%H:%M:%SZ` and compute the
window from it; Aegis wants ISO 8601 with a `Z`.

Done when you know the target ids and the start and end timestamps.

## 4. Fetch the recipe for each target

Run every call in the recipe for each target chosen. Independent calls can go
out in parallel. Parameter names matter — Aegis drops a misspelled one silently
and answers with its default:

| Target | Calls |
|---|---|
| **All accounts combined** | `aegis_equity_all` (`start_time`, `end_time`, `interval_ms` ≈ window ÷ 200), `aegis_calendar` (`year`, `month` of the window's end) |
| **An account** (`oms_id`) | `aegis_equity` and `aegis_drawdown` (`start_time`, `end_time`, `pts: 200`), `aegis_position` (`latest: "1"`), `aegis_trade` (`limit: 20`) |
| **A portfolio's strategies** (`portfolio_id`) | `aegis_alphas_health`, `aegis_alphas_alert`, `aegis_alphas_signal_activity` — these three take **`from` / `to`**, not `start_time` / `end_time`. Call `aegis_alphas_health` with `gm` left out: the per-alpha rows step 5 reads come back only then, and `gm: "1"` collapses them into a single `{"alerting": N}` count |
| **One alpha** (`alpha_id`) | `aegis_alpha_signal`, `aegis_alpha_alert` (`start_time`, `end_time`); `aegis_alpha_equity` also needs `asset` = the alpha's `base_asset` from step 2 |

Add `aegis_equity_backtest` (`portfolio_id`) beside an account's equity only
when the user asks how live compares with the backtest; it is an index rebased
to 100 and simulated, so compare shapes and percentages, never levels.

Done when every call in every chosen target's row has returned — a result, an
empty result or an error all count as returned.

## 5. Report

Lead with the verdict in one or two sentences — healthy, or what needs a look —
then the few numbers behind it, each taken from a result above. Name the
account or alpha each number belongs to, using the names the user knows.

- **Alpha health**: name every alpha that is not `ok`, with its status and how
  long it has been silent against its usual cadence. `critical` and `dead` come
  first. `ok` is within `signal_interval`; `slow` is past it but inside
  `stale_after` (seconds from the last signal, so it is also the deadline before
  the alpha starts alerting). `last_signalled` is an epoch-ms string of the
  signal's *data-bar* time, not when it was emitted, so an hourly alpha reads
  `slow` while its next input bar has not landed yet — give the `stale_after`
  deadline rather than calling it broken.
- **Empty results** mean no data came back for that window, which is not proof
  of inactivity: several Aegis tools answer an inaccessible id with an empty
  result instead of a denial.
- **A scope denial** is final for that id; report it rather than retrying.
- **Paper and live**: say which one each account is whenever both appear, so a
  paper gain is never read as real money.

End by offering the obvious next look — the worst alpha's alerts, a longer
window, or live against backtest — as a single sentence.

Done when every target the user chose is covered in the report, and the report
says the window and the time the data is as of.
