"""Bounded, qualitative checks on declared research hypotheses and negative lessons.

Inputs are researcher/Agent proposals; this module does NOT attest their truth.
Scientific rules and actual Run evidence remain with PD-RW.
"""
from __future__ import annotations
import inspect
import re
from itertools import combinations
from ..schemas import AgentError
from .probe_frontier import summarize_declared_probe_frontier

OUTCOMES = {"INCREASE", "DECREASE", "NO_CHANGE", "UNKNOWN"}
COSTS = {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}
CHECKS = ("label_provenance", "group_independence", "legal_inputs",
          "evaluation_integrity", "metric_appropriateness", "effect_size")
CHECK_STATES = {"PASS", "FAIL", "UNKNOWN", "NOT_CHECKED"}
CLAIMS = {"CAPABILITY/PERFORMANCE", "MECHANISM/CAUSAL", "LAW/BOUNDARY"}
CLAIM_ALIASES = {
    "CAPABILITY": "CAPABILITY/PERFORMANCE",
    "MECHANISM": "MECHANISM/CAUSAL",
    "LAW": "LAW/BOUNDARY",
}
MAX_PROBES = 6

# A probe's reference condition is its baseline. Two ways that stops being a
# legal comparison: the reference needs information unavailable at prediction
# time (CASE-02/CASE-12 oracle), or the evaluation unit repeats one subject
# while group independence is declared PASS (CASE-11/EXT-X3).
_ILLEGAL_REFERENCE = re.compile(
    r"(oracle|测试(集)?真值|test[- ]time (truth|labels)|future (information|labels)|"
    r"dev_val 标签|未来信息)", re.I)
# Naming an oracle as a diagnostic next to a deployable arm is not using it as
# the comparison. Without this, "oracle upper bound and deployable arm" was
# flagged illegal and a lawful decisive probe disappeared from the frontier.
_DIAGNOSTIC_ARM = re.compile(
    r"((oracle|diagnostic)\s+(upper\s+bound|ceiling)|诊断上界)", re.I)
_REPEATED_UNIT = frozenset({"WINDOW", "FRAME", "RECORD", "SEGMENT", "TOKEN", "ROW", "EPISODE"})
_PROBE_RULE = {
    "REFERENCE_NOT_LEGAL": "ALGORITHM_ENGINEERING §1 BASELINE / CASE-02",
    "PROBE_UNIT_NOT_INDEPENDENT": "HIGH_VALUE_RESEARCH_DESIGN §B INDEPENDENT_N / CASE-11",
    "EXECUTION_DECLARED_NOT_VERIFIED": "SCIENCE_RESULT_HARVEST §RUN_EVIDENCE / CASE-20",
    "EXECUTION_STATUS_CONFLICT": "SCIENCE_RESULT_HARVEST §RUN_EVIDENCE / CASE-20",
    "CLOSURE_PREMISE_UNBOUND": "RESEARCH_RECORD §EXP_PREMISE / CASE-20",
    "CLOSURE_PREMISE_CONTRADICTED": "RESEARCH_RECORD §EXP_PREMISE / CASE-20",
    "CLOSURE_PLAN_UNRESOLVED": "RESEARCH_RECORD §EXP_PREMISE / CASE-20",
}
_PROBE_PRECEDENT = {
    "REFERENCE_NOT_LEGAL": ["CASE-02", "CASE-12"],
    "PROBE_UNIT_NOT_INDEPENDENT": ["CASE-11", "EXT-X3"],
    "EXECUTION_DECLARED_NOT_VERIFIED": ["CASE-20", "CASE-21"],
    "EXECUTION_STATUS_CONFLICT": ["CASE-20", "CASE-21"],
    "CLOSURE_PREMISE_UNBOUND": ["CASE-20", "CASE-21"],
    "CLOSURE_PREMISE_CONTRADICTED": ["CASE-20", "CASE-21"],
    "CLOSURE_PLAN_UNRESOLVED": ["CASE-20", "CASE-21"],
}
_PROBE_QUESTION = {
    "REFERENCE_NOT_LEGAL": "Which reference is legal at prediction time, and does it exist already?",
    "PROBE_UNIT_NOT_INDEPENDENT": "How many independent units (not windows) does this probe compare?",
    "EXECUTION_DECLARED_NOT_VERIFIED": (
        "Which Run or record proves this probe already ran under this premise?"),
    "EXECUTION_STATUS_CONFLICT": (
        "The cited Run and the declaration disagree about whether it ran; which is right?"),
    "CLOSURE_PREMISE_UNBOUND": (
        "Under which premise was this experiment run? Without one it closes nothing."),
    "CLOSURE_PREMISE_CONTRADICTED": (
        "The cited Run executed another premise or plan. Which experiment did it answer, "
        "and is this probe that experiment or a new one?"),
    "CLOSURE_PLAN_UNRESOLVED": (
        "The Run names a frozen plan that cannot be read here; which plan did it execute?"),
}
# What the probe may still be used for. A test-time-truth reference is a
# legitimate diagnostic upper bound and an illegitimate decisive comparison;
# an unresolved unit question asks for a count, not for a ban on the metric;
# an unverifiable closure is a record to check, not a reason to rerun.
_PROBE_USAGE = {
    "REFERENCE_NOT_LEGAL": "DIAGNOSTIC_UPPER_BOUND_ONLY",
    "PROBE_UNIT_NOT_INDEPENDENT": "VERIFY_INDEPENDENT_UNITS_FIRST",
    "EXECUTION_DECLARED_NOT_VERIFIED": "DO_NOT_TREAT_AS_CLOSED_OR_AS_NEW",
    "EXECUTION_STATUS_CONFLICT": "DO_NOT_TREAT_AS_CLOSED_OR_AS_NEW",
    "CLOSURE_PREMISE_UNBOUND": "BIND_PREMISE_BEFORE_RELYING_ON_IT",
    "CLOSURE_PREMISE_CONTRADICTED": "DO_NOT_TREAT_AS_CLOSED_OR_AS_NEW",
    "CLOSURE_PLAN_UNRESOLVED": "VERIFY_FROZEN_PLAN_BEFORE_RELYING_ON_IT",
}

# Not "run it again": if this probe *is* the experiment that Run executed, it is
# closed there. Confirm which experiment was answered before spending anything.
_CONTRADICTION_NEXT_ACTION = "CONFIRM_WHICH_EXPERIMENT_THE_RUN_ANSWERED"

_DISQUALIFYING_FROM_FRONTIER = frozenset({"REFERENCE_NOT_LEGAL"})

# CASE-20/CASE-21: an experiment that already answered this premise cannot
# answer it again. The declared execution state decides what the next action is,
# and a state without a Run reference stays a claim, never a verified closure.
EXECUTION_STATUSES = {"NOT_EXECUTED", "COMPLETED_VALID", "COMPLETED_INVALID",
                      "INCONCLUSIVE", "BLOCKED"}
PRIOR_EXECUTION_FIELDS = {"status", "run_ref", "record_ref", "premise_ref",
                          "premise_id", "conclusion", "new_information",
                          "requires_new_authorization"}
_PRIOR_EXECUTION_FIELDS = PRIOR_EXECUTION_FIELDS
_MAX_PRIOR_TEXT = 240

# The next action each declared state implies. Nothing here runs, stops, or
# approves anything: it names what would have to be true before a rerun.
_NEXT_ACTION = {
    "NOT_YET_RUN": "RUN_IF_LEGAL_AND_DISCRIMINATING",
    "NEEDS_AUTHORIZATION": "OBTAIN_AUTHORIZATION_FIRST",
    "HISTORICAL_EVIDENCE_ONLY": "KEEP_AS_RECORDED_EVIDENCE_DO_NOT_RERUN",
    # Same action, different epistemic footing: cite it and say that the premise
    # link is the caller's declaration rather than the record's.
    "HISTORICAL_EVIDENCE_PREMISE_ASSUMED":
        "CITE_AS_EVIDENCE_ONLY_AND_DECLARE_THE_PREMISE_LINK",
    "CLOSURE_DECLARED_NOT_VERIFIED": "VERIFY_RUN_BEFORE_DECIDING",
    "TARGETED_REPAIR": "REPAIR_NAMED_DEFECT_FIRST",
    "REVISIT_ON_NEW_INFORMATION": "REVISIT_ONLY_IF_NEW_INFORMATION_CHANGES_JUDGMENT",
    "AWAIT_NEW_INFORMATION": "HOLD_UNTIL_NEW_INFORMATION_EXISTS",
    "BLOCKER_UNRESOLVED": "RESOLVE_BLOCKER_FIRST",
    "CLOSURE_PREMISE_UNBOUND": "BIND_PREMISE_ID_BEFORE_TREATING_AS_CLOSED",
    "STATUS_CONFLICT": "RESOLVE_RUN_STATUS_CONFLICT_FIRST",
}

# A Run record uses its own vocabulary ("COMPLETED", "VALID", "PARTIAL"...). The
# comparison below is deliberately coarse: it can only say that the declared
# state and the record agree, disagree, or cannot be compared.
_VALID_RUN_TERMS = frozenset({"VALID", "COMPLETED", "SUCCESS", "SUCCEEDED", "DONE", "PASSED"})
_INVALID_RUN_TERMS = frozenset({"INVALID", "PARTIAL", "CRASH", "CRASHED", "FAILED", "FAILURE",
                                "ERROR", "NOT_RUN", "ABORTED", "RESTRICTED"})
_INCONCLUSIVE_RUN_TERMS = frozenset({"INCONCLUSIVE", "UNDECIDED"})


def _term_is(term: str, terms: frozenset) -> bool:
    return term in terms or any(term.startswith(t + "_") for t in terms)


def _status_consistency(declared_status: str, binding: dict | None) -> str:
    """Compare a declared execution state with the Run's own record.

    CONSISTENT means the two agree. CONFLICT means the record contradicts the
    declaration -- an "invalid" attempt declared as a valid closure, the reverse,
    a directory holding another Run's record, or a plan whose bytes are not the
    bytes the record names. UNKNOWN covers everything else, including "no record
    was read".
    """
    if not binding or binding.get("status") != "RUN_RECORD_BOUND":
        return "UNKNOWN"
    if binding.get("run_id_consistency") == "MISMATCH":
        return "CONFLICT"
    if (binding.get("plan") or {}).get("hash_match") is False:
        return "CONFLICT"
    term = str(binding.get("run_status_declared") or "").strip().upper()
    verdict = str(binding.get("verdict_declared") or "").strip().upper()
    anchor_failed = binding.get("anchor_pass_declared") is False
    invalid = _term_is(term, _INVALID_RUN_TERMS) or verdict.startswith("INVALID")
    if declared_status == "COMPLETED_VALID":
        if invalid or anchor_failed:
            return "CONFLICT"
        return "CONSISTENT" if _term_is(term, _VALID_RUN_TERMS) else "UNKNOWN"
    if declared_status == "COMPLETED_INVALID":
        if invalid:
            return "CONSISTENT"
        return "CONFLICT" if _term_is(term, _VALID_RUN_TERMS) else "UNKNOWN"
    if declared_status == "INCONCLUSIVE":
        if _term_is(term, _INCONCLUSIVE_RUN_TERMS) or "INCONCLUSIVE" in verdict:
            return "CONSISTENT"
        return "CONFLICT" if invalid else "UNKNOWN"
    return "UNKNOWN"


def _binding_echo(binding: dict | None) -> dict | None:
    """A bounded echo of the binding receipt; never the whole record."""
    if binding is None:
        return None
    return {
        "status": binding.get("status"),
        "reason": binding.get("reason"),
        "run_dir": binding.get("run_dir"),
        "record_ref": binding.get("record_ref"),
        "record_sha256": binding.get("record_sha256"),
        "run_id_declared": binding.get("run_id_declared"),
        "run_id_expected": binding.get("run_id_expected"),
        "run_id_consistency": binding.get("run_id_consistency"),
        "record_structure": binding.get("record_structure"),
        "premise_id_recorded": binding.get("premise_id_recorded"),
        "plan": binding.get("plan"),
        "premise_plan": binding.get("premise_plan"),
        "premise_plan_match": binding.get("premise_plan_match"),
        "artifact_links_verified": binding.get("artifact_links_verified"),
        "run_status_declared": binding.get("run_status_declared"),
        "verdict_declared": binding.get("verdict_declared"),
        "anchor_pass_declared": binding.get("anchor_pass_declared"),
    }


def _invoke_binder(binder, ref, record_ref, premise_ref):
    """Pass the optional references when the binder accepts them.

    Custom binders written against 0.9.11 take one argument. Refusing to call
    them would turn a schema addition into a breaking change.
    """
    try:
        params = inspect.signature(binder).parameters
        flexible = any(p.kind is p.VAR_KEYWORD for p in params.values())
    except (TypeError, ValueError):
        flexible = False
    if flexible or "premise_ref" in params:
        return binder(ref, record_ref=record_ref, premise_ref=premise_ref)
    return binder(ref)


def _prior_execution(value, premise_id: str, binder=None) -> dict:
    """Read the declared execution state of one probe without trusting it.

    Absent means "not run", which is the only reading that keeps old packets
    valid. When a project root is available the cited reference is resolved to
    Run bytes (`binder`) and six questions are answered separately:

    * is a reference declared at all (`reference_present`);
    * did it resolve to a Run record inside this project (`file_binding`);
    * is that record the Run it claims to be (`run_identity`: record id against
      the directory, structure rather than a bare metrics file);
    * does that record's own status agree with the declaration
      (`status_consistency`);
    * did it execute *this* premise's frozen plan (`premise_binding` with
      `premise_binding_basis`);
    * therefore, is the closure trustworthy (`status_verified`).

    Only the last one is an inference, and it needs all of the others. The
    premise question is deliberately not answered by comparing two strings the
    caller wrote: the record's own premise, or the premise of the plan the
    record names, has to disagree for a citation to be contradicted.
    """
    if value is None:
        return {
            "declared_status": "NOT_EXECUTED",
            "run_ref": None,
            "reference_present": False,
            "file_binding": "NOT_CHECKED",
            "status_consistency": "UNKNOWN",
            "premise_binding": "NOT_APPLICABLE",
            "premise_binding_basis": None,
            "premise_evidence": "NONE",
            "premise_verified": False,
            "premise_contradicted": False,
            "plan_unresolved": False,
            "status_verified": False,
            "binding_checked": False,
            "premise_match": None,
            "history_applicable": False,
            "requires_new_authorization": False,
            "authorization_basis": "CALLER_DECLARED_ONLY",
            "new_information_declared": False,
            "applicability": "NOT_YET_RUN",
            "next_action": _NEXT_ACTION["NOT_YET_RUN"],
            "run_binding": None,
        }
    if not isinstance(value, dict) or set(value) - _PRIOR_EXECUTION_FIELDS:
        raise AgentError("SCIENCE_PACKET_INVALID",
                         "prior_execution accepts only declared execution fields")
    status = value.get("status", "NOT_EXECUTED")
    if not isinstance(status, str) or status not in EXECUTION_STATUSES:
        raise AgentError("SCIENCE_PACKET_INVALID", "Unsupported declared execution status")
    texts = {}
    for key in ("run_ref", "record_ref", "premise_ref", "conclusion", "new_information"):
        item = value.get(key)
        if item is None:
            texts[key] = None
            continue
        if not isinstance(item, str) or not item.strip() or len(item) > _MAX_PRIOR_TEXT:
            raise AgentError("SCIENCE_PACKET_INVALID", f"prior_execution.{key} must be bounded text")
        texts[key] = item
    prior_premise = value.get("premise_id")
    if prior_premise is not None:
        _id(prior_premise, "prior_execution.premise_id")
    needs_auth = value.get("requires_new_authorization", False)
    if not isinstance(needs_auth, bool):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         "requires_new_authorization must be boolean")

    reference_present = bool(texts["run_ref"])
    binding = None
    if reference_present and binder is not None:
        try:
            binding = _invoke_binder(binder, texts["run_ref"], texts["record_ref"],
                                     texts["premise_ref"])
        except AgentError as exc:
            binding = {"status": "BINDING_ERROR", "reason": exc.code,
                       "run_ref": texts["run_ref"]}
    file_binding = "NOT_CHECKED"
    if binding is not None:
        file_binding = ("BOUND" if binding.get("status") == "RUN_RECORD_BOUND"
                        else "UNRESOLVED")
    consistency = _status_consistency(status, binding)
    plan = (binding or {}).get("plan") or {}
    recorded_premise = ((binding or {}).get("premise_id_recorded")
                        or plan.get("premise_id"))
    premise_plan_mismatch = (binding or {}).get("premise_plan_match") is False
    plan_declared = plan.get("plan_status") not in (None, "NOT_DECLARED")
    plan_unresolved = bool(plan_declared and plan.get("plan_status") != "BOUND")
    if status == "NOT_EXECUTED":
        premise_binding, premise_basis = "NOT_APPLICABLE", None
    elif prior_premise is None:
        premise_binding, premise_basis = "UNBOUND", None
    elif prior_premise.strip().casefold() != premise_id.strip().casefold():
        # The caller already says the closure concerns another premise. No file
        # is needed to see that, and no record can turn it into this one.
        premise_binding, premise_basis = "MISMATCH", "CALLER_DECLARATION"
    elif premise_plan_mismatch:
        # The caller said which plan encodes this premise; the cited Run
        # executed another one.
        premise_binding, premise_basis = "MISMATCH", "PREMISE_PLAN"
    elif recorded_premise:
        same = recorded_premise.strip().casefold() == prior_premise.strip().casefold()
        premise_binding = "MATCH" if same else "MISMATCH"
        premise_basis = ("RUN_RECORD" if (binding or {}).get("premise_id_recorded")
                         else "FROZEN_PLAN")
    else:
        # Nothing on disk speaks to the premise: the attribution is a label the
        # caller wrote twice. Kept, and labelled as such.
        premise_binding, premise_basis = "MATCH", "CALLER_DECLARATION"
    contradicted = (premise_binding == "MISMATCH"
                    and premise_basis in {"RUN_RECORD", "FROZEN_PLAN", "PREMISE_PLAN"})
    premise_verified = (premise_binding == "MATCH"
                        and premise_basis in {"RUN_RECORD", "FROZEN_PLAN"})
    if (binding or {}).get("premise_id_recorded"):
        premise_evidence = "RUN_RECORD"
    elif plan.get("premise_id"):
        premise_evidence = "FROZEN_PLAN"
    elif plan.get("plan_status") == "BOUND":
        premise_evidence = "FROZEN_PLAN_WITHOUT_PREMISE"
    else:
        premise_evidence = "NONE"
    # Two different questions, two different answers. `execution_verified` says
    # the cited Run ran as declared. `premise_verified` says something on disk --
    # not the caller's own label repeated twice -- places that Run under this
    # premise. A closure needs both; a Run that ran is evidence either way, which
    # is why the action below does not fall back to "run it again".
    execution_verified = (status == "COMPLETED_VALID" and reference_present
                          and file_binding == "BOUND" and consistency == "CONSISTENT"
                          and not contradicted)
    closure_verified = execution_verified and premise_verified and not plan_unresolved

    if status == "NOT_EXECUTED":
        applicability = "NEEDS_AUTHORIZATION" if needs_auth else "NOT_YET_RUN"
    elif consistency == "CONFLICT":
        # The record contradicts the citation about what ran: until that is
        # resolved it is not evidence about this probe, and the probe is not a
        # free new experiment either.
        applicability = "STATUS_CONFLICT"
    elif premise_binding == "MISMATCH":
        applicability = "NOT_YET_RUN"
    elif premise_binding == "UNBOUND":
        # Running it again would be waste; calling it closed would let an
        # unbound claim remove a live candidate. Neither is allowed.
        applicability = "CLOSURE_PREMISE_UNBOUND"
    elif status == "COMPLETED_VALID":
        if closure_verified:
            applicability = "HISTORICAL_EVIDENCE_ONLY"
        elif plan_unresolved:
            applicability = "CLOSURE_DECLARED_NOT_VERIFIED"
        elif execution_verified and premise_binding == "MATCH":
            # The Run is real and ran as declared; the premise it tested is a
            # label the caller wrote. Recorded evidence, not a settled premise.
            applicability = "HISTORICAL_EVIDENCE_PREMISE_ASSUMED"
        else:
            applicability = "CLOSURE_DECLARED_NOT_VERIFIED"
    elif status == "COMPLETED_INVALID":
        applicability = "TARGETED_REPAIR"
    elif status == "INCONCLUSIVE":
        applicability = ("REVISIT_ON_NEW_INFORMATION" if texts["new_information"]
                         else "AWAIT_NEW_INFORMATION")
    else:
        applicability = "BLOCKER_UNRESOLVED"
    return {
        "declared_status": status,
        "run_ref": texts["run_ref"],
        "reference_present": reference_present,
        "file_binding": file_binding,
        "status_consistency": consistency,
        "premise_binding": premise_binding,
        # How the premise question was answered: the Run's own record, the
        # frozen plan it names, the caller's plan reference, or nothing.
        "premise_binding_basis": premise_basis,
        "premise_evidence": premise_evidence,
        "premise_verified": premise_verified,
        "premise_contradicted": contradicted,
        "plan_unresolved": plan_unresolved,
        # Did the cited Run run as declared? Independent of what premise it
        # tested, and of whether this probe is closed.
        "execution_verified": execution_verified,
        # Kept for compatibility; now it means what its name says -- the closure
        # is verified -- so it can never be true while `premise_verified` is
        # false. Before 0.9.13 the two could disagree, and the label
        # HISTORICAL_EVIDENCE_ONLY hid which half was missing.
        "status_verified": closure_verified,
        "closure_verified": closure_verified,
        "binding_checked": binding is not None,
        "premise_match": None if premise_binding in {"UNBOUND", "NOT_APPLICABLE"}
                        else premise_binding == "MATCH",
        "history_applicable": premise_binding == "MATCH" and status != "NOT_EXECUTED",
        "requires_new_authorization": needs_auth,
        # A declared boolean is a caller statement, never an execution permit.
        "authorization_basis": "CALLER_DECLARED_ONLY",
        "new_information_declared": bool(texts["new_information"]),
        "applicability": applicability,
        # A probe whose citation turned out to be another experiment is runnable,
        # but "run it" is the wrong instruction until the identity is settled.
        "next_action": (_CONTRADICTION_NEXT_ACTION
                        if contradicted and applicability == "NOT_YET_RUN"
                        else _NEXT_ACTION[applicability]),
        "run_binding": _binding_echo(binding),
    }


# An identifier is a key: 80 characters is already generous. A *description*
# (what is observed, what it is compared against) is read by a human and echoed
# by the checker, so it gets the same room as any other declared text -- the old
# 80-character limit on those two fields produced ten of the thirteen shape
# violations in one real packet without protecting anything.
_ID_LIMIT = 80
_DESCRIPTION_LIMIT = 240


def _id(value, label: str, limit: int = _ID_LIMIT) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"{label}: expected 1..{limit} characters of text, got "
                         f"{type(value).__name__}")
    if len(value) > limit:
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"{label}: {len(value)} characters > {limit}; use a short token, "
                         "the prose belongs in the report")
    return value


def _refs(value, label: str, limit: int = 8) -> list[str]:
    if not isinstance(value, list) or len(value) > limit or any(
        not isinstance(x, str) or not x.strip() or len(x) > 240 for x in value
    ):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"{label}: expected a list of at most {limit} source "
                         f"identifiers (<=240 characters each), got "
                         f"{type(value).__name__}")
    return value


def _scope(value) -> dict[str, str]:
    if not isinstance(value, dict):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"scope: expected a mapping of at most 12 keys to short "
                         f"string values, got {type(value).__name__}")
    for key, item in value.items():
        if not isinstance(key, str) or not key or len(key) > 60:
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"scope: key {key!r} must be 1..60 characters")
        if not isinstance(item, str) or not item.strip():
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"scope.{key}: expected a non-empty string value")
        if len(item) > 160:
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"scope.{key}: {len(item)} characters > 160; keep the "
                             "boundary here and the argument in the report")
    if len(value) > 12:
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"scope: {len(value)} keys > 12")
    return value


def assess_proposal(packet: dict, *, project_root=None, run_binder=None) -> dict:
    """Report discriminability, unresolved evidence and premise similarity.

    `project_root` (optional) makes declared execution claims checkable: a cited
    Run reference is resolved to a record inside that project by the existing
    read-only binder. Without it every closure stays `file_binding:
    NOT_CHECKED`, which is the same answer as "not verified" -- never "true".

    This does not rank candidates by scientific merit, infer numerical
    probabilities, or authorize any action. No permanent memory is written.
    """
    binder = run_binder
    if binder is None and project_root is not None:
        from .feedback_link import bind_run_reference  # local: keeps import graph flat

        def binder(ref, record_ref=None, premise_ref=None):
            return bind_run_reference(project_root, ref, record_ref, premise_ref)
    if not isinstance(packet, dict):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"$: expected one JSON object, got {type(packet).__name__}")
    raw_type = packet.get("claim_type")
    if not isinstance(raw_type, str):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"claim_type: expected text, got {type(raw_type).__name__}; "
                         f"accepted: {', '.join(sorted(CLAIMS))}")
    claim_type = CLAIM_ALIASES.get(raw_type, raw_type)
    if claim_type not in CLAIMS:
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"claim_type: {raw_type!r} is not a claim type; "
                         f"accepted: {', '.join(sorted(CLAIMS))}")
    question = packet.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise AgentError("SCIENCE_PACKET_INVALID",
                         "question: expected 1..1000 characters of text")
    claim_refs = _refs(packet.get("claim_evidence_refs", []), "claim_evidence_refs")
    hypotheses = packet.get("hypotheses", [])
    if not isinstance(hypotheses, list) or not 2 <= len(hypotheses) <= 6:
        count = len(hypotheses) if isinstance(hypotheses, list) else type(hypotheses).__name__
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"hypotheses: expected a list of 2..6 IDs, got {count}")
    ids = [_id(x, "hypothesis ID") for x in hypotheses]
    if len(set(ids)) != len(ids):
        raise AgentError("SCIENCE_PACKET_INVALID", "hypotheses: IDs must be distinct")
    proposed = packet.get("proposed_premise", {})
    if not isinstance(proposed, dict):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"proposed_premise: expected an object, got {type(proposed).__name__}")
    premise_id = _id(proposed.get("premise_id"), "premise_id")
    scope = _scope(proposed.get("scope", {}))
    if not scope:
        raise AgentError("SCIENCE_PACKET_INVALID",
                         "proposed_premise.scope: expected at least one key")

    checks = packet.get("prechecks", {})
    if not isinstance(checks, dict):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"prechecks: expected a mapping keyed by check name, got "
                         f"{type(checks).__name__} of {len(checks)}; accepted: "
                         + ", ".join(CHECKS))
    if set(checks) - set(CHECKS):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         "prechecks: unknown check name(s) "
                         f"{', '.join(sorted(set(checks) - set(CHECKS)))}; accepted: "
                         + ", ".join(CHECKS))
    prechecks = {}
    for key in CHECKS:
        entry = checks.get(key, {"status": "NOT_CHECKED", "evidence_refs": []})
        if not isinstance(entry, dict) or not isinstance(entry.get("status"), str) or entry["status"] not in CHECK_STATES:
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"prechecks.{key}.status: expected one of "
                             + ", ".join(sorted(CHECK_STATES)))
        refs = _refs(entry.get("evidence_refs", []), key)
        prechecks[key] = {
            "declared_status": entry["status"],
            "evidence_refs": refs,
            "review": ("SOURCE_REQUIRED" if entry["status"] == "PASS" and not refs
                       else "DECLARED_RISK" if entry["status"] == "FAIL"
                       else "SOURCE_NOT_VERIFIED" if refs
                       else "UNKNOWN_OR_UNCHECKED"),
            "independently_verified": False,
        }

    lessons = packet.get("prior_negative_lessons", [])
    if not isinstance(lessons, list) or len(lessons) > 10:
        raise AgentError("SCIENCE_PACKET_INVALID", "At most ten prior negative lessons")
    negative_candidates = []
    for lesson in lessons:
        if not isinstance(lesson, dict):
            raise AgentError("SCIENCE_PACKET_INVALID", "Negative lessons must be objects")
        old_id = _id(lesson.get("premise_id"), "prior premise ID")
        old_scope = _scope(lesson.get("scope", {}))
        refs = _refs(lesson.get("evidence_refs", []), "negative evidence refs")
        validity = lesson.get("validity")
        if not isinstance(validity, str) or validity not in {"VALID_NEGATIVE", "INVALID", "UNKNOWN"}:
            raise AgentError("SCIENCE_PACKET_INVALID", "Negative lesson validity must be explicit")
        if old_id != premise_id:
            continue
        category = ("DECLARED_SAME_PREMISE_SCOPE_CANDIDATE"
                    if old_scope == scope and validity == "VALID_NEGATIVE" and refs
                    else "SCOPE_DIFFERS_REVIEW"
                    if old_scope != scope
                    else "NEGATIVE_EVIDENCE_INSUFFICIENT")
        negative_candidates.append({
            "premise_id": old_id, "status": category,
            "prior_validity_declared": validity,
            "evidence_refs": refs, "scientific_equivalence_verified": False,
            "automatic_stop": False,
        })

    # A verified-looking *declared* success is not a universally applicable
    # mechanism or automatic GO. Only exact premise/scope yields an advisory
    # candidate; actual Run evidence and scientific transfer need review.
    positive_lessons = packet.get("prior_positive_lessons", [])
    if not isinstance(positive_lessons, list) or len(positive_lessons) > 10:
        raise AgentError("SCIENCE_PACKET_INVALID", "At most ten prior positive lessons")
    positive_candidates = []
    for lesson in positive_lessons:
        if not isinstance(lesson, dict):
            raise AgentError("SCIENCE_PACKET_INVALID", "Positive lessons must be objects")
        old_id = _id(lesson.get("premise_id"), "prior positive premise ID")
        old_scope = _scope(lesson.get("scope", {}))
        refs = _refs(lesson.get("evidence_refs", []), "positive evidence refs")
        validity = lesson.get("validity")
        if not isinstance(validity, str) or validity not in {"VALID_POSITIVE", "INVALID", "UNKNOWN"}:
            raise AgentError("SCIENCE_PACKET_INVALID", "Positive lesson validity must be explicit")
        if old_id != premise_id:
            continue
        category = ("DECLARED_SAME_PREMISE_SCOPE_POSITIVE_CANDIDATE"
                    if old_scope == scope and validity == "VALID_POSITIVE" and refs
                    else "SCOPE_DIFFERS_REVIEW" if old_scope != scope
                    else "POSITIVE_EVIDENCE_INSUFFICIENT")
        positive_candidates.append({
            "premise_id": old_id, "status": category,
            "prior_validity_declared": validity,
            "evidence_refs": refs, "scientific_equivalence_verified": False,
            "automatic_go": False,
        })

    probes = packet.get("probes", [])
    if not isinstance(probes, list) or not 1 <= len(probes) <= MAX_PROBES:
        count = len(probes) if isinstance(probes, list) else type(probes).__name__
        raise AgentError("SCIENCE_PACKET_INVALID",
                         f"probes: expected a list of 1..{MAX_PROBES}, got {count}")
    summaries = []
    probe_findings = []
    repeated_unit_probes = []
    seen = set()
    for probe in probes:
        if not isinstance(probe, dict):
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"probes[{len(seen)}]: expected a probe object, got "
                             f"{type(probe).__name__}")
        pid = _id(probe.get("id"), f"probes[{len(seen)}].id")
        if pid in seen:
            raise AgentError("SCIENCE_PACKET_INVALID", f"probes.id: {pid!r} is used twice")
        seen.add(pid)
        # All competing hypotheses must predict the same observable,
        # evaluation unit and reference condition. No metric is invented.
        observable = _id(probe.get("observable"), "probe observable", _DESCRIPTION_LIMIT)
        evaluation_unit = _id(probe.get("evaluation_unit"), "evaluation_unit")
        comparison_reference = _id(probe.get("comparison_reference"),
                                   "comparison_reference", _DESCRIPTION_LIMIT)
        predictions = probe.get("predictions")
        if not isinstance(predictions, dict):
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"probe {pid}.predictions: expected a mapping of hypothesis "
                             f"ID to outcome, got {type(predictions).__name__}")
        if set(predictions) - set(ids):
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"probe {pid}.predictions: unknown hypothesis "
                             f"{', '.join(sorted(set(predictions) - set(ids)))}; "
                             "keys must be declared in hypotheses")
        if any(not isinstance(v, str) or v not in OUTCOMES for v in predictions.values()):
            bad = sorted({str(v) for v in predictions.values()
                          if not isinstance(v, str) or v not in OUTCOMES})
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"probe {pid}.predictions: {', '.join(bad)} not in "
                             f"{', '.join(sorted(OUTCOMES))}")
        cost = probe.get("cost_band", "UNKNOWN")
        if not isinstance(cost, str) or cost not in COSTS:
            raise AgentError("SCIENCE_PACKET_INVALID",
                             f"probe {pid}.cost_band: {cost!r} not in "
                             f"{', '.join(sorted(COSTS))}")
        refs = _refs(probe.get("prediction_evidence_refs", []), "probe evidence refs")
        separated = []
        for a, b in combinations(ids, 2):
            pa, pb = predictions.get(a, "UNKNOWN"), predictions.get(b, "UNKNOWN")
            if pa != "UNKNOWN" and pb != "UNKNOWN" and pa != pb:
                separated.append([a, b])
        # Declaration-level contradictions only: no file is read and nothing is
        # promoted. A probe whose reference needs test-time truth, or whose unit
        # repeats one subject while group independence is declared PASS, is not
        # a clean comparison even if it separates every hypothesis pair.
        findings = []
        if _ILLEGAL_REFERENCE.search(_DIAGNOSTIC_ARM.sub(" ", comparison_reference)):
            findings.append("REFERENCE_NOT_LEGAL")
        if evaluation_unit.strip().upper() in _REPEATED_UNIT:
            if prechecks["group_independence"]["declared_status"] == "PASS":
                repeated_unit_probes.append(pid)
                findings.append("PROBE_UNIT_NOT_INDEPENDENT")
        # A claimed closure that cannot be traced to a Run under this premise is
        # a record to check, not a finished experiment and not a free rerun
        # (CASE-20). A contradicting record is a different question again.
        prior = _prior_execution(probe.get("prior_execution"), premise_id, binder)
        # The cited Run executed another premise or another frozen plan: this
        # experiment is still unanswered, whatever the packet's labels say. When
        # the record is not even the cited Run, the identity conflict speaks
        # first and its premise is not evidence about anything.
        if prior["premise_contradicted"] and prior["status_consistency"] != "CONFLICT":
            findings.append("CLOSURE_PREMISE_CONTRADICTED")
        if prior["applicability"] == "CLOSURE_DECLARED_NOT_VERIFIED":
            findings.append("CLOSURE_PLAN_UNRESOLVED" if prior["plan_unresolved"]
                            else "EXECUTION_DECLARED_NOT_VERIFIED")
        elif prior["applicability"] == "CLOSURE_PREMISE_UNBOUND":
            findings.append("CLOSURE_PREMISE_UNBOUND")
        elif prior["applicability"] == "STATUS_CONFLICT":
            findings.append("EXECUTION_STATUS_CONFLICT")
        if findings:
            probe_findings.append({
                "probe_id": pid,
                "codes": findings,
                "rules": [_PROBE_RULE[code] for code in findings],
                "precedent": sorted({c for code in findings for c in _PROBE_PRECEDENT[code]}),
                "questions": [_PROBE_QUESTION[code] for code in findings],
                "usage": [_PROBE_USAGE[code] for code in findings],
                "blocks_decisive_frontier": any(
                    code in _DISQUALIFYING_FROM_FRONTIER for code in findings),
                "independently_verified": False,
            })
        summary = {
            "id": pid, "observable": observable,
            "evaluation_unit": evaluation_unit,
            "comparison_reference": comparison_reference,
            "distinguishable_hypothesis_pairs_as_declared": separated,
            "pair_count": len(separated),
            "missing_hypothesis_predictions": [
                h for h in ids if predictions.get(h, "UNKNOWN") == "UNKNOWN"
            ],
            "declared_cost_band": cost,
            "prediction_evidence_refs": refs,
            "prediction_source_verified": False,
            "findings": findings,
            "applicability": prior["applicability"],
            "next_action": prior["next_action"],
            "recommended_action": "COMPARE_WITH_ORIGINAL_EVIDENCE_NOT_AUTORANK",
        }
        # Only echo an execution history the caller actually declared.
        if "prior_execution" in probe:
            summary["prior_execution"] = prior
        summaries.append(summary)

    # A precheck cannot stay "declared PASS" while the probe it is attached to
    # counts repeated windows as independent units: that is the CASE-11 defect
    # reappearing one layer down.
    if repeated_unit_probes:
        prechecks["group_independence"]["review"] = "DECLARED_CONFLICT"
        prechecks["group_independence"]["conflict_with_probe_units"] = repeated_unit_probes
    no_decisive = bool(summaries) and all(s["pair_count"] == 0 for s in summaries)
    efficiency = summarize_declared_probe_frontier(summaries)
    no_legal = efficiency["no_legal_decisive_probe"]
    no_executable = efficiency["no_executable_next_probe"]

    return {
        "status": "ADVISORY_REVIEW_ONLY",
        "question": question,
        "claim_type": claim_type,
        "claim_evidence_refs": claim_refs,
        "premise_candidates": negative_candidates,
        "positive_premise_candidates": positive_candidates,
        "prechecks": prechecks,
        "probe_comparisons": summaries,
        "declared_probe_efficiency": efficiency,
        "probe_findings": probe_findings,
        "no_decisive_probe": no_decisive,
        "no_decisive_probe_question": (
            "Which observable would separate at least one pair of the named hypotheses? "
            "Without one, running any of these probes cannot change the judgment."
            if no_decisive else None),
        "no_legal_decisive_probe": no_legal,
        "no_legal_decisive_probe_question": (
            "Which reference condition is available at prediction time? A probe that "
            "separates the hypotheses only against test-time truth can bound what is "
            "achievable, but cannot decide between them."
            if no_legal and not no_decisive else None),
        # Distinct from the two flags above: the probes can decide and are legal,
        # but none of them is a step you can take now (already answered, needs a
        # repair, needs new information, or needs an authorization).
        "no_executable_next_probe": no_executable,
        "no_executable_next_probe_question": (
            "Which listed probe has not already answered this premise and can start "
            "under the current authorization? A closed probe is recorded evidence, an "
            "invalid one needs its named defect repaired, a closure without a bound "
            "premise or Run must be verified first, and an ungranted one is a "
            "candidate rather than a next action."
            if no_executable else None),
        # What was actually checked this call. Without a project root every
        # closure stays a declaration, and the output says so instead of
        # presenting a non-empty string as verified evidence.
        "run_binding_checked": binder is not None,
        "run_binding_scope": ("DECLARED_REFERENCE_RESOLVED_TO_PROJECT_BYTES_AND_RUN_STATUS"
                              if binder is not None else "NO_PROJECT_ROOT_SUPPLIED"),
        # Execution permission is never granted here: an authorization field in
        # the packet is a caller statement, and this tool cannot verify it.
        "authorization_basis": "CALLER_DECLARED_ONLY_NEVER_A_PERMIT",
        "no_claim_of_novelty_or_scientific_validity": True,
        "original_user_authorization": "UNVERIFIED",
        "automatic_stop": False,
        "automatic_go": False,
        "guidance": ("Refer to PD-RW HIGH_VALUE_RESEARCH_DESIGN / SCIENCE_RESULT_HARVEST; "
                     "verify original Run and named literature before choosing a Task or Probe."),
    }
