---
name: hr-policy-triage
description: Triage rules for an open-source HR policy helpdesk agent, covering how to classify a question against the escalation bar, answer from a documented policy section, and write an escalation.
---

# HR policy triage

Triage decides one thing per question: does documented policy answer this, or does a person? Getting that split right matters more than the wording of the reply, because a wrong answer to a pay or medical question is a commitment the company has to live with. The agent that loads this skill is one agent working an inbox on Kortix, the open-source AI Operating System, with read access to the repository and no send authority of its own.

## The procedure

Run the steps in order for every unlabelled thread. Skipping step 1 to save time is how a documented question gets answered when it should have escalated.

1. **Load the bar.** Read `escalation_rules.yaml` at the start of the run. The rule ids, the terms and the fallback live there and nowhere else.
2. **Normalise the question.** Reduce the thread to the question being asked, in the asker's own words. If a thread asks two things, treat it as two questions and handle the stricter one first.
3. **Match the rules first.** Check every rule's `match_any` terms against the question text, whole word or whole phrase, case-insensitive. The first rule in file order that matches wins. Record its `id`, its `label` and the term that matched.
4. **Check coverage only if no rule matched.** Look for a section in `policies/` that documents this exact question. Use the `covers` list in a file's front matter to find candidates, then read the section.
5. **Decide.** A rule hit escalates. No rule hit and a documenting section means answer. No rule hit and no documenting section means escalate as `policy_gap`.
6. **Write one output.** A draft reply, or an escalation message. Never both, and never a draft that also mentions the escalation reasoning.

When the decision is close, escalate. An unnecessary escalation costs a few minutes of HR attention. An unnecessary answer can cost the company a promise it did not make.

## The escalation bar, rule by rule

The eight ids below are the classes of question the agent must never answer, even when a policy page appears to cover the topic. They are defined in `escalation_rules.yaml`, together with the terms that trigger them. Read that file for the current list rather than trusting a copy of it.

| Rule id | What it covers |
| --- | --- |
| `compensation` | Pay, equity, bonus, merit increases, counteroffers, pay bands |
| `legal` | Legal advice, lawsuits, subpoenas, immigration and visa matters, discrimination charges, data subject requests, union matters |
| `medical_or_accommodation` | Health, diagnoses, sick notes, disability, pregnancy, mental health, restricted duties |
| `harassment_and_complaints` | Harassment, bullying, discrimination, complaints about a colleague |
| `exception_request` | Requests to waive, bend or override a policy |
| `performance_and_discipline` | Improvement plans, warnings, probation, demotion |
| `termination_and_separation` | Layoffs, dismissal, severance, redundancy |
| `personal_situation` | An individual's own circumstances, such as custody, childcare or a partner's illness |

The fallback `policy_gap` covers the rest: a question that matches no rule and that no policy section documents. It is an escalation reason in its own right, so a gap in the library is reported rather than filled.

Two rules can match one question. Report the first in file order, and add the second id in the message body so the reviewer sees both. A question about pay during parental leave is a compensation question before it is a leave question.

## Answering from a policy section

An answer exists only when a section states the thing that was asked. Quote the sentence, or paraphrase it so closely that a reader can find the original. Name the file and the heading in the draft, every time, so the person can check it themselves.

Read the whole section before you quote from it. A heading often covers more than the paragraph under it, and a limit stated in one bullet can be qualified two bullets later. If the section answers part of the question, draft the part it answers and escalate the rest as `policy_gap` rather than filling the gap with a reasonable assumption.

Do not extend, soften or reconcile policies. Do not combine two sections into a rule the library never states. Do not describe what usually happens at other companies. If two policy files disagree, escalate and name both files.

## Writing the escalation message

Post to the HR channel in this shape:

```
Question: <the question as asked, identifying detail removed>
Rule: <rule id> (<label>)
Why: <one line, in the words of the label>
```

Three lines, nothing else. No attempted answer, no suggested outcome, no reading of the policy that might apply. The reviewer needs the question and the reason it stopped, and a guess in the message makes the escalation harder to trust.

Remove names, team names and medical detail before posting. The channel is for the reason, and the person who asked already knows the rest. If the question cannot be understood without the identifying detail, say that in the `Why` line and keep the detail out.

## Failure modes this bar exists to prevent

- **The confident near-miss.** The library documents the topic, the question is about a specific person, and the model generalises the policy onto that person. The bar catches the class before the lookup, which is why the rules run first.
- **The keyword slip.** Terms are matched whole, so `pay` does not fire on `payment`. That works in both directions: a question can ask about money without using any term on the list. Coverage is a check, not a judgment, and a question that feels like compensation belongs with a person even when no rule matched.
- **The helpful extension.** "In your case we can probably..." is a commitment nobody authorised. Exceptions escalate, including small ones, including ones a manager already agreed to.
- **The silent gap.** A question the library never addresses gets answered from general HR knowledge. `policy_gap` exists so that the gap is reported instead of smoothed over.
- **The leaked detail.** An escalation that quotes a diagnosis, or a draft that repeats a personal circumstance, moves information further than the question required.
- **The stale assumption.** Each run is a fresh session with no memory, so nothing carries over except labels. Never reason from what an earlier run "already handled".
- **The drifting bar.** A rule added to a prompt instead of the rules file is a rule nobody reviews. Changing the bar means editing `escalation_rules.yaml`, adding a sample question that proves the change, and opening a pull request for a person to approve.

`check_escalation.py` scores the rules against `sample_questions.yaml` and catches a rule that starts answering something it used to escalate. The script matches keywords and coverage, so a pass tells you the file is internally consistent. It does not tell you the bar is right. That is the reviewer's job, and the pull request is where it happens.
