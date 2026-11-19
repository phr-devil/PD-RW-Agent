"""Read-only H3 candidate review: value, novelty, identifiability, comparison.

The existing checks answer two different questions:

* ``staged_selection.review_early_choice`` validates a card's *shape* and the
  author's choice binding;
* ``decision.assess_proposal`` compares *probes* once competing hypotheses and
  predictions exist.

Neither looks at the candidate itself, so a card that says "important", "no
prior work", "F1 improves" and "windows as N" passes every structural check.
This module adds the missing cross-checks over a *declared* candidate card. It
reports the specific relation that is unstated, contradictory or
non-discriminating, and the cheapest check that would settle it.

It never scores, ranks, approves, rejects, stops or starts anything, and it
does not read literature, project files or Runs. Every finding is a statement
about the card's own text, not about the science.
"""
from __future__ import annotations

import re

from ..schemas import AgentError

CARD_VERSION = "pdrw-candidate-card-v1"
FORMS = frozenset({
    "ALGORITHM", "TRADITIONAL_METHOD", "MECHANISM", "LAW_BOUNDARY",
    "MEASUREMENT", "EVALUATION", "SYSTEM", "NEGATIVE_RESULT",
})
NEAREST_STATES = frozenset({"ACCESSED", "ABSTRACT_ONLY", "NOT_ACCESSED", "NONE_FOUND"})
TRUTH_KINDS = frozenset({
    "MEASURED_INSTRUMENT", "HUMAN_LABEL", "PROXY_FROM_INPUT",
    "MODEL_GENERATED", "SIMULATION_PARAMETER", "UNKNOWN",
})
SELF_REFERENTIAL_TRUTH = frozenset({"PROXY_FROM_INPUT", "MODEL_GENERATED"})
# Units that repeat the same physical subject many times. Counting them as N is
# the CASE-11 defect, not a rounding issue.
REPEATED_UNITS = frozenset({"WINDOW", "FRAME", "RECORD", "SEGMENT", "SAMPLE", "TOKEN"})
INDEPENDENT_UNITS = frozenset({"SUBJECT", "SESSION", "DEVICE", "BATCH", "SITE", "SPECIMEN"})
UNITS = REPEATED_UNITS | INDEPENDENT_UNITS
CARD_FIELDS = frozenset({
    "schema_version", "candidate_id", "question", "failure_premise",
    "contribution_form", "success_new_knowledge", "refutation_consequence",
    "named_nearest", "nearest_status", "competing_explanations", "falsifier",
    "truth_kind", "truth_source", "truth_independent_of_input",
    "prediction_time_inputs", "evaluation_unit", "independent_units",
    "reported_n", "confounders", "evidence_path", "confirmation_ref",
    "confirmation_shares_evaluation_data", "resources",
})
_ABSENCE = re.compile(
    r"(no prior|no existing|none found|no work|first to|"
    r"未检索到|未搜到|检索零命中|零命中|首次|尚无|没有人|没有任何工作|无具名)", re.I)
_REPLICATION = re.compile(
    r"(同一|相同|该|这一|same).{0,24}(关系|结论|效应|定律|机制|relation|effect|law|mechanism)"
    r".{0,20}(另一|其他|不同|another|other|different).{0,12}"
    r"(传感器|数据集|数据库|人群|设备|被试|sensor|dataset|cohort|device)"
    r".{0,16}(成立|复现|验证|适用|holds|replicat|general)", re.I)
_METRIC_ONLY = re.compile(
    r"(提升|改进|优于|超过|更高|SOTA|准确率|准确度|F1|MAE|RMSE|"
    r"improve|outperform|higher accuracy)", re.I)
_CONSEQUENCE = re.compile(
    r"(机制|边界|适用|何时|何类|规律|测量|能力|解释|上界|失效|"
    r"mechanism|boundary|\bconditions?\b|when|law|measurement|capability|"
    r"explain|upper bound|fails)", re.I)
_ILLEGAL_INPUT = re.compile(
    r"(测试(集)?真值|真实标签直接|oracle|未来(信息|标签)|"
    r"test[- ]time (truth|labels)|future information)", re.I)
_CHECK_ORDER = (
    "nearest_prior", "knowledge_gain", "truth_provenance", "evaluation_unit",
    "discrimination", "confirmation", "confounders", "legal_inputs",
)
_RULE = {
    "nearest_prior": "HIGH_VALUE_RESEARCH_DESIGN §A NAMED_NEAREST_ORIGINAL / SEARCH_DISCOVERY §4",
    "knowledge_gain": "HIGH_VALUE_RESEARCH_DESIGN §A UNANSWERED_KNOWLEDGE",
    "truth_provenance": "HIGH_VALUE_RESEARCH_DESIGN §B MEASUREMENT / CASE-10",
    "evaluation_unit": "HIGH_VALUE_RESEARCH_DESIGN §B INDEPENDENT_N / CASE-11",
    "discrimination": "HIGH_VALUE_RESEARCH_DESIGN §C DISTINCT_PREDICTIONS",
    "confirmation": "HIGH_VALUE_RESEARCH_DESIGN §B CONFIRMATION / CASE-20",
    "confounders": "HIGH_VALUE_RESEARCH_DESIGN §B CONFOUNDING",
    "legal_inputs": "HIGH_VALUE_RESEARCH_DESIGN §B LEGAL_INFO",
}
_PRECEDENT = {
    "NOVELTY_FROM_ABSENCE": ["CASE-14", "CASE-21"],
    "NEIGHBOR_UNVERIFIED": ["CASE-14"],
    "NEAREST_GAP_NOT_STATED": ["CASE-14"],
    "REPLICATION_ONLY": ["CASE-21"],
    "KNOWLEDGE_GAIN_IS_METRIC_ONLY": ["CASE-21", "CASE-13"],
    "TRUTH_NOT_INDEPENDENT": ["CASE-10"],
    "DECLARED_CONFLICT": ["CASE-10", "CASE-17"],
    "UNIT_NOT_INDEPENDENT": ["CASE-11"],
    "UNIT_COUNT_CONFLATION": ["CASE-11"],
    "NO_INDEPENDENT_CONTRAST": ["CASE-08", "CASE-17"],
    "NON_DISCRIMINATING": ["CASE-08", "CASE-17"],
    "STRONGEST_ALTERNATIVE_MISSING": ["CASE-08"],
    "ALTERNATIVES_NOT_DISTINCT": ["CASE-08"],
    "FALSIFIER_NOT_STATED": ["CASE-09"],
    "PREDICTION_NOT_STATED": ["CASE-08"],
    "CONFIRMATION_CIRCULAR": ["CASE-20"],
    "CONFIRMATION_NOT_PLANNED": ["CASE-20"],
    "CONFOUNDERS_NOT_STATED": ["CASE-10", "CASE-05"],
    "ILLEGAL_PREDICTION_INPUT": ["CASE-10", "CASE-12"],
}
_QUESTION = {
    "nearest_prior": ("Which single original paper is closest, what did it already prove, "
                      "and what exactly remains unproven?"),
    "knowledge_gain": ("If this succeeds, what does the field understand or decide differently "
                       "— and what changes if it is refuted?"),
    "truth_provenance": ("Which instrument or human protocol produces the target value, and is it "
                         "independent of the input signal used at prediction time?"),
    "evaluation_unit": ("What is one independent unit (subject/session/device/batch), and how many "
                        "of them support each condition?"),
    "discrimination": ("Which observable would differ between the strongest alternative and the "
                       "proposed explanation?"),
    "confirmation": ("Which data were never used for selection, tuning or evaluation, and can they "
                     "still be obtained?"),
    "confounders": ("Which device/subject/time/scene factors are bound to the condition, and which "
                    "of them could produce the same result?"),
    "legal_inputs": ("What is visible at prediction time, and does the declared input include "
                     "anything only available after the outcome?"),
}
_CHEAPEST = {
    "nearest_prior": "Read the closest paper's protocol table and write its remaining gap in one sentence.",
    "knowledge_gain": "Write the refutation consequence; if it is the same sentence, stop and reframe.",
    "truth_provenance": "Open the label/measurement record and name the instrument and protocol per label.",
    "evaluation_unit": "Count independent units per condition from the group column, not the row count.",
    "discrimination": "Write one observable whose predicted value differs between the two explanations.",
    "confirmation": "Name a group/session/device that was not used anywhere in selection or evaluation.",
    "confounders": "List the bound factors and mark each DESCRIPTIVELY_CROSSED or free.",
    "legal_inputs": "List the columns visible at prediction time and delete anything later.",
}


def _text(value, key: str, bound: int = 1200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentError("CANDIDATE_CARD_INVALID", f"{key}: non-empty bounded text required")
    if len(value) > bound:
        raise AgentError("CANDIDATE_CARD_INVALID", f"{key}: exceeds {bound} characters")
    return value.strip()


def _norm(value: str) -> str:
    return re.sub(r"[\s，。、；;,.()（）\[\]“”\"']+", "", value).lower()


def _validate(card) -> dict:
    if not isinstance(card, dict) or set(card) != CARD_FIELDS:
        raise AgentError("CANDIDATE_CARD_INVALID",
                         "Card fields are missing or unexpected for pdrw-candidate-card-v1")
    if card["schema_version"] != CARD_VERSION:
        raise AgentError("CANDIDATE_CARD_INVALID", "Unsupported candidate card version")
    _text(card["candidate_id"], "candidate_id", 80)
    for key in ("question", "failure_premise", "success_new_knowledge",
                "refutation_consequence", "truth_source", "prediction_time_inputs",
                "evidence_path", "confirmation_ref", "resources"):
        _text(card[key], key)
    if card["contribution_form"] not in FORMS:
        raise AgentError("CANDIDATE_CARD_INVALID", "Unknown contribution form")
    if card["nearest_status"] not in NEAREST_STATES:
        raise AgentError("CANDIDATE_CARD_INVALID", "Unknown nearest-prior status")
    if card["truth_kind"] not in TRUTH_KINDS:
        raise AgentError("CANDIDATE_CARD_INVALID", "Unknown truth kind")
    if card["evaluation_unit"] not in UNITS:
        raise AgentError("CANDIDATE_CARD_INVALID", "Unknown evaluation unit")
    nearest = card["named_nearest"]
    if not isinstance(nearest, list) or len(nearest) > 4:
        raise AgentError("CANDIDATE_CARD_INVALID", "named_nearest must be a list of at most four")
    for item in nearest:
        if not isinstance(item, dict) or set(item) != {"work", "covers", "remaining"}:
            raise AgentError("CANDIDATE_CARD_INVALID", "nearest entry needs work/covers/remaining")
        for key in item:
            if not isinstance(item[key], str) or len(item[key]) > 600:
                raise AgentError("CANDIDATE_CARD_INVALID", "nearest text must be bounded")
    competing = card["competing_explanations"]
    if not isinstance(competing, list) or len(competing) > 4:
        raise AgentError("CANDIDATE_CARD_INVALID", "Use at most four competing explanations")
    for item in competing:
        if not isinstance(item, dict) or set(item) != {"explanation", "predicted_observation"}:
            raise AgentError("CANDIDATE_CARD_INVALID", "explanation needs a predicted observation")
        for key in item:
            if not isinstance(item[key], str) or len(item[key]) > 600:
                raise AgentError("CANDIDATE_CARD_INVALID", "explanation text must be bounded")
    confounders = card["confounders"]
    if confounders != "NONE_AFTER_CHECK":
        if (not isinstance(confounders, list) or len(confounders) > 8
                or any(not isinstance(x, str) or not x.strip() or len(x) > 200 for x in confounders)):
            raise AgentError("CANDIDATE_CARD_INVALID",
                             "confounders must be a short list or the literal NONE_AFTER_CHECK")
    for key in ("independent_units", "reported_n"):
        value = card[key]
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)
                                  or not 0 <= value <= 10 ** 9):
            raise AgentError("CANDIDATE_CARD_INVALID", f"{key} must be a bounded integer or null")
    for key in ("truth_independent_of_input", "confirmation_shares_evaluation_data"):
        if not isinstance(card[key], bool) and card[key] is not None:
            raise AgentError("CANDIDATE_CARD_INVALID", f"{key} must be true/false/null")
    return card


def _check(card: dict, key: str) -> dict:
    """One declared-relation check. Returns state, findings and one question."""
    findings: list[str] = []
    state = "DECLARED"

    if key == "nearest_prior":
        nearest, status = card["named_nearest"], card["nearest_status"]
        if not nearest or status == "NONE_FOUND":
            findings.append("NOVELTY_FROM_ABSENCE")
            state = "UNVERIFIED"
        if status in {"NOT_ACCESSED", "ABSTRACT_ONLY"}:
            findings.append("NEIGHBOR_UNVERIFIED")
            state = "UNVERIFIED"
        gaps = [item for item in nearest if _ABSENCE.search(item["remaining"] + " " + item["work"])]
        if gaps:
            if "NOVELTY_FROM_ABSENCE" not in findings:
                findings.append("NOVELTY_FROM_ABSENCE")
            state = "UNVERIFIED"
        if nearest and all(_norm(item["covers"]) == _norm(item["remaining"])
                           or not item["remaining"].strip() for item in nearest):
            findings.append("NEAREST_GAP_NOT_STATED")
            state = "NOT_DECLARED" if state == "DECLARED" else state

    elif key == "knowledge_gain":
        knowledge = card["success_new_knowledge"]
        if _ABSENCE.search(knowledge):
            findings.append("NOVELTY_FROM_ABSENCE")
            state = "UNVERIFIED"
        if _REPLICATION.search(knowledge):
            findings.append("REPLICATION_ONLY")
            state = "DECLARED_CONFLICT"
        if _METRIC_ONLY.search(knowledge) and not _CONSEQUENCE.search(knowledge):
            findings.append("KNOWLEDGE_GAIN_IS_METRIC_ONLY")
            if state == "DECLARED":
                state = "NOT_DECLARED"

    elif key == "truth_provenance":
        kind, independent = card["truth_kind"], card["truth_independent_of_input"]
        if kind == "UNKNOWN" or independent is None:
            state = "NOT_DECLARED"
        elif kind in SELF_REFERENTIAL_TRUTH:
            findings.append("TRUTH_NOT_INDEPENDENT")
            state = "DECLARED_CONFLICT" if independent else "UNVERIFIED"
        elif not card["truth_source"].strip():
            findings.append("TRUTH_NOT_INDEPENDENT")
            state = "NOT_DECLARED"
        if kind in {"MEASURED_INSTRUMENT", "HUMAN_LABEL"} and re.search(
                r"(VLM|模型生成|伪标签|pseudo|self-supervised target|重建目标)", card["truth_source"]):
            findings.append("TRUTH_NOT_INDEPENDENT")
            state = "DECLARED_CONFLICT"

    elif key == "evaluation_unit":
        unit, units, reported = (card["evaluation_unit"], card["independent_units"],
                                 card["reported_n"])
        if units is None:
            state = "NOT_DECLARED"
        elif unit in REPEATED_UNITS:
            findings.append("UNIT_NOT_INDEPENDENT")
            state = "DECLARED_CONFLICT"
            if reported is not None and units == reported and units > 100:
                findings.append("UNIT_COUNT_CONFLATION")
        elif units < 2:
            findings.append("NO_INDEPENDENT_CONTRAST")
            state = "NOT_DECLARED"

    elif key == "discrimination":
        competing = card["competing_explanations"]
        if len(competing) < 2:
            findings.append("STRONGEST_ALTERNATIVE_MISSING")
            state = "NOT_DECLARED"
        observations = [_norm(x["predicted_observation"]) for x in competing]
        if any(not o for o in observations):
            findings.append("PREDICTION_NOT_STATED")
            state = "NOT_DECLARED" if state == "DECLARED" else state
        elif len(set(observations)) < len(observations):
            findings.append("NON_DISCRIMINATING")
            state = "DECLARED_CONFLICT"
        if len({_norm(x["explanation"]) for x in competing}) < len(competing):
            findings.append("ALTERNATIVES_NOT_DISTINCT")
            state = "DECLARED_CONFLICT"
        if not card["falsifier"].strip() or _norm(card["falsifier"]) in observations:
            findings.append("FALSIFIER_NOT_STATED")
            if state == "DECLARED":
                state = "NOT_DECLARED"

    elif key == "confirmation":
        if not card["confirmation_ref"].strip():
            findings.append("CONFIRMATION_NOT_PLANNED")
            state = "NOT_DECLARED"
        elif card["confirmation_shares_evaluation_data"] is True:
            findings.append("CONFIRMATION_CIRCULAR")
            state = "DECLARED_CONFLICT"
        elif card["confirmation_shares_evaluation_data"] is None:
            findings.append("CONFIRMATION_NOT_PLANNED")
            state = "UNVERIFIED"

    elif key == "confounders":
        if card["confounders"] != "NONE_AFTER_CHECK" and not card["confounders"]:
            findings.append("CONFOUNDERS_NOT_STATED")
            state = "NOT_DECLARED"

    elif key == "legal_inputs":
        if _ILLEGAL_INPUT.search(card["prediction_time_inputs"]):
            findings.append("ILLEGAL_PREDICTION_INPUT")
            state = "DECLARED_CONFLICT"

    return {
        "check": key,
        "state": state,
        "findings": findings,
        "rule": _RULE[key],
        "precedent": sorted({c for f in findings for c in _PRECEDENT.get(f, [])}),
        "question": _QUESTION[key] if findings else None,
        "cheapest_check": _CHEAPEST[key] if findings else None,
        "independently_verified": False,
    }


def review_candidate(card: dict) -> dict:
    """Review one declared card. Advisory; never a verdict on the science."""
    card = _validate(card)
    checks = [_check(card, key) for key in _CHECK_ORDER]
    blocking = [c for c in checks if c["findings"]]
    unknowns = [
        {
            "unknown_id": f"{card['candidate_id']}:{c['check']}",
            "question": c["question"],
            "cheapest_check": c["cheapest_check"],
        }
        for c in blocking
    ]
    return {
        "candidate_id": card["candidate_id"],
        "status": "CANDIDATE_REVIEW_ADVISORY",
        "checks": {c["check"]: c["state"] for c in checks},
        "findings": [
            {"check": c["check"], "codes": c["findings"],
             "rule": c["rule"], "precedent": c["precedent"]}
            for c in blocking
        ],
        "flags": sorted({f for c in blocking for f in c["findings"]}),
        "blocking_unknowns": unknowns,
        "next_cheapest_check": (unknowns[0]["cheapest_check"] if unknowns else
                                "NONE_IDENTIFIED — no declared relation was left unstated"),
        "clean_checks": [c["check"] for c in checks if not c["findings"]],
        "scientific_truth_verified": False,
    }


def review_candidates(cards: list[dict]) -> dict:
    """Review one to six candidates and compare their failure premises.

    The comparison reports duplication only. It never orders candidates by
    merit or produces a combined score.
    """
    if not isinstance(cards, list) or not 1 <= len(cards) <= 6:
        raise AgentError("CANDIDATE_CARD_INVALID", "Review one to six candidate cards")
    reviewed = [review_candidate(card) for card in cards]
    validated = [_validate(card) for card in cards]
    ids = [c["candidate_id"] for c in validated]
    if len(set(ids)) != len(ids):
        raise AgentError("CANDIDATE_CARD_INVALID", "Candidate IDs must be unique")
    premises: dict[str, list[str]] = {}
    questions: dict[str, list[str]] = {}
    for card in validated:
        premises.setdefault(_norm(card["failure_premise"]), []).append(card["candidate_id"])
        questions.setdefault(_norm(card["question"]), []).append(card["candidate_id"])
    shared = [group for group in premises.values() if len(group) > 1]
    duplicate_questions = [group for group in questions.values() if len(group) > 1]
    return {
        "status": "CANDIDATE_REVIEW_ADVISORY",
        "schema_version": CARD_VERSION,
        "candidates": reviewed,
        "cross_candidate": {
            "shared_failure_premise": shared,
            "duplicate_question": duplicate_questions,
            "distinct_failure_premises": len(premises),
            "note": ("Candidates sharing one failure premise are one option, not a comparison; "
                     "H3 requires genuinely different failure premises."),
            "options_are_ordered": False,
        },
        "score_provided": False,
        "scientific_truth_verified": False,
        "automatic_stop": False,
        "automatic_go": False,
        "model_invoked": False,
        "decision_authority": "PD-RW_WORKFLOW_AND_AUTHOR_ONLY",
        "guidance": ("Feed these questions back into HIGH_VALUE_RESEARCH_DESIGN / SEARCH_DISCOVERY. "
                     "A finding is a statement about the card's text, not about the science; "
                     "the author still chooses the question."),
    }
