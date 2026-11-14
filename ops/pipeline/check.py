"""Does this strategy or portfolio satisfy the pipeline contract?

The contract is `contract.json`; this file only interprets it. Rules live there
so that the human-readable `CONTRACT.md` can be generated from the same source
and cannot drift from what is enforced — which is the failure being fixed. The
shipped pipelines asserted in bold that a `status` of `success`, `fail` or
`review` would be rejected, while the dashboard accepted all three.

Why a checker rather than prose: almost every violation here is **silent**. A
strategy missing its date prefix is not listed. A missing frontmatter key drops
it from the index. A malformed report envelope is reported as "No report found".
An alpha path built with an f-string ships a deployment without that alpha. None
of them says anything, and the cause is never near the symptom.

    python ops/pipeline/check.py brain/strategy/2026-09-21_my-alpha
    python ops/pipeline/check.py brain/portfolio/2026-09-21_my-portfolio
    python ops/pipeline/check.py --emit-doc > ops/pipeline/CONTRACT.md

Exits non-zero when a rule is violated, so `/deploy` can gate on it.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent
CONTRACT = HERE / "contract.json"


@dataclass(frozen=True)
class Violation:
    rule: str
    breaks: str
    consumer: str
    silent: bool
    detail: str

    def render(self) -> str:
        mark = "  (silent — nothing will tell you)" if self.silent else ""
        return (
            f"✗ {self.rule}{mark}\n"
            f"    {self.detail}\n"
            f"    breaks: {self.breaks}\n"
            f"    read by: {self.consumer}"
        )


def frontmatter(path: Path) -> dict[str, str]:
    """The YAML-ish header, parsed without a YAML dependency.

    Deliberately shallow: the keys the contract cares about are all flat
    strings, and a full parser would be a dependency this workspace does not
    otherwise need.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    _, _, rest = text.partition("---\n")
    body, _, _ = rest.partition("\n---")
    found: dict[str, str] = {}
    for line in body.splitlines():
        key, sep, value = line.partition(":")
        if sep and not key.startswith((" ", "\t", "#")):
            found[key.strip()] = value.strip().strip("\"'")
    return found


def _async_def(tree: ast.Module, name: str) -> ast.AsyncFunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    return None


def _any_def(tree: ast.Module, name: str) -> ast.stmt | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return node
    return None


def check(directory: Path, kind: str, rules: list[dict]) -> list[Violation]:
    found: list[Violation] = []

    def fail(rule: dict, detail: str) -> None:
        found.append(
            Violation(rule["id"], rule["breaks"], rule["consumer"], rule.get("silent", False), detail)
        )

    for rule in rules:
        applies = rule["applies_to"]
        if applies not in (kind, "both"):
            continue
        kind_of_check = rule["check"]

        if kind_of_check == "dir_name_matches":
            if not re.search(rule["pattern"], directory.name):
                fail(rule, f"directory {directory.name!r} does not match {rule['pattern']}")

        elif kind_of_check == "file_exists":
            if not (directory / rule["path"]).is_file():
                fail(rule, f"{rule['path']} is missing")

        elif kind_of_check == "frontmatter_keys":
            target = directory / rule["path"]
            if not target.is_file():
                continue  # file_exists already reported it
            keys = frontmatter(target)
            missing = [k for k in rule["required"] if k not in keys]
            if missing:
                fail(rule, f"{rule['path']} frontmatter is missing: {', '.join(missing)}")

        elif kind_of_check == "frontmatter_enum":
            target = directory / rule["path"]
            if not target.is_file():
                continue
            value = frontmatter(target).get(rule["key"])
            if value is not None and value not in rule["allowed"]:
                fail(rule, f"{rule['key']} is {value!r}; accepted: {', '.join(rule['canonical'])}")

        elif kind_of_check == "async_def_exists":
            target = directory / rule["path"]
            if not target.is_file():
                fail(rule, f"{rule['path']} is missing")
                continue
            try:
                tree = ast.parse(target.read_text(encoding="utf-8"))
            except SyntaxError as err:
                fail(rule, f"{rule['path']} does not parse: {err}")
                continue
            fn = _async_def(tree, rule["function"])
            if fn is None and _reexported(tree, rule["function"]):
                # A re-export resolves at import, which is how the consumer
                # reaches it: `importlib.import_module(...).setup_portfolio`.
                # Follow it to the sibling module rather than reporting a
                # violation the runtime does not have. Demanding a `def` here
                # would push people to add a wrapper, and a wrapper breaks the
                # live-hint signature gating this same rule then checks.
                fn, tree = _follow_reexport(
                    directory, tree, rule["function"]
                ) or (None, tree)
            if fn is None:
                other = _any_def(tree, rule["function"])
                if other is not None:
                    fail(rule, f"{rule['function']} is defined but not `async def`")
                else:
                    fail(rule, f"{rule['path']} does not define {rule['function']}")
                continue
            names = {a.arg for a in fn.args.args} | {a.arg for a in fn.args.kwonlyargs}
            absent = [p for p in rule["params"] if p not in names]
            if absent:
                fail(rule, f"{rule['function']} does not accept: {', '.join(absent)}")

        elif kind_of_check == "quoted_paths_present":
            # Every top-level .py in the directory, because that is exactly
            # what the bundler scrapes (`portfolio_dir.glob("*.py")`). Checking
            # only `portfolio.py` reported a violation for a portfolio whose
            # alpha literals sit in a sibling module and which bundles
            # correctly -- a checker narrower than the consumer it models,
            # which is worse than no checker, because it teaches people to
            # ignore it.
            targets = sorted(directory.glob("*.py")) if directory.is_dir() else []
            if not targets:
                continue
            literals = []
            trees = []
            for target in targets:
                try:
                    one = ast.parse(target.read_text(encoding="utf-8"))
                except SyntaxError:
                    continue
                trees.append(one)
                literals.extend(
                    n.value
                    for n in ast.walk(one)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                )
            if not trees:
                continue
            tree = trees[0]
            # An f-string is the nastier case: the bundler's regex runs over the
            # *source text*, so `f"brain/strategy/{name}/alpha.py"` matches and
            # yields a path containing a literal `{name}`. It looks found and
            # cannot exist, which is worse than matching nothing.
            composed = [
                n
                for one in trees
                for n in ast.walk(one)
                if isinstance(n, ast.JoinedStr)
                and any(
                    isinstance(v, ast.Constant)
                    and isinstance(v.value, str)
                    and rule["pattern"] in v.value
                    for v in n.values
                )
            ]
            if composed:
                fail(
                    rule,
                    f"a .py in {directory.name} builds a {rule['pattern']}... path "
                    "with an f-string. "
                    "The bundler scrapes source text, so it will package a path "
                    "containing a literal '{...}' that cannot exist",
                )
            elif not any(rule["pattern"] in lit for lit in literals):
                fail(
                    rule,
                    f"no .py directly in {directory.name} contains a quoted "
                    f"{rule['pattern']}... literal, "
                    "so deployment will package no alpha files",
                )

    return found


def _reexported(tree: ast.Module, name: str) -> bool:
    """Whether `name` arrives by `from ... import name` rather than a def."""
    return any(
        isinstance(node, ast.ImportFrom)
        and any(alias.asname == name or alias.name == name for alias in node.names)
        for node in ast.walk(tree)
    )


def _follow_reexport(
    directory: Path, tree: ast.Module, name: str
) -> tuple[ast.AsyncFunctionDef, ast.Module] | None:
    """Resolve `from <sibling> import name` to the def in that sibling.

    Only siblings directly in the same directory are followed — the same scope
    the bundler uses, and enough for the re-export shape this exists to accept
    without turning the checker into an import resolver.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if not any(a.asname == name or a.name == name for a in node.names):
            continue
        original = next(
            (a.name for a in node.names if a.asname == name or a.name == name), name
        )
        sibling = directory / f"{node.module.split('.')[-1]}.py"
        if not sibling.is_file():
            continue
        try:
            subtree = ast.parse(sibling.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        found = _async_def(subtree, original)
        if found is not None:
            return found, subtree
    return None


def check_skill(directory: Path) -> list[str]:
    """Validate a pipeline skill file, as far as a file can be validated.

    Not discovery: skills load once at opencode startup, so nothing here can
    confirm the skill is actually available. What it can catch is the set of
    mistakes that make a well-written pipeline invisible — and every one of
    them is silent, because an unusable skill and an absent one look the same.
    """
    problems: list[str] = []
    skill = directory / "SKILL.md"
    if not skill.is_file():
        return [f"{skill} does not exist"]

    keys = frontmatter(skill)
    name = keys.get("name", "")

    if not name:
        problems.append("frontmatter has no `name`")
    elif name != directory.name:
        problems.append(f"name {name!r} does not match folder {directory.name!r}")

    if not name.startswith(("pipeline-alpha-", "pipeline-portfolio-")):
        problems.append(
            f"name {name!r} does not begin `pipeline-alpha-` or `pipeline-portfolio-`, "
            "so /strategy and /portfolio will never list it"
        )
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name or ""):
        problems.append(
            f"name {name!r} must be lowercase, hyphen-separated and at most 64 characters"
        )
    if not keys.get("description"):
        problems.append(
            "frontmatter has no `description` — a skill without one is filtered out "
            "and never surfaced to the model"
        )
    return problems


def emit_doc(contract: dict) -> str:
    out = [
        "# The pipeline contract",
        "",
        "**Generated from `ops/pipeline/contract.json` — do not edit.**",
        "Run `python ops/pipeline/check.py --emit-doc > ops/pipeline/CONTRACT.md`.",
        "",
        "These are the things other code reads. Everything else in a pipeline is",
        "methodology, and yours to change.",
        "",
        "Each rule names its consumer, because that is what makes it a contract",
        "rather than a preference.",
        "",
    ]
    for scope, title in (("strategy", "Strategies"), ("portfolio", "Portfolios"), ("both", "Both")):
        applicable = [r for r in contract["rules"] if r["applies_to"] == scope]
        if not applicable:
            continue
        out += [f"## {title}", ""]
        for rule in applicable:
            out += [
                f"### `{rule['id']}`",
                "",
                f"- **Breaks:** {rule['breaks']}",
                f"- **Read by:** `{rule['consumer']}`",
                f"- **Fails silently:** {'yes' if rule.get('silent') else 'no'}",
            ]
            if rule.get("note"):
                out += [f"- **Note:** {rule['note']}"]
            out += [""]
    out += ["## Yours to change", ""]
    out += [f"- {line}" for line in contract["methodology"]["free"]]
    out += [""]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    contract = json.loads(CONTRACT.read_text())

    if "--emit-doc" in argv:
        print(emit_doc(contract))
        return 0

    if "--skill" in argv:
        target = Path(argv[argv.index("--skill") + 1])
        problems = check_skill(target)
        if not problems:
            print(f"✓ {target} is a well-formed pipeline skill")
            print("  It will not appear in /strategy until opencode is restarted.")
            return 0
        print(f"{len(problems)} problem(s) with {target}:\n")
        for problem in problems:
            print(f"✗ {problem}")
        return 1

    if not argv:
        print(__doc__)
        return 2

    directory = Path(argv[0])
    if not directory.is_dir():
        print(f"not a directory: {directory}")
        return 2

    parts = directory.resolve().parts
    kind = "portfolio" if "portfolio" in parts else "strategy"

    violations = check(directory, kind, contract["rules"])
    if not violations:
        print(f"✓ {directory} satisfies the {kind} contract")
        return 0

    print(f"{len(violations)} violation(s) in {directory} (checked as a {kind}):\n")
    for v in violations:
        print(v.render(), "\n")
    print("Everything not listed above is methodology and yours to change —")
    print("see the 'Yours to change' section of ops/pipeline/CONTRACT.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
