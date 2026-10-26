# An open-source HR policy helpdesk agent for Kortix

An HR inbox collects two very different kinds of question and gives them one queue. One is "how many vacation days carry over", which a policy document already answers word for word. The other is "my doctor put me on restricted duties", which no document should answer at all. This repository is a reference agent that separates those two, built on Kortix, the open-source AI Operating System. It drafts a reply when a policy section covers the question and hands everything else to a person, with the reason and no attempted answer.

The file worth reading first is `escalation_rules.yaml`. It holds the list of questions the agent must never answer, as eight rules and a fallback, in a file a reviewer can diff and a checker can test.

## The loop: cron, classify, draft, escalate

A cron trigger fires every 15 minutes and starts a fresh session. One isolated sandbox per session. Each session has its own isolated machine and branch. Nothing carries over to the next run, so the inbox's own labels are the record of what has been handled. The agent reads the unlabelled threads and works in this order.

1. **Classify before reading any policy.** Every question is matched against `escalation_rules.yaml`, whole words and phrases, case-insensitive. The first matching rule decides the outcome, and a rule hit ends that thread's run.
2. **Draft only from a documented section.** A question that no rule matched is looked up in `policies/`. When a section documents it, the draft quotes that section and names the file and the heading it came from.
3. **Escalate the rest.** A rule hit, or a question that no policy section covers, goes to the HR channel with the question, the rule id and the reason. No answer is attempted.
4. **Label what was touched.** Every thread the agent drafted for or escalated gets a label, so the next run leaves it alone.

The order is the safety property. A question about a raise fails at step 1 even when the compensation policy is excellent, because the rule runs before the lookup.

## What is in the repository

| File | What it is | Where to look |
| --- | --- | --- |
| `kortix.yaml` | The v2 manifest: one agent, one cron trigger, the connector policy | `policy.default_mode: risk` and the two rules |
| `agents/hr-policy-desk.md` | The agent's prompt | the order of operations |
| `skills/hr-policy-triage/SKILL.md` | The triage skill the agent loads | how an answer and an escalation are written |
| `escalation_rules.yaml` | The bar: eight rules plus the `policy_gap` fallback | the `match_any` terms |
| `sample_questions.yaml` | Eighteen questions with the verdict each one must get | ten answers, eight escalations |
| `check_escalation.py` | Scores the bar against the sample questions | the table it prints |
| `tests/test_check_escalation.py` | The same comparison as tests, plus edge cases | the whole-word match test |
| `policies/*.md` | The policy library the agent answers from | front matter with `title` and `covers` |

Each policy file is plain markdown with front matter. `covers` lists the terms the file is responsible for, and the checker reads that list to decide whether a question is documented. `sample_questions.yaml` expects four files: `pto-and-leave.md`, `remote-and-hybrid-work.md`, `expenses-and-travel.md` and `learning-and-equipment.md`.

## The bar is a file, and the guardrails are in the manifest

`escalation_rules.yaml` holds one entry per class of question that belongs to a person: `compensation`, `legal`, `medical_or_accommodation`, `harassment_and_complaints`, `exception_request`, `performance_and_discipline`, `termination_and_separation` and `personal_situation`. Each entry has an `id` the agent reports, a `label` a person reads in Slack, and the `match_any` terms that trigger it. The fallback, `policy_gap`, is what the agent reports when no rule matched and no policy section covers the question.

Because a rule beats the policy library, a documented topic can still escalate. Parental leave is a documented subject, and "my doctor signed me off during parental leave" still goes to a person, because the medical rule matches first.

The manifest carries the loop and the guardrails next to each other:

```yaml
triggers:
  - slug: hr-inbox-sweep
    type: cron
    agent: hr-policy-desk
    session_mode: fresh
    cron: "0 */15 * * * *"

policy:
  default_mode: risk

policies:
  - match: "*.send_email"
    action: require_approval
  - match: "*.*.delete*"
    action: block

approvals:
  ttl: 4h
```

`policy.default_mode: risk` is the default for any connector call that no rule matches: a read runs, a write waits for approval. Approval gates you set. Off until you set them. This manifest states the mode instead of taking the platform default. The two project rules sit on top of it. A send needs a person, a delete is refused outright, and a held call waits four hours for an answer before it expires. Connector credentials are brokered server-side and never enter the machine. Nothing in the manifest holds one.

`connectors` is `none` on the agent as it ships. The agent can read the repository and nothing else, which is the right starting point for an agent that touches an employee inbox and the company policy record. Add the Gmail, policy-library and Slack connectors you use, grant them to `hr-policy-desk`, then re-read the two rules above and confirm they still match the tool names you granted.

Validate the manifest before you push it:

```bash
kortix validate --file kortix.yaml
```

## Run the checker and the tests

```bash
python3 -m pip install -r requirements.txt
python3 check_escalation.py
python3 -m pytest -q
```

The script is committed without the executable bit, so call it through `python3` rather than `./check_escalation.py`. It prints one line per question with an `ok` or `FAIL` marker, then what the sample expected against what the rules produced. A closing line counts how many questions met the bar and how many rules and policy files the run read. Add `--json` for the same report as data. Exit code 0 means every expectation held, 1 means at least one did not, and 2 means a file could not be read. If you see `no policy files found`, the checkout has no `policies/*.md` and the coverage half of the check cannot run.

The test file holds five tests. Four compare the rules against one question each: `pay` matches a rule while `payment` does not, a medical question about a documented topic still escalates, an uncovered question falls back to `policy_gap`, and every answered question names a policy file that exists. The fifth is an integration test. It scores all eighteen sample questions the same way the script does, so a rule that starts answering something the sample says must escalate fails there first.

## What the checker is and is not

`check_escalation.py` is a coarse pre-check. It matches keywords and phrases against the question text, then checks coverage against the front matter of the policy files. It does not read a question the way a person does. A hostile paraphrase can slip past the terms, and a generous `covers` list can make an undocumented question look answered.

So the checker is not the agent's judgment, and a passing run is not proof that the bar is right. The real control is a person reading the diff. A change to `escalation_rules.yaml`, or to a `covers` list in `policies/`, is the moment where a question starts or stops being answered by a machine. That change belongs in a pull request with a reason. The checker exists to make that review cheap and to fail loudly when a rule starts answering something the sample says must escalate.

## Change the bar

Adding a rule takes three edits: an entry in `escalation_rules.yaml`, at least one question in `sample_questions.yaml` that the rule must catch, and a run of both commands above. A rule with no sample question is untested, and nothing warns you when it starts firing on the wrong question.

Adding a policy file means front matter with a `title` and a `covers` list. Keep the covers narrow. Every term you add to that list is a question the agent may answer without a person.

Fork the repository and point the agent at your own library. Open source. Read it, fork it, audit it.

## Where to read more

The longer walkthrough of this agent, with the Gmail, policy-library and Slack wiring, is on the [HR policy QA agent page](https://aiagentsforhrguide.com/hr-policy-qa-agent). The question of who signs off on a rule change, and where approvals sit in an HR workflow, is covered in [governance and approvals](https://aiagentsforhrguide.com/hr-ai-governance-and-approvals). For the wider pattern behind these files, see [the Kortix blog](https://kortix.com/blog/ai-agents-for-hr).

Kortix is the open-source AI Operating System this agent runs on. [Try Kortix](https://kortix.com) and run this agent against your own policy library.
