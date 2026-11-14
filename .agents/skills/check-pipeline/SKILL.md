---
name: check-pipeline
description: >
  Check whether a strategy or portfolio directory satisfies the pipeline
  contract -- the parts other code actually reads. Use when a strategy is
  missing from the dashboard, a report says "No report found", a deployment
  seems to be missing an alpha, or the user asks "/check-pipeline" or whether
  their work is set up correctly.
metadata:
  kind: entry
---

# Checking a pipeline's output

Run the checker and explain what it found.

```bash
python ops/pipeline/check.py <directory>
```

It exits non-zero on a violation, prints each one with the consumer it breaks,
and marks the ones that fail **silently**.

## Why this exists

Nearly every violation it catches is invisible. A strategy without a date prefix
is simply never listed. A missing frontmatter key drops it from the index. A
malformed report envelope is reported as "No report found", which reads like
nothing ran. An alpha path composed at runtime ships a deployment without that
alpha, and an f-string ships one pointing at a file that cannot exist.

None of these produce an error. The user sees an absence and has nowhere to
look. This command is where they look.

## When to reach for it unprompted

- A strategy or portfolio the user just made is not showing in the dashboard.
- A report panel says "No report found" on work the user believes finished.
- Before `/deploy`, if the portfolio has been edited by hand since it was made.
- After `/make-pipeline`, on the first directory that pipeline produced — a new
  pipeline's first output is the only real test of it.

## Reading the output

Say which consumer breaks, not just which rule failed. "The dashboard will not
list this, because `summary.md` has no `created_at`" is actionable; "invalid
frontmatter" is not.

**Be equally clear about what is not wrong.** The contract is small, and a great
deal of what a pipeline prescribes has no reader at all — file names inside the
directory, every chart filename, the four portfolio parquets, the frontmatter
keys `author` and `revision`. A user who thinks everything is load-bearing will
not change the one thing they should. `ops/pipeline/CONTRACT.md` has the full
split; its "Yours to change" section is the part people need told.

## If the contract itself looks wrong

`ops/pipeline/contract.json` is the source of truth and `CONTRACT.md` is
generated from it — never edit the markdown. Each rule names the file and line
that reads it, so a rule can be checked against reality rather than believed.
One already was: the shipped pipelines insist in bold that a `status` of
`success`, `fail` or `review` will be rejected, and the dashboard accepts all
three.
