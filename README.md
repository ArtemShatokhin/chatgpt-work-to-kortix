# chatgpt-work-to-kortix

Turn a ChatGPT Work agent inventory into a Kortix project you can run, review and own.

When a team decides to move work off ChatGPT Work, the inventory travels as a spreadsheet or a JSON export: agent names, the apps each one may touch, which actions need a human, and who owns it. None of that export is runnable. This repository converts it into a Kortix project — a `kortix.yaml`, one agent file per inventory row, and deny-by-default grants — so the first thing the team runs is a project it can read, not a rewrite.

## What it does

```
inventory.json  ->  kortix.yaml
                    agents/<agent>.md
                    report.md
```

- Every agent in the inventory becomes an entry in `agents:` with its own file.
- Every app an agent may touch becomes a connector, and only those connectors are granted to that agent. `kortix_permissions: none` is the agent's whole grant on the project; an omitted grant also means none.
- Any inventory row marked as needing approval becomes a `policy.policies` rule with `action: require_approval`, and `policy.default_mode` is written as `risk` so writes and destructive calls stop for a person even where no rule matches.
- Anything the converter could not map is written to `report.md` as a question for a human. It never guesses a connector or a scope.

## The inventory format

```json
{
  "workspace": "acme",
  "agents": [
    {
      "name": "support",
      "purpose": "Answer customer email with the order history in front of it",
      "apps": ["stripe", "gmail"],
      "approvals": [
        { "match": "stripe.refund", "action": "require_approval" },
        { "match": "gmail.send_email", "action": "require_approval" }
      ]
    }
  ]
}
```

`apps` are app slugs as the connector catalogue writes them. `approvals[].match` is a `domain.resource.verb` pattern — the same shape Kortix records for every action — so a policy rule and an audit row use the same word for the same thing.

## Run it

```bash
python3 convert.py --inventory example-inventory.json --out ./my-project
cd my-project && kortix validate
```

`kortix validate` exits 0 when the project is internally consistent, and 1 with errors. It checks that every agent file the manifest names exists, that every connector slug is declared under `connectors:`, and that every secret name the agents use is declared under `env:`. It does **not** check `policy` or `policies`: a malformed rule is skipped at connector sync and surfaces afterwards as a connector error, so read the rules the converter wrote before the first sync.

`convert.py --selftest` runs the converter against the bundled inventory and asserts the output, so a change to the templates fails loudly. It needs only the standard library.

## What it deliberately does not do

- It does not call the OpenAI API or scrape a tenant. Take the inventory out through your own admin process; this repository starts after that.
- It does not create accounts, projects or secrets. The output is files you commit and review.
- It does not claim feature parity. A control Work offers that Kortix handles differently is listed in `report.md` rather than translated into wishful YAML.

## Where the comparison lives

The control-by-control comparison, with OpenAI's own sentences behind each row, is at [kortix.com/blog/chatgpt-work-for-enterprise](https://kortix.com/blog/chatgpt-work-for-enterprise). The narrower question — what a fully self-hosted deployment looks like — is at [chatgptworkalternative.com](https://chatgptworkalternative.com).

Kortix is the open-source AI Operating System: agents, skills, company memory and connectors in one git repository you own, with every agent working on its own cloud computer. Free to start, free to self-host.

## Licence

MIT. The converter is a hundred lines and a template; keep it in your own repository if that is easier than depending on this one.
