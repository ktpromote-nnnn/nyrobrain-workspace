"""Retired. The publisher is `python -m nyrobrain.portfolio`.

This file used to generate signals *and*, by default, place orders: it took
`--role {all,portfolio,oms}` defaulting to `all`, and the deployment shim never
passed the flag. A two-process deployment therefore ran an adrs OMS beside a
`nyrobrain.execution` OMS, on one account, each blind to the other's fills.

It is a stub rather than a deletion on purpose. Workspaces are seeded by copying
this directory over, and a copy never deletes — so deleting it here would leave
every existing workspace holding a file that still starts an order placer. This
replaces it with something that cannot.

    python -m nyrobrain.portfolio <portfolio.py> -f <config.json>

`oms/` is otherwise yours; nothing else in it is touched.
"""

from __future__ import annotations

import sys

MESSAGE = """\
oms/run.py has been retired.

The publisher now lives in the library, so it is versioned and updated with it
instead of rotting in a workspace copy:

    uv run python -m nyrobrain.portfolio <portfolio.py> -f <config.json>

It generates signals and publishes portfolio targets. It does not place orders
-- a `nyrobrain.execution` OMS does that, from `brain/execution/<...>/oms.py`.
There is no `--role` any more, because one process doing both is what this
change exists to make impossible.

Needs `nyrobrain[portfolio]`; see /deploy.
"""


def main() -> int:
    print(MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
