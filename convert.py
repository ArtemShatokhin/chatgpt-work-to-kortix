#!/usr/bin/env python3
"""Convert a ChatGPT Work agent inventory into a Kortix project.

    python3 convert.py --inventory example-inventory.json --out ./my-project
    python3 convert.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HEAD = """# Generated from a ChatGPT Work inventory by chatgpt-work-to-kortix.
# `kortix validate` checks this manifest, the agent files, the connector slugs
# and the secrets. It does not check policy.policies: read those rules.
kortix_version: 2
default_agent: {default}
"""

AGENT = """  {name}:
    file: agents/{name}.md
    connectors: [{connectors}]
    secrets: [{secrets}]
    kortix_permissions: none
"""

DOC = """# {name}

{purpose}

## Scope

This agent may reach: {apps}. Its grants are the connector list in
`kortix.yaml`; a project entry with no permission line has no access.

## Actions that stop for a person

{approvals}

Everything that writes or destroys is sent to approval by
`policy.default_mode: risk`, even where no rule below matches.
"""


def slug(value: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in value.strip())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "agent"


def build(inventory: dict) -> tuple[str, dict[str, str], str]:
    rows = inventory.get("agents") or []
    if not rows:
        raise ValueError("inventory has no agents")
    notes: list[str] = []
    agents, docs, rules = [], {}, []
    connectors: list[str] = []
    secrets: set[str] = set()
    seen: list[str] = []

    for row in rows:
        name = slug(row.get("name", ""))
        if name in seen:
            notes.append(f"- duplicate agent `{name}`: only the first was written")
            continue
        seen.append(name)
        apps = [a for a in (row.get("apps") or []) if isinstance(a, str) and a.strip()]
        for app in apps:
            if app not in connectors:
                connectors.append(app)
        keys = sorted(f"{a.upper().replace('-', '_')}_API_KEY" for a in apps)
        secrets.update(keys)

        approvals = []
        for rule in row.get("approvals") or []:
            match = (rule.get("match") or "").strip()
            action = (rule.get("action") or "require_approval").strip()
            if not match:
                notes.append(f"- `{name}` has an approval row with no match pattern")
                continue
            if action not in ("require_approval", "block", "allow"):
                notes.append(f"- `{name}`: unknown action `{action}` for `{match}`; written as require_approval")
                action = "require_approval"
            rules.append(f"  - match: {match}\n    action: {action}")
            approvals.append(f"- `{match}` -> `{action}`")

        agents.append(AGENT.format(
            name=name, connectors=", ".join(apps), secrets=", ".join(keys)))
        docs[f"agents/{name}.md"] = DOC.format(
            name=name,
            purpose=(row.get("purpose") or "").strip() or
            "Purpose not stated in the inventory; write one sentence before the first run.",
            apps=", ".join(apps) or "no connected app",
            approvals="\n".join(approvals) or "- nothing beyond the default `risk` mode",
        )
        if keys:
            notes.append(f"- `{name}` expects {', '.join('`' + k + '`' for k in keys)}: "
                         "set values with `kortix secrets` after the first `kortix ship`.")

    manifest = HEAD.format(default=seen[0])
    if secrets:
        manifest += "\nenv:\n  required: [" + ", ".join(sorted(secrets)) + "]\n"
    if connectors:
        manifest += "\nconnectors:\n" + "".join(
            f"  - slug: {a}\n    provider: composio\n    app: {a}\n" for a in connectors)
    manifest += "\nagents:\n" + "".join(agents)
    manifest += "\npolicy:\n  default_mode: risk\n"
    if rules:
        manifest += "  policies:\n" + "\n".join(rules) + "\n"

    report = "# Report\n\nEverything the converter could not decide, as questions:\n\n"
    report += "\n".join(notes) if notes else "- nothing: every inventory row mapped cleanly"
    return manifest, docs, report + "\n"


def selftest() -> int:
    here = Path(__file__).resolve().parent
    manifest, docs, _ = build(json.loads((here / "example-inventory.json").read_text()))
    assert "default_agent: support" in manifest, manifest
    assert manifest.count("\nconnectors:") == 1, manifest
    assert "required: [GMAIL_API_KEY, NOTION_API_KEY, STRIPE_API_KEY]" in manifest, manifest
    assert "match: stripe.refund" in manifest
    assert manifest.count("kortix_permissions: none") == 2
    assert set(docs) == {"agents/support.md", "agents/research.md"}, docs
    assert "Purpose not stated" not in docs["agents/support.md"]
    print("selftest ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory")
    p.add_argument("--out")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.inventory or not a.out:
        p.error("--inventory and --out are required")
    manifest, docs, report = build(json.loads(Path(a.inventory).read_text()))
    out = Path(a.out)
    (out / "agents").mkdir(parents=True, exist_ok=True)
    (out / "kortix.yaml").write_text(manifest)
    for path, text in docs.items():
        (out / path).write_text(text)
    (out / "report.md").write_text(report)
    print(f"wrote {out}/kortix.yaml and {len(docs)} agent file(s); read report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
