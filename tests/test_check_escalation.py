"""Tests for the escalation bar in this open-source reference project.

Run them from the repository root:

    python3 -m pytest -q

The integration test scores sample_questions.yaml the same way the CLI does, so a
rule that starts answering something it used to escalate fails here first.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import check_escalation as ce  # noqa: E402


def fixtures():
    rules, fallback = ce.load_rules(ROOT / "escalation_rules.yaml")
    sections = ce.load_policies(ROOT / "policies")
    return rules, sections, fallback


def test_rule_matches_whole_words_only():
    rules, sections, fallback = fixtures()
    # "pay" is a compensation term; "payment" must not be.
    assert ce.classify("Can I get a pay rise?", rules, sections, fallback)["reason"] == "compensation"
    assert ce.classify("Where do I find the payment terms for a vendor?", rules, sections, fallback)["verdict"] == "escalate"
    assert ce.classify("Where do I find the payment terms for a vendor?", rules, sections, fallback)["reason"] == "policy_gap"


def test_rules_win_over_policy_coverage():
    rules, sections, fallback = fixtures()
    # "parental leave" is documented, but a medical question about it is not answered.
    result = ce.classify("My doctor signed me off during parental leave, what now?", rules, sections, fallback)
    assert result["verdict"] == "escalate"
    assert result["reason"] in {"medical_or_accommodation", "legal"}


def test_uncovered_question_escalates_as_policy_gap():
    rules, sections, fallback = fixtures()
    result = ce.classify("How many days of study leave do I get?", rules, sections, fallback)
    assert result == {"verdict": "escalate", "reason": "policy_gap", "policy": None, "matched": None}


def test_every_sample_question_meets_its_expectation():
    rules, sections, fallback = fixtures()
    questions = ce.read_yaml(ROOT / "sample_questions.yaml")["questions"]
    failed = [r for r in ce.score(questions, rules, sections, fallback) if not r["ok"]]
    assert not failed, failed


def test_every_policy_file_is_reachable():
    sections = ce.load_policies(ROOT / "policies")
    names = {s["file"] for s in sections}
    referenced = {q["policy"] for q in ce.read_yaml(ROOT / "sample_questions.yaml")["questions"] if q["expected"] == "answer"}
    assert referenced <= names
