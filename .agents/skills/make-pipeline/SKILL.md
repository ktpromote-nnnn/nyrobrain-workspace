---
name: make-pipeline
description: >
  Author a new alpha or portfolio pipeline as a reusable skill, when the shipped
  defaults do not fit the user's methodology. Use when the user says
  "/make-pipeline", wants their own research process, a different split or
  holdout, or their own definition of a pass. Not for writing a single strategy
  -- that is /strategy.
metadata:
  kind: entry
---

# Authoring a pipeline

A **pipeline** is a methodology: how a strategy is split, what is measured, what
counts as a pass, and what gets written down. The shipped ones are defaults, not
rules. This command turns the user's own methodology into a skill that
`/strategy` or `/portfolio` will offer alongside them.

Invoked as `/make-pipeline alpha` or `/make-pipeline portfolio`. If the kind is
missing, ask — it decides which command will offer it and cannot be guessed from
a description.

## Before anything: is this the right command?

Authoring a good pipeline is a different skill from doing good research, and the
shipped defaults are considered. If the user wants **one strategy done
differently**, that is `/strategy` with a conversation, not a new pipeline.

Reach for this when the difference is **methodological and repeatable**: they
always use a different holdout, they measure something the defaults do not, they
have a house format for `summary.md`. A pipeline is worth authoring when it will
be used more than once.

Say this plainly if it looks like a one-off. It is not gatekeeping; a pipeline
built for a single strategy is a worse strategy and a worse pipeline.

## 1. Interview

Do not present a template. A blank skeleton produces something worse than the
default it replaces, because the default at least had reasons behind it.

Ask, one at a time, and let the answers become the pipeline:

- **What is wrong with the default?** The honest starting point. If they cannot
  name it, the pipeline has no purpose and the conversation should go back to
  `/strategy`.
- **How is the data split?** Train and test, walk-forward, purged k-fold, a
  fixed holdout by date. Why that, for this kind of alpha.
- **What is measured, and what is a pass?** A pipeline that reports numbers
  without a threshold leaves the judgement to whoever reads it, which is how two
  strategies stop being comparable.
- **What must be written down?** The shape of `summary.md` beyond the required
  frontmatter — what a reader needs in order to trust the result.
- **What should it refuse?** The failure the user has seen before and does not
  want to repeat. This is usually the most valuable answer in the interview.

## 2. Write the skill

Into `.agents/skills/pipeline-<kind>-<name>/SKILL.md`, beside the shipped ones —
a user's pipeline is a peer, not a second-class thing in another folder.

Three naming rules, all load-bearing:

- **The name must begin `pipeline-alpha-` or `pipeline-portfolio-`.** That
  prefix is how `/strategy` and `/portfolio` find it. A perfectly written
  pipeline under any other name is invisible: the skill listing exposes only
  `name`, `description`, `location` and `content`, so nothing else can be
  matched on.
- **Lowercase, hyphen-separated, at most 64 characters, identical to the folder
  name.** So it cannot be taken verbatim from what the user typed — propose one
  and confirm it.
- **A `description` is mandatory.** A skill without one is filtered out and
  never surfaced. It is also the only other field the listing shows, so it is
  what the user reads when choosing between this pipeline and the default. Say
  what the methodology *is*, not that it exists.

## 3. Inherit the contract — by reference, never by copy

Some of what a pipeline prescribes is read by other code: the dashboard, the
report panel, the knowledge-base indexer, the deployment bundler. A pipeline is
free to change methodology and not free to change those.

Every pipeline this command writes must carry a short section pointing at
`ops/pipeline/CONTRACT.md` and at `/check-pipeline`. **Point; do not restate.**
A copied contract is a contract that rots the first time the real one moves,
which is exactly the failure that made `CONTRACT.md` generated rather than
written.

Read `CONTRACT.md` yourself before writing, and make sure the methodology you
were just told is actually compatible with it. If the user wants something the
contract forbids — a different `summary.md` location, a report in another format
— say so now, while it is a conversation, rather than letting them discover it
from a blank dashboard.

## 4. Verify what you can, and be honest about what you cannot

Check the file:

```bash
python ops/pipeline/check.py --skill .agents/skills/pipeline-<kind>-<name>
```

It verifies the frontmatter parses, the `name` matches the folder, the prefix is
right and the description is non-empty — the four mistakes that make a
well-written pipeline invisible. Each is silent, because an unusable skill and
an absent one look identical.

**Then tell the user to restart opencode.** Skills are loaded once at startup
and are not hot-reloaded, so the pipeline they just authored will not appear in
`/strategy` until they quit and reopen. This is the last thing the command says,
because a user who does not hear it concludes the command failed.

You cannot confirm discovery yourself for the same reason. Do not claim the
pipeline is available; say it will be after a restart.

## 5. The first real test

A pipeline is only proved by what it produces. Tell the user that once they have
run `/strategy` with it, `/check-pipeline` on that first output directory is the
thing that says whether the pipeline they wrote actually satisfies the contract.
