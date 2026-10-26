# The loop: what one run does

This repository is a reference HR policy helpdesk agent for Kortix, the open-source AI Operating System. Its whole job fits in one loop. The loop starts when a cron fires and ends when a Gmail thread carries a label. Everything else here exists to make that loop safe: the policy library it may quote, the escalation bar it has to check first, and the checker that scores both.

It is open source, so the loop described below is the loop you can run. Read it end to end before changing any of it. The order of the steps is the safety property. Move a step earlier or later and you change what the agent can do to somebody's inbox.

## The trigger

```yaml
triggers:
  - slug: hr-inbox-sweep
    type: cron
    agent: hr-policy-desk
    session_mode: fresh
    cron: "0 */15 * * * *"
```

The trigger's `prompt` is the job description, and it names the order. Classify first. Answer only from a section of `policies/` that documents the question. Draft, never send. Post anything the bar escalates. Label every thread the run touched.

Fifteen minutes is a scheduling choice, not a promise about latency. A question that lands at 09:07 gets its draft some time after 09:15. Nothing in the system promises a faster path. The interval exists so that a question arriving during a run is picked up by the next one.

## Seven steps from fire to label

1. **List the unlabeled threads.** The run reads the HR inbox and keeps the threads with no label from the set the agent applies. A thread the previous run labeled is skipped, whatever state it is in.
2. **Classify before reading any policy.** Every question is matched against `escalation_rules.yaml`, whole word or whole phrase, case-insensitive. The first rule that matches decides the reason. No policy file is opened at this step.
3. **Escalate when a rule hits.** The run posts the question, the rule id and the rule's label to the HR channel. It writes no draft. Not a holding reply either.
4. **Find the policy section when no rule hits.** The `covers` list in each policy file's front matter decides which file is relevant. Inside the file, the heading that answers the question decides which paragraph gets quoted.
5. **Draft the reply.** The draft quotes or closely paraphrases that section, and it names the file and the heading it came from. The draft is the only artifact the answering path produces.
6. **Save the draft in the thread.** The agent has no send authority. A person opens the draft, checks the quote, and presses send.
7. **Label the thread.** The label records that this run handled the thread. Nothing more. It does not record a verdict, and it does not say whether a person sent the draft, changed it or threw it away.

Steps 3 and 5 are exclusive. A question that hits a rule never reaches the policy lookup. A question that reaches the policy lookup has already passed every rule.

## Why every run starts with a fresh session

`session_mode: fresh` gives each firing a new session with no memory of the last one. One isolated sandbox per session. Each session has its own isolated machine and branch.

That choice removes a class of bug and creates one obligation. It removes the agent that remembers a question from three hours ago and answers the follow-up from recollection instead of from the file. It also removes the run whose context grew until it began inventing a policy section. In exchange, the loop has nowhere to keep progress except the inbox itself. That makes the label heavier than it looks. It is the only record that a thread has been handled.

Two consequences follow, and both show up in practice. A run that dies after step 6 and before step 7 leaves a draft with no label, so the next run drafts the same reply again. Duplicate drafts are the cost of a crash. That cost is lower than a silent skip, which is what an optimistic label applied at the start would produce. The second consequence is that the labels have to survive a change to the prompt or the rules. Anything a run needs to know about a thread must be readable from the thread.

## Where state lives

The loop keeps state in three places. None of them is the session.

- **Gmail labels** record which threads have been handled.
- **`policies/` and `escalation_rules.yaml`** hold what the agent may say and what it must refuse. Both are files in this repository, so a change to either one arrives as a diff.
- **The HR channel** holds the escalations, with the question and the reason together. That is the context the person picking one up would otherwise rebuild from the thread.

Connector credentials are brokered server-side and never enter the machine, so the session holds no token for the inbox, the policy library or the channel. Every action is recorded. Reading, exporting and streaming the audit log depend on the plan.

## What a run never does

A run never sends mail. It never edits a policy page, never grants an exception, and never decides anything about a person. Those limits are not prompt etiquette. The manifest enforces two of them: the agent has no write grant, and every send call waits for a person. The other two are why `escalation_rules.yaml` runs before the policy lookup instead of after it.

The write-up of the loop Kortix runs on its own HR inbox walks the same steps from the inbox's side. It is also where the draft-rather-than-send design is argued: [the HR policy desk](https://aiagentsforhrguide.com/hr-policy-qa-agent). What a reviewer reads in the manifest before switching the trigger on is on [the governance page](https://aiagentsforhrguide.com/hr-ai-governance-and-approvals).

## What to read next

`docs/02-the-escalation-bar.md` takes the bar apart rule by rule, and says what the checker can and cannot prove. `docs/03-wiring-the-inbox.md` gives the order of operations for pointing this loop at an inbox that is not the example one.
