---
name: execution
description: >
  Write the OMS that trades a portfolio's signals, into brain/execution/. Use
  when the user says "/execution", wants an OMS, an executor, or to actually
  trade a portfolio they have built. The third step of the Nyrobrain workflow,
  after /portfolio and before /deploy.
metadata:
  kind: entry
  step: "3"
---

# Writing the OMS

A portfolio produces target weights. An **OMS** turns them into orders and never
trades past the target. This command writes one the user owns, into
`brain/execution/<YYYY-MM-DD>_<oms_id>/`, mirroring the portfolio convention.

It is built on `nyrobrain.execution`. The library does the sizing, the delta and
the guards; the user supplies the placement.

## Three files, three lifecycles

This is the part to get right, and to tell the user plainly.

| File | Whose | On a re-run |
|---|---|---|
| `hooks.py` | **theirs** | never touched |
| `config.json` | theirs, but data | never touched |
| `.env` | **theirs**, secret | scaffolded empty if missing, never read |
| `oms.py` | generated | **regenerated** |

**`hooks.py` is the only file that is genuinely theirs.** It holds a `Placement`:
one method, `plan(ctx) -> Sequence[Action]`, deciding *how* a delta is worked
into the book — how many orders, at what price, amend or cancel, how long before
crossing. It never decides *how much*; the library clamps that, and the seam is
shaped so a hook cannot reach around it.

It is also mode-agnostic. The same `hooks.py` runs under backtest, paper and
live, which is what makes a backtest mean anything: a difference in behaviour
between two modes is the venue, not the harness.

**`oms.py` is regenerated, and must say so in its own header.** That is how a
user picks up library updates instead of accumulating version archaeology in a
file nothing refreshes. Tell them: edits there do not survive. Anything they
want to keep belongs in `hooks.py` or `config.json`.

## Ask for the `oms_id`. Never derive it.

Default to the portfolio's id, which is today's convention, but **ask**.

Deriving it would silently reuse the id of whatever OMS is already publishing
for that portfolio — and `oms_id` decides which rows merge together in Aegis,
which account's charts light up, and who may read them. A wrong one fails at
none of those: the metrics publish cleanly, merge cleanly, and are invisible.

Reusing an id is a legitimate choice — it gives one unbroken equity curve across
a cutover. Taking a fresh one gives a clean before-and-after comparison. Both are
fine; neither should happen by accident.

## Write a test beside `hooks.py`

`nyrobrain.execution.testing.PlacementHarness` drives a placement through fills,
book moves and target changes with **no venue, no network and no nautilus**. So
the one file the user owns can be iterated on in seconds.

Write that test as part of scaffolding. A placement with no test is a strategy
nobody can change safely, and this is the cheapest feedback loop in the whole
workspace.

## Credentials go in `.env`, beside `config.json`

Scaffold a `.env` in the OMS directory and point `config.json` at it:

```json
"credentials": ".env",
"prime_credentials": ".env"
```

One file holds both. The field names are namespaced rather than positional —
`BYBIT_API_KEY`/`BYBIT_API_SECRET` for the venue, and `PRIME_API_KEY` for Prime.
Call `credential_fields(venue)` for the venue pair rather than spelling it out;
a different venue gives different names.

Write it with the names present and every value blank, so the user edits rather
than guesses:

```
BYBIT_API_KEY=
BYBIT_API_SECRET=
PRIME_API_KEY=
```

**Add `.env` to the OMS directory's `.gitignore` in the same step.** The two
belong together: the file only stays out of a commit because that line is there.

**A relative path in `config.json` resolves against the OMS directory, not the
process's working directory.** Generated `oms.py` must resolve it that way,
because the OMS is run both from the workspace root and, on Prime, from the
bundle root:

```python
_HERE = Path(__file__).resolve().parent


def _credentials_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else _HERE / path
```

This is also what makes `/deploy` work at all. A bundle preserves the
workspace's relative layout, so a `.env` beside `config.json` travels with it
and resolves on the pod. An absolute `~/.config/nyrobrain/...` path does not
exist there, and a live deployment pointed at one fails when it loads
credentials — after the deployment has been created and billed.

**Do not tell the user the library keeps credentials out of this repository.**
`load_credentials` refuses a path inside the working tree that *the library
itself* lives in, which protects a `nyrobrain` checkout and nothing else. Here
`nyrobrain` is an installed wheel, so a `.env` in the workspace is accepted.
The `.gitignore` line is the whole of the protection. Any `_note` written into
`config.json` must say that and not the stronger thing.

## The OMS owns its account's run state

`register_account` creates an account; it does not start one. The driver must
also set it `active` on start and `stopped` on exit, using the `account_id`
registration returned — `nyrobrain.prime.set_status`.

**`account_id` is not optional.** Status is per account, and a portfolio id
alone is a 409 the moment a portfolio has more than one — which a role-split
portfolio always does.

Without the exit call, an account reads Running forever after the pod stops.
Without the start call it reads Stopped for the whole life of a healthy run,
while its metrics stream — alive in charts, dead in status, because those are
two different paths. The exit call belongs in a `finally` and must never raise:
losing the exit code on a pod turns a clean stop into a restart loop.

## `log_level` defaults to `INFO`

It is nautilus's stdout level, and on a deployment it is the audit trail —
orders submitted, filled and cancelled, and each target applied. Write `INFO`
into `config.json`. `WARNING` leaves no way to tell a working pod from an idle
one, and disagrees with the publisher, which logs at INFO.

## Ids are namespaced per user when deployed

The publisher writes its targets under `{user_id}_{portfolio_id}`, because two
users' portfolios share NATS subjects and Prime's `account_oms_id_unique` is
global. `user_id` is the id Prime reports for your API key
(`GET /api/keys/verify`), **never the key itself** — an id built from the key
would publish the credential to Prime, Aegis, NATS subjects and logs. The
generated driver applies the same rule through
`nyrobrain.portfolio.naming.namespace` (imported rather than reimplemented,
because the two sides have to agree forever), which refuses a `nyr_` value.

The driver resolves `user_id` through `nyrobrain.prime.resolve_user_id`
whenever a Prime key is available. `USER_ID` is honoured only as an explicit
override, and the driver refuses it if it holds an API key — unset it. A local
run with no Prime key and no override is unchanged.

Prime's portfolio **name** is the bare id (`DELTA1`), while its id stays
namespaced. Names are unique per owner and case-insensitive, so two portfolios
whose bare ids differ only in case clash and the publisher stops with
`PortfolioNameTaken` — pick distinct names.

`config.json` therefore holds the **bare** ids. Do not pre-namespace them there;
it would be applied twice on a pod and once nowhere else.

An OMS that skips this asks Prime for a portfolio target that does not exist and
refuses at startup with a 404 it cannot retry its way out of.

## What it refuses to guess

- **Credential values.** Scaffold `.env` with empty values and stop there.
  Never fill one in, never echo one, never read one back. `ApiCredentials` masks
  itself in `repr` so a traceback cannot leak a key; printing one here would
  undo that.
- **Real money.** This command writes a driver. It does not pick a venue
  environment, and mainnet needs an explicit flag that nothing here supplies.
- **A portfolio that does not exist.** If `brain/portfolio/` is empty, stop and
  point at `/portfolio`.

## Then

Try it before deploying it:

```bash
uv run python brain/execution/<...>/oms.py --mode paper --minutes 10
```

Paper needs no credentials — real Bybit quotes, simulated fills. Watch the
report's guard counters; `overshoot 0` and `invariant held` are the lines that
matter.

**Check `nyrobrain>=0.11.0` before running paper at all.** Below 0.6.0 a paper
run keeps its book only in memory, so every restart reads a position of zero,
computes a delta equal to the whole target, and buys a book it is already
holding — silently, and compounding with each restart. On an older version the
run is not merely un-persisted; it is wrong the moment anything restarts it.
Below 0.6.1 `nyrobrain.prime` does not export `set_status`, so the driver
written above cannot mark its account Running at all. Below 0.7.0 every trade is
published with a positive quantity, so the trade feed cannot tell a sell from a
buy. Below 0.7.1 the portfolio publisher never writes its target to Prime, so an
OMS that polls for it reads `never_published` indefinitely. Below 0.9.0 Bybit
orders carry nautilus's broker code instead of Nyrobrain's. Below 0.10.0
`register_account` does not take `mode` or `environment`, so the account never
records whether it is paper or live, or which exchange environment its keys are
for. Below 0.11.0 ids are namespaced with `USER_ID`, which can hold the API key,
so the key is published in every portfolio, OMS and alpha id, and a portfolio
name another of yours already holds is not caught.

```bash
uv run python -c "from importlib.metadata import version; print(version('nyrobrain'))"
```

The package exposes no `__version__` attribute, so read it from the installed
distribution's metadata rather than the module. If it reads lower, upgrade
before continuing:

```bash
uv add "nyrobrain[execution,portfolio,prime,aegis]>=0.11.0"
```

When it behaves, the next step is **`/deploy`**.
