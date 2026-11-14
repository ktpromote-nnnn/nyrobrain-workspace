---
name: deploy
description: >
  Package a portfolio and its OMS into one archive and run it on Prime managed
  compute, paper or live. Use when the user says "/deploy", wants to go live,
  forward-test on Prime, or manage an existing deployment -- status, logs, stop,
  start, redeploy, archive. The last step of the Nyrobrain workflow.
metadata:
  kind: entry
  step: "4"
---

# Deploying

A deployment is **one archive and two processes**: the portfolio publishes
target weights, and the OMS polls them and trades. They run under a supervisor
that exits if either dies, so Prime restarts the pod rather than leaving half a
deployment running — an OMS whose publisher has died keeps polling, finds
nothing new, and looks exactly like a portfolio with nothing to say.

The machinery is `nyrobrain.prime`. Use it; do not reimplement any of it, and
above all do not reimplement the idempotency key.

## Before deploying

1. **A portfolio and an OMS must both exist.** `brain/portfolio/<...>/` from
   `/portfolio`, and `brain/execution/<...>/` from `/execution`. If either is
   missing, say which and stop.
2. **Run `/check-pipeline` on the portfolio directory.** A violation here is
   cheap; the same violation after deploying is a blank dashboard or a bundle
   missing an alpha.
3. **Confirm the `oms_id`** in the OMS's `config.json` is the one intended.
   A wrong one publishes cleanly, merges cleanly, and is invisible.

## Ask two questions. Never assume either.

**Paper or live.** This decides whether real money moves. Ask in plain language
— not "which environment?" but whether this should trade real capital. If live:

- Say plainly that it trades real money, and wait for an affirmative answer.
- Tell them to use a **trade-only** exchange key with no withdrawal permission,
  and to whitelist Prime's egress IPs on it.
- If Prime answers with the compute-terms gate, give them the URL and stop.
  **Never accept the terms for them.** The API would let you; the waiver is only
  worth something if the person liable read it.

**Which tier.** This decides whether they are charged.

- `shared` is covered by a grant on the **first** instance only. A *second*
  shared deployment is billed at $10/mo. Say so before deploying, not after.
- **Do not promise `shared` will hold this.** It reserves 50m CPU and 512 MiB
  and bursts to 2 GiB, and burstable tenants are evicted first under node
  pressure. The OMS's import floor alone is ~152 MiB before a node, a cache or a
  quote exists, and the portfolio adds polars, pandas, numpy and pyarrow. Nobody
  has yet run two processes there. If the user picks `shared`, tell them it is
  untested at this shape and that `starter` is the safe choice.
- Paid tiers: `starter`, `pro`, `performance`, `dedicated`.

## What the bundle carries, and what it misses

`collect_files` ships every file directly under the portfolio directory, the
alphas it finds by scraping quoted `brain/strategy/...` literals, and
`pyproject.toml`, `uv.lock`. Nothing else, and it does not read
`.gitignore` — so a gitignored `.env` beside `config.json` **does** travel with
the deployment, which is how a deployment gets its credentials.

**A module imported from elsewhere in the workspace will not be there.** A
portfolio importing `oms/s3_store.py`, or any helper outside its own directory
that is not an alpha, is bundled only if you say so. List it in
`.prime/include` at the workspace root, one workspace-relative path per line,
`#` for comments:

```
# portfolio.py imports this
oms/s3_store.py
```

This is the designed seam for it. `_BASE_FILES` deliberately holds only the
files every workspace has; a workspace-specific import belongs here instead.

**Check before deploying, not after.** A missing import fails at startup on the
pod, after the deployment has been created and billed — so read the portfolio's
imports, and add anything outside its directory that is not an alpha.

## Deploying

Build the bundle with the OMS included, so the entrypoint starts both
processes, and deploy through `nyrobrain.prime.compute.deploy`. "Included" means
passing `oms_rel` — the workspace-relative path of the OMS's `oms.py` — to
`build_bundle`; without it the bundle starts the publisher alone.

The two processes are `python -m nyrobrain.portfolio` and the user's `oms.py`.
Only the second places orders. There is no `--role`: the publisher *cannot*
place an order, which is what stops a deployment from running two order placers
that cannot see each other's fills.

A `checkoutUrl` in the result means billing needs activating: give the user the
link and tell them the deployment starts by itself once checkout completes.
There is no second command.

**If a deploy fails, re-run it.** The stored `Idempotency-Key` is replayed, so a
deploy whose response was lost cannot be billed twice. **Never delete
`.prime_idempotency_key` to tidy up** — that is precisely what double-charges,
because the failed attempt may already have reserved the deployment.

## Credentials the deployment needs at run time

Prime gives the pod almost no environment. Anything the portfolio or the OMS
needs has to travel in the bundle, and it does not travel by itself.

Two kinds, and they are not interchangeable:

- **Exchange and Prime keys** — the `.env` beside `config.json`, read by
  `load_credentials` at a path `config.json` names. Covered by `/execution`.
- **Everything else the process environment must hold** — `AWS_*` for a
  portfolio that reads S3, `UV_INDEX_*` so a private index resolves. These
  reach the bundle through `extra_env`:

```python
from nyrobrain.prime import compute

extra = compute.env_from_environ(
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION",
    "UV_INDEX_BALAENAQUANT_USERNAME", "UV_INDEX_BALAENAQUANT_PASSWORD",
)
compute.redeploy(client=c, workspace=ws, portfolio_dir=d, slot=s, extra_env=extra)
```

They are written to a `.env` at the **bundle root** and baked into the
entrypoint. Both, because they are needed at two different moments: Prime
resolves dependencies with `uv` and *then* execs the entrypoint, so anything
`uv sync` needs — the private index above all — must be on disk before any of
our Python runs. Baking alone is always too late for that one.

If those variables live in a file beside the portfolio rather than in the
deploying shell — which is usually the right place for them — read that instead,
and the portfolio's own values win over whoever happens to be deploying:

```python
extra = compute.env_from_file(portfolio_dir / ".env")
```

**Work out which variables are needed by reading the code**, not by forwarding
everything. Grep the portfolio and its imports for `os.environ` and
`boto3`/`client(`, and check whether `pyproject.toml` names a private index. A
deploy that swept up the whole shell would bake values nobody chose into an
artifact nobody re-reads.

**Getting this wrong fails on the pod, not at build.** A missing `AWS_*` is a
botocore `InvalidAccessKeyId` in a crash loop; a missing `UV_INDEX_*` is a
`uv sync` that cannot reach the index. Both after the deployment is created and
billed.

## What runs in the pod: you compose it

A deployment is **a list of files and a list of processes**. That is also all
Prime's API takes — an archive and an entrypoint — so the library takes the same
two things and nothing else knows what a portfolio is.

```python
from pathlib import Path
from nyrobrain.prime import bundle, compute, workspace

files = [
    *workspace.portfolio_files(ws, portfolio_dir),
    *workspace.oms_files(ws, oms_dir),
]
processes = [                                        # OMS only: omit the publisher
    workspace.oms(oms_rel, mode="paper", portfolio_id=portfolio_id),
]
workspace.refuse_conflicting(processes)

archive = bundle.pack(
    workspace=ws, files=files, processes=processes,
    env=compute.env_from_file(oms_dir / ".env"),
    out_path=Path(tmp) / "bundle.tar.zst",
)
compute.redeploy(client=c, archive=archive, state_dir=portfolio_dir, slot=slot)
```

The three shapes are three lists, not three flags:

- publisher only — `[workspace.publisher(portfolio_rel, config_rel, log=...)]`
- OMS only — `[workspace.oms(oms_rel, mode=..., portfolio_id=...)]` (`portfolio_id` required for `paper`)
- both — the two together, and the supervisor exits if either dies

`mode` has **no default**: `live` places real orders, so a paper deployment
must say `mode="paper"` out loud.

**A paper deployment needs `nyrobrain>=0.11.0`, and this is where it bites
hardest.** Below 0.6.0 the simulated venue's book lives only in the process, so
every redeploy, every pod eviction and every crash-loop restart reads a position
of zero and re-enters the whole target — compounding silently, while the metrics
show a book that keeps growing for no reason anyone can see. A deployment
restarts far more often than a laptop run does, which is why the floor matters
more here than in `/execution`. Below 0.6.1 `nyrobrain.prime` does not export
`set_status`, so a deployed OMS cannot mark its account Running on start or
Stopped on the way out — it reads Stopped while healthy, or Running forever after
the pod is gone. Below 0.7.0 every trade reaches Aegis with a positive quantity,
so the trade feed shows each sell as a buy — a short opened as `+0.93` beside a
position of `-0.93` — and a redeploy re-publishes the restored trades the same
way. Below 0.7.1 the portfolio publisher never writes its target to Prime, so
the OMS polls `GET /api/portfolio-target/<id>` and gets `never_published`
forever while every log line on both sides looks healthy. Below 0.9.0 a live
Bybit deployment's orders carry nautilus's broker code instead of Nyrobrain's.
Below 0.10.0 `register_account` does not take `mode` or `environment`, so the
deployed account never records whether it is paper or live, or which exchange
environment its keys are for. Below 0.11.0 ids are namespaced with `USER_ID`,
which can hold the API key, so the key is published in every portfolio, OMS and
alpha id; the portfolio's name is the namespaced id rather than the bare one;
and a name another portfolio already holds is not caught.

**From 0.6.0 a paper OMS must be given `portfolio_id`:**

```python
processes = [workspace.oms(oms_rel, mode="paper", portfolio_id=portfolio_id)]
```

The journal lives on `/cache/paper_journal`, which outlives the pod, and is kept
one file per portfolio. `bundle` bakes `NYROBRAIN_PAPER_JOURNAL` into every
generated entrypoint — it cannot know which deployments are paper — so a paper
OMS always finds a journal directory configured, and one keyed on nothing would
collide with a sibling portfolio's book the moment two of them shared it. The
driver refuses to start rather than guess a name, so **a paper deployment
without `portfolio_id` does not boot.** `live` does not need it: a real venue
reconciles its own positions and writes no journal.

**Ids on Prime are `{user_id}_{bare id}`; the portfolio's name is the bare id.**
`config.json` holds bare ids and the publisher and OMS namespace them with the
user id Prime reports for your key — never the key itself. So do not put
`USER_ID` or your API key in `extra_env`: a baked `USER_ID` that starts with
`nyr_` is refused at startup, and the key already reaches the pod through the
`.env` beside `config.json`. Two things stop a deploy rather than degrade it: a
portfolio name another of your portfolios already holds (Prime compares
case-insensitively, so `Delta1` and `DELTA1` clash), which the publisher reports
as `PortfolioNameTaken`; and an `oms_id` someone else holds. Rename the bare id
in `config.json` and redeploy.

The user id is resolved at startup with `GET /api/keys/verify` (header
`x-api-key`), so a publisher or OMS that dies at startup with `Prime refused
with 401` or `Prime did not accept the API key` has a bad `prime_api_key` /
`PRIME_API_KEY`, not a namespacing problem. Check the key directly:

```bash
curl -s -H "x-api-key: $PRIME_API_KEY" "$PRIME_API_URL/api/keys/verify"
```

`{"valid": true, "userId": "..."}` means the key is good, and that `userId` is
the prefix your ids get. Anything else means rotate or re-enter the key. A
transient 5xx there is retried by restarting, not by changing anything.

**Always call `workspace.refuse_conflicting(processes)` before packing.** Two
publishers is not wasted compute: each carries its own `(epoch, sequence)`
ordering key and a consumer orders targets by that pair, so a *fresh* target
from the older publisher loses to a *stale* one from the newer — the OMS trades
the wrong weights and nothing in any log says so. Two order placers is the
mirror image, each blind to the other's fills.

A shape nobody anticipated — a second sidecar, a backtest job — is another entry
in the list. It needs no new library version.

## One portfolio directory can host several deployments

A role-split portfolio has at least two: a publisher pod and one or more OMS
pods. Two OMSes on different exchanges is the same again. Each is addressed by a
**slot**:

```python
from nyrobrain.prime.compute import Slot

Slot()                                          # the single combined deployment
Slot(role="portfolio")                          # the publisher
Slot(role="oms")                                # the OMS
Slot(config_name="config_bybit.json", role="oms")   # one OMS of several
```

Every command takes `slot=`. **Omitting it addresses the default slot, which is
a different deployment** — very often an old combined one that has been stopped.
A `redeploy` aimed at the wrong slot ships new code to something nobody is
running while the live pod keeps serving the old revision, and nothing reports
an error.

**Look before you act.** The slots that exist are on disk, one file each:

```bash
ls -a brain/portfolio/<...>/.prime_deployment*
```

`.prime_deployment` is the default slot; `.prime_deployment.portfolio` and
`.prime_deployment.oms` are roles; `.prime_deployment.config_bybit.oms` is a
config and a role. Read that list and confirm which one the user means before
touching anything — especially with more than one.

## Managing it afterwards

- `status` — desired and actual state, plus recent events.
- `logs` — each line prefixed with the process that wrote it.
- `stop` / `start` — pause without ending billing, and resume. A `start` that
  raises `PaymentRequired` carries the checkout URL.
- **`redeploy` for code changes.** It bumps the revision in place, keeps the
  subscription item, and costs nothing. Always prefer it to archive-then-deploy.
  Pass the `slot=` of the deployment you mean; the default is its own slot.
- `archive` — permanent, and **it voids the payment**. Prime removes the
  subscription item immediately, so the rest of the paid period is lost, not
  refunded. Warn the user in those words and confirm before calling it. If they
  want a pause, they want `stop`.

## Checking how it is doing

`status` and `logs` say whether the pod is running. Whether the *strategy* is
doing well — PnL, drawdown, positions, alpha health — is `/monitor`. After a
successful deploy, name it as the next step.

## Two things nobody has verified

Say these if the user is deploying live for the first time.

- **Prime-side `NYROBRAIN_WEB_URL` and `COMPUTE_BILLING_MODE=stripe` must be
  live in the target environment.** If they are not, deploys land `exempt` and
  **silently take no payment** — which looks like success.
- **The CLI path has never run against real Stripe.** The browser path has a
  smoke test; this one does not. A first live deploy is also a first test of the
  billing path.
