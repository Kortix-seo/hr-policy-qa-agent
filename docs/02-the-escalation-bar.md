# The escalation bar, as data

Every HR agent has a list of questions it must not answer. In most deployments that list lives in a prompt, or in the head of whoever wrote it. Nobody can diff either one. Here the list is `escalation_rules.yaml`: eight rules, a fallback, and a reason string for each. This document explains what each rule protects. It also says why the rules run before the policy lookup, and what the checker can and cannot prove. The repository is a reference project built on Kortix, the open-source AI Operating System. It is open source, and the bar is the part worth copying into a new project first.

## A rule is a class of question, never a case

Each rule carries an `id`, a `label` for the person reading the escalation, and a `match_any` list of words and phrases. A rule matches when the question contains one of those terms, case-insensitive, as a whole word or a whole phrase. The first matching rule in file order decides the reason.

The whole-word part carries weight. `pay` is a compensation term. `payment` is not, so a question about vendor payment terms escalates as `policy_gap` rather than for the wrong reason. `test_rule_matches_whole_words_only` pins that behavior, because a substring matcher would send a supplier invoice to the compensation queue.

## The eight rules

- **`compensation`** (Pay, equity, bonus and offer decisions). Protects pay, equity, bonus, counteroffers and merit increases. A question about an offer from another company is a negotiation. A negotiation is not a policy lookup.
- **`legal`** (Legal, regulatory and immigration matters). Protects anything with a lawyer, a subpoena, immigration status, a visa, a work permit, a discrimination charge, a data subject request or a union matter. These carry deadlines the company can miss, and words that become evidence.
- **`medical_or_accommodation`** (Health, medical and accommodation requests). Protects medical detail, diagnoses, sick notes, disability, accommodation requests, pregnancy and restricted duties. The library can say how sick leave works. It cannot say what a diagnosis means for one person's job.
- **`harassment_and_complaints`** (Harassment, discrimination and complaints about a person). Protects complaints about a colleague, including the phrasing people actually use, such as comments about an accent or a hostile standup. The first reply in a complaint becomes part of the record.
- **`exception_request`** (Requests to waive, bend or override a policy). Protects every request to waive, override or make an allowance. The policy files state numbers. Only a person can decide that a number does not apply this time.
- **`performance_and_discipline`** (Performance, discipline and probation). Protects improvement plans, warnings, probation and demotion. The existence of a plan is sensitive before anyone asks about its content.
- **`termination_and_separation`** (Termination, layoffs and severance). Protects layoffs, dismissals, severance, termination and redundancy, including a question phrased about "someone" rather than the asker.
- **`personal_situation`** (An individual's personal circumstances). Protects the questions that describe a life: a divorce, custody, childcare, a partner's illness, an immigration status. None of these has a policy section. All of them arrive in the same inbox as "how many sick days do I have".

## The fallback

When no rule matches and no policy file covers the question, the run escalates with the reason `policy_gap`. The name is chosen so the escalation queue reads as a to-do list for the policy library. Study leave is the example. The bar does not treat study leave as sensitive, and no policy file mentions it. It escalates as a gap. The fix is a heading in `policies/pto-and-leave.md` plus `study leave` in that file's `covers` list, not a ninth rule.

`policy_gap` is also the honest answer for anything the library almost covers. A file that mentions a topic in passing does not answer a question about it. The fallback is the only route that keeps the agent from filling that space with plausible prose.

## Why the rules run before the lookup

The order is the guarantee, not an optimization. `check_escalation.py` walks the rules first and the policy `covers` lists second, and the agent's prompt states the same order. Try the other order on "my doctor signed me off during parental leave, what now?". The lookup finds `parental leave` in a file and produces a draft. Only then does the run discover that the question also matched the medical rule. By that point the draft exists, and somebody has to catch it before it goes out.

Running the bar first makes the escalation unconditional. A matching rule ends the question's path through the loop, whatever the library says. The policy library is allowed to be incomplete for the same reason. A missing paragraph costs one escalation. A paragraph that half-answers a sensitive question costs a wrong reply.

## What the checker scores

`sample_questions.yaml` holds 18 questions with the verdict each one must get: `answer` plus the policy file, or `escalate` plus the rule id. `check_escalation.py` runs every question through the same classifier the prompt describes, and prints one line per question. On the library as it stands:

```
18/18 questions met the bar (8 rules, 4 policy sections)
```

The suite behind it, `python3 -m pytest -q`, checks the properties that matter more than the score. Whole-word matching. Rules winning over coverage. An uncovered question falling back to `policy_gap`. Every policy file named by a question existing on disk. A bar change that starts answering something it used to escalate fails there before it ships.

## What the checker cannot prove

The matcher is coarse on purpose. The limits are worth stating plainly, because they are the reason a person still reviews a rule change.

- **It matches terms, not meaning.** A question can be about compensation without using any of the compensation words, and the checker will route it to the policy lookup. "Can I carry over 30 days because my manager promised?" matches `carry over`. It is answered from a file whose carry-over limit is 15 days. The reply quotes the rule correctly, and it is still not the reply that question needs.
- **Every hole is a question nobody wrote down.** The 18 questions are a sample of an inbox, not its population. A question that avoids every term in every rule and every `covers` list lands in `policy_gap`. That is safe and unhelpful, and no test fails because no test exists for it.
- **It records one reason.** The first match wins, so a question that raises two sensitive classes keeps only the earlier rule's id. "A comment about my accent, and a question about my visa" escalates as `harassment_and_complaints`. The legal half travels as text in the question, not as a label. That is why the channel post carries the whole question next to the reason instead of a summary.
- **It does not read the drafts.** Answer quality, quote fidelity and tone sit outside the checker entirely. It scores routing, and it says so.

None of these limits is a reason to drop the checker. They are the reason it is called a pre-check rather than the control.

## The review a change to the bar deserves

A change to `escalation_rules.yaml` is an HR decision stored in a file, so the pull request carries more than a diff. It carries the question that prompted the change, added to `sample_questions.yaml` with its expected verdict. It carries the checker's output. The reviewer asks three things. Does the new term appear in any policy file, so that the rule now shadows a documented answer? Would the term capture a class of question, or one person's phrasing? And does the fallback cover the case if the rule is not added?

Session work reaches `main` through a change request. Merge is default-deny for agents, which means the bar cannot widen itself. The agent that reads the inbox has no push and no merge, and the file it obeys is the file a person approved.

## Where this sits next to an HR suite

An HR suite's agent inherits the suite's rules, applied to the records the suite holds. That is a real advantage inside those records, and it stops at their edge. This bar is a different kind of object. It is a file the company writes, versioned next to the policy library it qualifies, and readable by anyone who has to sign off on the agent. The comparison with the suite agents, and the point where each design fits, is in [AI agents for HR compared with Workday, Oracle and Lattice](https://aiagentsforhrguide.com/ai-agents-for-hr-vs-workday-oracle-lattice).
