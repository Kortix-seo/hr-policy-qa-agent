# Wiring the inbox

This repository is a reference HR policy helpdesk agent for Kortix, the open-source AI Operating System. It is open source, and it runs as it stands: the trigger, the agent and the policy library are all in `kortix.yaml`, and the checker passes. What it does not have is a mailbox. This document gives the order of operations for pointing the loop at a real HR inbox. Follow it in the order that keeps a mistake away from an employee.

Each step is small. The order matters more than the speed. A connector added before the rules are read is a connector an agent can call. A trigger enabled before the tests run is a batch of drafts nobody checked.

## 1. Add the three connectors

The manifest grants none, and that is deliberate. In a v2 manifest an omitted grant means none. The agent reaches nothing until a line says it may.

```yaml
connectors:
  - slug: gmail
    provider: composio
    app: gmail
  - slug: notion
    provider: composio
    app: notion
  - slug: hr-channel
    provider: channel
    platform: slack
```

Then name the same three slugs in the agent's grant. Leave `secrets` empty, because the credentials live in the connector account rather than in a secret the sandbox reads:

```yaml
agents:
  hr-policy-desk:
    connectors: [gmail, notion, hr-channel]
    secrets: none
```

The `app` values are the catalog names for the apps you connect. Give the policy library connector a read-only account, so that the grant cannot edit a policy page even if a prompt asks it to. Connector credentials are brokered server-side and never enter the machine. That is how the agent can read an inbox without holding a token for it. The catalog is wide (3,000+ apps in a click, plus MCP, OpenAPI, Postman, GraphQL and raw HTTP). Pick the narrowest connector that does the job.

Run `kortix validate --file kortix.yaml` after this edit. One class of error it catches: a connector slug an agent names that the top-level `connectors` list does not declare.

## 2. Keep the send on approval

The manifest ships two rules, and the first is the one this loop depends on:

```yaml
policy:
  default_mode: risk

policies:
  - match: "*.send_email"
    action: require_approval
  - match: "*.*.delete*"
    action: block
```

A rule matches a fully qualified tool path, `<connector-slug>.<tool>`. So `*.send_email` covers every connector's send tool without naming one. The second rule refuses every delete call on every connector. That is what keeps an agent with inbox access away from a thread, a page or a record it was only meant to read.

`default_mode: risk` is not the default. Approval gates you set. Off until you set them. Under `risk`, a read runs. A write or a destructive call waits for a person. That is the mode an inbox needs; the alternative, `allow_all`, runs the call.

One consequence deserves a decision rather than a surprise. Creating a draft is a write, so under `risk` the draft-creating call is held too. A run can end with an escalation posted and a draft still waiting. If you want drafts to land unattended while sends stay held, add the draft tool explicitly:

```yaml
  - match: "gmail.create_draft"
    action: always_run
```

Take the tool name from the connector's tool list in the project settings rather than from this example. That line is a real trade. It lets one write reach an employee's mailbox without a person in between. It is worth writing only because the message it creates cannot leave the mailbox until someone sends it.

`kortix validate` does not check `policy` or `policies`. When the connectors sync, a malformed rule is skipped and reported as a connector sync error. Read the rules back in the connector settings after the merge, not only in the diff.

## 3. Set an approval lifetime a person answers

```yaml
approvals:
  ttl: 4h
```

`approvals.ttl` is how long a held call waits for a decision. It takes an integer and `m`, `h` or `d`. Kortix clamps it to five minutes through 30 days. Without the key, or with a value it cannot read, a held call waits 24 hours. A held call nobody decides expires. An expired call does not run.

Four hours fits an HR desk that answers within a working day. A draft created at 09:00 is still waiting at lunch. Nothing expires at 03:00 for a person to find in the morning. A team spread across timezones should shorten it to something the on-call person will see. A long ttl turns a paused call into a silent one.

## 4. Run the checker and the tests before the cron

Both commands run from the repository root and need only PyYAML and pytest:

```bash
python3 -m pip install -r requirements.txt
python3 check_escalation.py
python3 -m pytest -q
```

The checker prints one line per sample question and ends with the score. A failure names the question, the expected verdict and the verdict it got. That is usually enough to see whether a rule or a `covers` list moved.

Put both commands in CI on every pull request. The workflow needs no credentials:

```yaml
on: [pull_request]
jobs:
  bar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 -m pip install -r requirements.txt
      - run: python3 check_escalation.py
      - run: python3 -m pytest -q
```

The manifest schema check runs on its own. `kortix validate` is the same check `kortix ship` runs and the change request merge runs. A CI job does not need the CLI to gate the pull request.

## 5. Enable the trigger

The last step is the one that starts spending money and writing to a mailbox. Leave the trigger disabled until steps 1 to 4 are merged. Then set `enabled: true` on `hr-inbox-sweep` and ship it, or use the CLI to flip the flag and `kortix ship` to push the change. It takes effect when it reaches the default branch.

Before the first run, narrow the trigger to one label or one mailbox folder if your connector supports a filter. Send it three questions of your own. Two that the library documents, and one that it does not. You are checking three things. The draft quotes the section you expected. The uncovered question lands in the channel with `policy_gap`. The thread carries a label afterwards. A run that fails any of those has a prompt or a grant problem, not a scheduling problem.

## The first week

Count four numbers daily: threads answered, drafts a person sent unchanged, drafts a person rewrote, and escalations by rule id. Read the third number closely. A rewritten draft means the quoted section did not match the question. The fix is usually a heading in a policy file, not a sentence in the prompt. A cluster of `policy_gap` escalations is the library's backlog, written down.

## The second and third inbox

The loop generalizes because the parts are separate. The bar is a data file. The answers are a policy library. The connector grants are lines in a manifest. A start date needs a mailbox, groups, a Slack channel and a repository seat. That is [the onboarding and offboarding loop](https://aiagentsforhrguide.com/onboarding-and-offboarding-agents): the same cron, the same approval rule on any write, and a checklist a person reads before the first day. A recruiting inbox is a different case. A screening or scheduling decision about a candidate changes that person's prospects. [The parts of hiring that stay with a person](https://aiagentsforhrguide.com/hiring-agents-screening-and-scheduling) are larger than the parts that do not. Build the policy desk first. It is the workflow where an answer that stops at a draft costs the least if the wiring goes wrong.
