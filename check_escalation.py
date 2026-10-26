#!/usr/bin/env python3
"""Score the escalation bar of an open-source HR policy helpdesk agent.

This repository is a reference project built on Kortix, the open-source AI
Operating System. An HR policy agent that answers from a policy library has one
requirement that matters more than answer quality: it must never answer the
questions that belong to a person. That rule lives in `escalation_rules.yaml`
and in the `covers:` list of each file under `policies/`, so it can be reviewed
in a pull request. This script is the check that keeps the two honest.

It classifies every question in `sample_questions.yaml` and compares the result
with the expectation recorded there:

    python3 check_escalation.py            # table plus a pass/fail line
    python3 check_escalation.py --json     # machine-readable report

Exit codes: 0 every expectation matched, 1 at least one did not, 2 a file could
not be read.

The matcher is deliberately coarse: keyword and phrase rules over the question
text, plus a coverage check against the policy library. It is a pre-check for
the bar, not the agent's own judgment, and the README says so.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment problem, not a rules problem
    sys.exit("check_escalation.py needs PyYAML: python3 -m pip install pyyaml")

ROOT = Path(__file__).resolve().parent
WORD_LEFT = r"(?<![a-z0-9])"
WORD_RIGHT = r"(?![a-z0-9])"


def term_pattern(term: str) -> re.Pattern[str]:
    """A whole-word/whole-phrase, case-insensitive pattern for one rule term."""
    return re.compile(WORD_LEFT + re.escape(term.strip().lower()) + WORD_RIGHT, re.IGNORECASE)


def read_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        sys.exit(f"cannot read {path}: {exc}")
    except yaml.YAMLError as exc:
        sys.exit(f"{path} is not valid YAML: {exc}")


def load_rules(path: Path) -> tuple[list[dict], str]:
    data = read_yaml(path)
    rules = []
    for rule in data.get("rules") or []:
        compiled = [term_pattern(t) for t in rule.get("match_any") or []]
        if not compiled:
            sys.exit(f"rule {rule.get('id')!r} has no match_any terms")
        rules.append({"id": rule["id"], "label": rule.get("label", rule["id"]), "patterns": compiled})
    fallback = data.get("fallback") or "policy_gap"
    return rules, fallback


def load_policies(policy_dir: Path) -> list[dict]:
    """Every policy file's front matter: its title and the terms it covers."""
    sections = []
    for path in sorted(policy_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            sys.exit(f"{path} has no front matter: expected title and covers")
        head = text.split("---", 2)[1]
        try:
            meta = yaml.safe_load(head) or {}
        except yaml.YAMLError as exc:
            sys.exit(f"{path} front matter is not valid YAML: {exc}")
        covers = meta.get("covers") or []
        if not covers:
            sys.exit(f"{path} declares no covers")
        sections.append(
            {
                "file": str(path.relative_to(ROOT)),
                "title": meta.get("title", path.stem),
                "patterns": [term_pattern(t) for t in covers],
            }
        )
    if not sections:
        sys.exit(f"no policy files found in {policy_dir}")
    return sections


def classify(question: str, rules: list[dict], sections: list[dict], fallback: str) -> dict:
    """Return {verdict, reason, policy} for one question.

    The rules run first: any rule hit escalates, whatever the policy library says.
    Only a question no rule matches is checked against the library, and a question
    the library does not cover escalates as `fallback`.
    """
    for rule in rules:
        for pattern in rule["patterns"]:
            hit = pattern.search(question)
            if hit:
                return {"verdict": "escalate", "reason": rule["id"], "policy": None, "matched": hit.group(0)}
    for section in sections:
        for pattern in section["patterns"]:
            hit = pattern.search(question)
            if hit:
                return {"verdict": "answer", "reason": "documented", "policy": section["file"], "matched": hit.group(0)}
    return {"verdict": "escalate", "reason": fallback, "policy": None, "matched": None}


def score(questions: list[dict], rules: list[dict], sections: list[dict], fallback: str) -> list[dict]:
    results = []
    for item in questions:
        result = classify(item["question"], rules, sections, fallback)
        expected = item["expected"]
        if expected == "answer":
            ok = result["verdict"] == "answer" and result["policy"] == item.get("policy")
            want = f"answer from {item.get('policy')}"
        else:
            ok = result["verdict"] == "escalate" and result["reason"] == item.get("rule")
            want = f"escalate: {item.get('rule')}"
        results.append(
            {
                "id": item["id"],
                "question": item["question"],
                "want": want,
                "got": f"{result['verdict']}: {result['reason']}",
                "matched_on": result["matched"],
                "ok": ok,
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rules", default=str(ROOT / "escalation_rules.yaml"))
    parser.add_argument("--questions", default=str(ROOT / "sample_questions.yaml"))
    parser.add_argument("--policy-dir", default=str(ROOT / "policies"))
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    rules, fallback = load_rules(Path(args.rules))
    sections = load_policies(Path(args.policy_dir))
    data = read_yaml(Path(args.questions))
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {args.questions}")

    results = score(questions, rules, sections, fallback)
    failed = [r for r in results if not r["ok"]]

    if args.json:
        print(json.dumps({"rules": len(rules), "policy_sections": len(sections), "results": results, "failed": len(failed)}, indent=2))
    else:
        width = max(len(r["question"]) for r in results)
        for r in results:
            mark = "ok  " if r["ok"] else "FAIL"
            print(f"{mark}  {r['id']}  {r['question']:<{width}}  want {r['want']:<28}  got {r['got']}")
            if not r["ok"]:
                print(f"      matched on {r['matched_on']!r}")
        print()
        print(f"{len(results) - len(failed)}/{len(results)} questions met the bar ({len(rules)} rules, {len(sections)} policy sections)")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
