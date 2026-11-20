"""The packet contract, in one place, with paths in the message.

SCIENCE-03D recorded four independent sessions that each wrote a packet and each
had it rejected -- and the rejection was the barrier, not the science. Three
things made repair impossible from the error alone:

* only the *first* defect was raised, so a packet with four defects needed four
  round trips, and a caller with a retry budget never got there;
* the message named the wrong thing ("Unexpected precheck names" for a
  `prechecks` **list**), so the obvious repair made it worse;
* fields the decision path silently ignores were accepted, so a caller could
  believe its execution history had been read when nothing looked at it.

This module answers all three for *shape*: every violation at once, each with a
path, the value found and what the field accepts; and a separate list of the
fields that will be ignored. It never fills in a prediction, a premise, an
evidence reference or an authorization, and it cannot accept a packet the
decision path would reject -- `decision` still decides, and a normalized packet
is judged by it exactly like a handwritten one.
"""
from __future__ import annotations
import difflib
import re

from .decision import (
    CHECKS, CHECK_STATES, CLAIMS, CLAIM_ALIASES, COSTS, EXECUTION_STATUSES,
    MAX_PROBES, OUTCOMES, PRIOR_EXECUTION_FIELDS,
)

SHAPE_VERSION = "pdrw-packet-v1"
PACKET_FIELDS = ("claim_type", "question", "hypotheses", "proposed_premise",
                 "prechecks", "probes", "claim_evidence_refs",
                 "prior_negative_lessons", "prior_positive_lessons")
PROBE_FIELDS = ("id", "observable", "evaluation_unit", "comparison_reference",
                "predictions", "cost_band", "prediction_evidence_refs",
                "prior_execution")
# These only mean something inside one probe's `prior_execution`. At the top
# level they are not read, so a packet that puts them there loses its history
# without a word -- which is what one independent session did.
EXECUTION_ONLY_FIELDS = tuple(sorted(PRIOR_EXECUTION_FIELDS))
MAX_ID = 80
MAX_DESCRIPTION = 240
MAX_SCOPE_KEYS = 12
MAX_SCOPE_KEY = 60
MAX_SCOPE_VALUE = 160
MAX_REF = 240
MAX_QUESTION = 1000

_UNIT_HINT = ("a short unit token -- SUBJECT, WINDOW, FRAME, RECORD, SEGMENT, "
              "TOKEN, ROW, EPISODE, or your own one-word unit. The decision path "
              "compares this token with the metric's independent unit, so a "
              "sentence here is not read as a unit at all.")

# A unit is compared with a fixed token set, so prose in this field does not
# fail -- it silently stops the independence check from ever firing. Reported as
# a warning, never a violation: the science may be right, the field is just not
# the one the check reads.
_UNIT_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9 _/\-]{0,39}$")

TEMPLATE = {
    "claim_type": "MECHANISM/CAUSAL",
    "question": "One bounded question, at most 1000 characters.",
    "hypotheses": ["H1_PRIMARY", "H2_COMPETING"],
    "proposed_premise": {
        "premise_id": "PREMISE_ID",
        "scope": {"dataset": "which data", "unit": "SUBJECT",
                  "outcome": "which primary outcome"},
    },
    "prechecks": {
        # The vocabulary is closed: these six names, nothing else. Four
        # independent packets in 03D each invented their own check names and
        # were rejected for it -- which is why all six are listed here.
        "label_provenance": {"status": "NOT_CHECKED", "evidence_refs": []},
        "group_independence": {"status": "NOT_CHECKED", "evidence_refs": []},
        "legal_inputs": {"status": "NOT_CHECKED", "evidence_refs": []},
        "evaluation_integrity": {"status": "NOT_CHECKED", "evidence_refs": []},
        "metric_appropriateness": {"status": "NOT_CHECKED", "evidence_refs": []},
        "effect_size": {"status": "NOT_CHECKED", "evidence_refs": []},
    },
    "probes": [
        {
            "id": "P1",
            "observable": "subject-level MAE of the primary outcome",
            "evaluation_unit": "SUBJECT",
            "comparison_reference": "same folds, existing baseline",
            "predictions": {"H1_PRIMARY": "DECREASE", "H2_COMPETING": "INCREASE"},
            "cost_band": "LOW",
        }
    ],
}


def template() -> dict:
    """A minimal packet that the decision path accepts as written."""
    import copy
    return copy.deepcopy(TEMPLATE)


def _close(value, pool, limit: int = 2) -> str:
    hits = difflib.get_close_matches(str(value), list(pool), n=limit, cutoff=0.5)
    return " or ".join(hits) if hits else ""


def _violation(violations, path, problem, accepted, hint=None, found=None):
    entry = {"path": path, "problem": problem, "accepted": accepted}
    if found is not None:
        text = found if isinstance(found, str) else repr(found)
        entry["found"] = text[:120] + ("..." if len(text) > 120 else "")
    if hint:
        entry["hint"] = hint
    violations.append(entry)


def _check_text(violations, value, path, limit, accepted, hint=None):
    if value is None:
        _violation(violations, path, "missing", accepted, hint or f"1..{limit} characters")
        return False
    if not isinstance(value, str) or not value.strip():
        _violation(violations, path, "not a non-empty string", accepted,
                   hint or f"1..{limit} characters", found=value)
        return False
    if len(value) > limit:
        _violation(violations, path, f"too long ({len(value)} > {limit})", accepted,
                   hint or f"shorten to 1..{limit} characters", found=value)
        return False
    return True


def _check_refs(violations, value, path):
    if value is None:
        return
    if not isinstance(value, list) or len(value) > 8 or any(
            not isinstance(x, str) or not x.strip() or len(x) > MAX_REF for x in value):
        _violation(violations, path, "not a small list of short strings",
                   "list of at most 8 source identifiers, each at most 240 characters",
                   "a list of identifiers, not one joined string", found=value)


def _check_scope(violations, scope, path):
    if scope is None:
        _violation(violations, path, "missing",
                   "mapping of at most 12 keys to short string values",
                   "e.g. {\"dataset\": \"PRESS DEV 26\", \"unit\": \"SUBJECT\"}")
        return
    if not isinstance(scope, dict):
        _violation(violations, path, f"is a {type(scope).__name__}, not a mapping",
                   "mapping of at most 12 keys to short string values",
                   "split the description into keys: dataset / input / unit / outcome / "
                   "excluded. One long string cannot be compared with another packet's scope.",
                   found=scope)
        return
    if not scope:
        _violation(violations, path, "empty", "at least one key")
        return
    if len(scope) > MAX_SCOPE_KEYS:
        _violation(violations, path, f"{len(scope)} keys > {MAX_SCOPE_KEYS}",
                   f"at most {MAX_SCOPE_KEYS} keys")
    for key, value in scope.items():
        slot = f"{path}.{key}"
        if not isinstance(key, str) or not key.strip() or len(key) > MAX_SCOPE_KEY:
            _violation(violations, slot, "unsupported key", f"1..{MAX_SCOPE_KEY} characters")
        if not isinstance(value, str) or not value.strip():
            _violation(violations, slot, "not a non-empty string", "short string value",
                       found=value)
        elif len(value) > MAX_SCOPE_VALUE:
            _violation(violations, slot,
                       f"value too long ({len(value)} > {MAX_SCOPE_VALUE})",
                       f"at most {MAX_SCOPE_VALUE} characters per value",
                       "move the argument into the report; scope holds the boundary, "
                       "not the reasoning", found=value)


def _check_prechecks(violations, checks, path):
    if checks is None:
        return
    if isinstance(checks, list):
        known = [c.get("id") for c in checks
                 if isinstance(c, dict) and c.get("id") in CHECKS]
        example = ("{" + ", ".join(f'"{c}": {{"status": "PASS", "evidence_refs": []}}'
                                  for c in (known[:2] or ["group_independence"])) + "}")
        _violation(violations, path, f"is a list of {len(checks)}, not a mapping",
                   "mapping keyed by check name",
                   "key your entries by their own id: " + example, found="list")
        return
    if not isinstance(checks, dict):
        _violation(violations, path, f"is a {type(checks).__name__}",
                   "mapping keyed by check name", found=checks)
        return
    unknown = sorted(set(checks) - set(CHECKS))
    if unknown:
        hint = ""
        near = _close(unknown[0], CHECKS) if len(unknown) == 1 else ""
        if near:
            hint = f"did you mean {near}?"
        _violation(violations, path, f"unknown check name(s): {', '.join(unknown)}",
                   "one of: " + ", ".join(CHECKS), hint or "check names are fixed", found=unknown)
    for key in [k for k in checks if k in CHECKS]:
        entry = checks[key]
        slot = f"{path}.{key}"
        if not isinstance(entry, dict):
            _violation(violations, slot, "not an object", "{\"status\": ..., \"evidence_refs\": [...]}",
                       found=entry)
            continue
        status = entry.get("status")
        if not isinstance(status, str) or status not in CHECK_STATES:
            near = _close(status, CHECK_STATES)
            _violation(violations, f"{slot}.status", "not a check state",
                       " or ".join(sorted(CHECK_STATES)),
                       f"did you mean {near}?" if near else "declare the state you actually have",
                       found=status)
        _check_refs(violations, entry.get("evidence_refs"), f"{slot}.evidence_refs")


def _check_prior(violations, prior, path):
    if prior is None:
        return
    if not isinstance(prior, dict):
        _violation(violations, path, "not an object", "declared execution fields", found=prior)
        return
    extra = sorted(set(prior) - set(PRIOR_EXECUTION_FIELDS))
    if extra:
        _violation(violations, path, f"unknown field(s): {', '.join(extra)}",
                   "only: " + ", ".join(EXECUTION_ONLY_FIELDS),
                   "the decision path rejects the whole probe when a prior_execution "
                   "field is unknown", found=extra)
    status = prior.get("status", "NOT_EXECUTED")
    if not isinstance(status, str) or status not in EXECUTION_STATUSES:
        near = _close(status, EXECUTION_STATUSES)
        _violation(violations, f"{path}.status", "not an execution state",
                   " or ".join(sorted(EXECUTION_STATUSES)),
                   f"did you mean {near}?" if near else "a declared state, not a sentence",
                   found=status)
    for key in ("run_ref", "record_ref", "premise_ref", "conclusion", "new_information"):
        item = prior.get(key)
        if item is not None:
            _check_text(violations, item, f"{path}.{key}", MAX_REF,
                        f"at most {MAX_REF} characters",
                        "a project-relative path for run_ref/record_ref/premise_ref"
                        if key.endswith("_ref") else None)
    if prior.get("premise_id") is not None:
        _check_text(violations, prior["premise_id"], f"{path}.premise_id", MAX_ID,
                    "1..80 characters", "the premise this Run is claimed to have tested")
    if "requires_new_authorization" in prior and not isinstance(
            prior["requires_new_authorization"], bool):
        _violation(violations, f"{path}.requires_new_authorization", "not a boolean",
                   "true or false", "a declared flag, never an execution permit",
                   found=prior["requires_new_authorization"])


def _check_probe(violations, probe, index, hypothesis_ids, warnings):
    path = f"probes[{index}]"
    if not isinstance(probe, dict):
        _violation(violations, path, "not an object", "one probe object", found=probe)
        return None
    for key, limit, hint in (
            ("id", MAX_ID, None),
            ("observable", MAX_DESCRIPTION, None),
            ("evaluation_unit", MAX_ID, _UNIT_HINT),
            ("comparison_reference", MAX_DESCRIPTION, None)):
        _check_text(violations, probe.get(key), f"{path}.{key}", limit,
                    f"1..{limit} characters", hint)
    predictions = probe.get("predictions")
    if isinstance(predictions, list):
        _violation(violations, f"{path}.predictions", "is a list, not a mapping",
                   "mapping of hypothesis ID to INCREASE/DECREASE/NO_CHANGE/UNKNOWN",
                   "{\"H1_PRIMARY\": \"DECREASE\", \"H2_COMPETING\": \"INCREASE\"}",
                   found=predictions)
    elif predictions is None:
        _violation(violations, f"{path}.predictions", "missing",
                   "mapping of hypothesis ID to outcome")
    elif not isinstance(predictions, dict):
        _violation(violations, f"{path}.predictions", "not a mapping",
                   "mapping of hypothesis ID to outcome", found=predictions)
    else:
        for key, value in predictions.items():
            slot = f"{path}.predictions.{key}"
            if hypothesis_ids and key not in hypothesis_ids:
                near = _close(key, hypothesis_ids, 1)
                _violation(violations, slot, "unknown hypothesis",
                           "one of the declared hypothesis IDs",
                           f"did you mean {near}?" if near else
                           "the ID must match `hypotheses` exactly", found=key)
            if not isinstance(value, str) or value not in OUTCOMES:
                near = _close(value, OUTCOMES)
                _violation(violations, slot, "not a qualitative outcome",
                           " or ".join(sorted(OUTCOMES)),
                           f"did you mean {near}?" if near else
                           "one of four directions; a sentence is not a prediction",
                           found=value)
    cost = probe.get("cost_band", "UNKNOWN")
    if not isinstance(cost, str) or cost not in COSTS:
        near = _close(cost, COSTS)
        _violation(violations, f"{path}.cost_band", "not a cost band",
                   " or ".join(sorted(COSTS)),
                   f"did you mean {near}?" if near else "an ordinal band, not an amount",
                   found=cost)
    unit = probe.get("evaluation_unit")
    if isinstance(unit, str) and unit.strip() and not _UNIT_TOKEN.match(unit.strip()):
        warnings.append({
            "path": f"{path}.evaluation_unit",
            "note": ("read as a unit token, but it is a sentence: the independence "
                     "check compares this value with SUBJECT/WINDOW/FRAME/... and will "
                     "not match it, so a repeated-unit conflict cannot be detected. "
                     "Name the unit and keep the description in comparison_reference."),
        })
    _check_refs(violations, probe.get("prediction_evidence_refs"),
                f"{path}.prediction_evidence_refs")
    _check_prior(violations, probe.get("prior_execution"), f"{path}.prior_execution")
    return probe.get("id")


def check_packet(packet) -> dict:
    """Return every shape violation at once; never raises for a dict input.

    Shape only: it says what the decision path would refuse to parse, and what it
    would silently ignore. It does not say whether the science is any good, and a
    `SHAPE_OK` packet can still be rejected by `decision` for a scientific reason
    (an illegal reference, a probe that separates nothing, an unbound closure).
    """
    violations: list[dict] = []
    ignored: list[dict] = []
    warnings: list[dict] = []
    if not isinstance(packet, dict):
        _violation(violations, "$", f"is a {type(packet).__name__}",
                   "one JSON object", found=packet)
        return {"status": "SHAPE_VIOLATIONS", "shape_version": SHAPE_VERSION,
                "violations": violations, "ignored_fields": ignored,
                "warnings": warnings,
                "note": "Shape only. Nothing here is executed or authorized."}

    # A common slip: the CLI's own envelope handed back as the packet. Saying so
    # costs one line and saves a confusing rejection.
    if (set(packet) <= {"status", "packet", "note", "shape_version"}
            and isinstance(packet.get("packet"), dict)):
        _violation(violations, "$", "this is a CLI envelope, not a packet",
                   "the value of its `packet` key",
                   "pass the packet itself; the envelope's `status` field is output, "
                   "not a declared execution state", found=sorted(packet))

    unknown = sorted(set(packet) - set(PACKET_FIELDS))
    for key in unknown:
        if key in PRIOR_EXECUTION_FIELDS:
            _violation(violations, key, "top-level execution field",
                       "inside probes[i].prior_execution",
                       "the decision path reads execution history only from a probe; "
                       "at the top level this value is not used at all",
                       found=packet[key])
        else:
            ignored.append({"path": key,
                            "note": "not part of the contract; the decision path ignores it"})

    claim = packet.get("claim_type")
    if not isinstance(claim, str) or not claim.strip():
        _violation(violations, "claim_type", "missing or not textual",
                   " or ".join(sorted(CLAIMS)),
                   "the *kind* of claim, not the claim itself")
    else:
        resolved = CLAIM_ALIASES.get(claim, claim)
        if resolved not in CLAIMS:
            near = _close(claim, list(CLAIMS) + list(CLAIM_ALIASES))
            _violation(violations, "claim_type", "not a claim type",
                       " or ".join(sorted(CLAIMS)),
                       f"did you mean {near}?" if near else
                       "this field names the claim's type; the claim's content "
                       "belongs in `question`", found=claim)

    _check_text(violations, packet.get("question"), "question", MAX_QUESTION,
                "1..1000 characters")

    hypotheses = packet.get("hypotheses")
    if not isinstance(hypotheses, list):
        _violation(violations, "hypotheses", "not a list",
                   "list of 2..6 short hypothesis IDs", found=hypotheses)
        hypotheses = []
    elif not 2 <= len(hypotheses) <= 6:
        _violation(violations, "hypotheses", f"{len(hypotheses)} entries",
                   "2..6 distinct hypothesis IDs")
    ids = []
    for index, item in enumerate(hypotheses):
        slot = f"hypotheses[{index}]"
        if not isinstance(item, str):
            _violation(violations, slot, "not a string", "short hypothesis ID", found=item)
            continue
        if len(item) > MAX_ID:
            _violation(violations, slot, f"too long ({len(item)} > {MAX_ID})",
                       "short ID, e.g. H_SENSOR_DRIFT",
                       "the ID is a key for predictions; its explanation belongs in "
                       "`question` or `scope`", found=item)
        ids.append(item)
    if len(set(ids)) != len(ids):
        _violation(violations, "hypotheses", "duplicate IDs", "distinct IDs")

    proposed = packet.get("proposed_premise")
    if not isinstance(proposed, dict):
        _violation(violations, "proposed_premise", "missing or not an object",
                   "{\"premise_id\": ..., \"scope\": {...}}", found=proposed)
    else:
        _check_text(violations, proposed.get("premise_id"), "proposed_premise.premise_id",
                    MAX_ID, "1..80 characters",
                    "the scientific premise under study, not the experiment's name")
        _check_scope(violations, proposed.get("scope", {}), "proposed_premise.scope")
        for key in sorted(set(proposed) - {"premise_id", "scope"}):
            ignored.append({"path": f"proposed_premise.{key}",
                            "note": "not part of the contract; the decision path ignores it"})

    _check_prechecks(violations, packet.get("prechecks"), "prechecks")
    _check_refs(violations, packet.get("claim_evidence_refs"), "claim_evidence_refs")

    probes = packet.get("probes")
    if not isinstance(probes, list):
        _violation(violations, "probes", "missing or not a list",
                   f"list of 1..{MAX_PROBES} probe objects", found=probes)
        probes = []
    elif not 1 <= len(probes) <= MAX_PROBES:
        _violation(violations, "probes", f"{len(probes)} entries",
                   f"1..{MAX_PROBES} probes")
    seen = []
    for index, probe in enumerate(probes):
        ident = _check_probe(violations, probe, index, ids, warnings)
        if isinstance(ident, str):
            if ident in seen:
                _violation(violations, f"probes[{index}].id", "duplicate probe ID",
                           "distinct probe IDs", found=ident)
            seen.append(ident)
        if isinstance(probe, dict):
            for key in sorted(set(probe) - set(PROBE_FIELDS)):
                ignored.append({"path": f"probes[{index}].{key}",
                                "note": "not part of the contract; the decision path ignores it"})

    for name in ("prior_negative_lessons", "prior_positive_lessons"):
        value = packet.get(name)
        if value is not None and (not isinstance(value, list) or len(value) > 10):
            _violation(violations, name, "not a small list",
                       "list of at most 10 declared lessons", found=value)

    violations.sort(key=lambda item: item["path"])
    return {
        "status": "SHAPE_OK" if not violations else "SHAPE_VIOLATIONS",
        "shape_version": SHAPE_VERSION,
        "violation_count": len(violations),
        "violations": violations,
        "ignored_fields": ignored,
        "warnings": warnings,
        "note": ("Shape only: an accepted packet can still be refused by `decision` "
                 "for a scientific reason, and nothing here is executed or authorized."),
    }


def normalize_packet(packet) -> dict:
    """Apply only the structural moves that cannot change what was claimed.

    Two shapes are rewritten, and only when the rewrite is a bijection of the
    input: a `prechecks` list of `{id, status, ...}` keyed by its own ids, and
    `predictions` written as a list of `{hypothesis, outcome}` pairs. Every other
    element -- a prediction's direction, an evidence reference, a premise, an
    authorization flag, a prose scope -- is left exactly as written and reported
    as refused, because choosing a value for it would be inventing science.
    """
    import copy
    original = copy.deepcopy(packet) if isinstance(packet, (dict, list)) else packet
    changes: list[dict] = []
    refused: list[dict] = []
    if not isinstance(original, dict):
        return {"packet": original, "changes": [], "refused": [
            {"path": "$", "reason": "not an object"}]}

    work = copy.deepcopy(original)

    checks = work.get("prechecks")
    if isinstance(checks, list):
        mapping, problem = {}, None
        for index, item in enumerate(checks):
            if not isinstance(item, dict):
                problem = f"prechecks[{index}] is not an object"
                break
            ident = item.get("id")
            if ident not in CHECKS:
                problem = f"prechecks[{index}].id is not a check name"
                break
            if ident in mapping:
                problem = f"prechecks[{index}].id duplicates {ident}"
                break
            entry = {k: v for k, v in item.items() if k != "id"}
            if "status" not in entry:
                problem = f"prechecks[{index}] has no status"
                break
            mapping[ident] = entry
        if problem:
            refused.append({"path": "prechecks", "reason": problem,
                            "hint": "a check needs an id from the fixed list and a status; "
                                    "nothing is guessed"})
        elif mapping:
            work["prechecks"] = mapping
            changes.append({"path": "prechecks", "from": f"list[{len(checks)}]",
                            "to": "mapping keyed by id",
                            "kept_fields": sorted({k for entry in mapping.values()
                                                   for k in entry})})

    probes = work.get("probes")
    if isinstance(probes, list):
        for index, probe in enumerate(probes):
            if not isinstance(probe, dict):
                continue
            predictions = probe.get("predictions")
            if not isinstance(predictions, list):
                continue
            mapping, problem = {}, None
            for item in predictions:
                if not isinstance(item, dict):
                    problem = "an entry is not an object"
                    break
                key = item.get("hypothesis", item.get("id"))
                value = item.get("outcome", item.get("prediction"))
                if not isinstance(key, str) or not isinstance(value, str):
                    problem = "an entry has no hypothesis/outcome pair"
                    break
                if value not in OUTCOMES:
                    problem = f"outcome {value!r} is not one of the four directions"
                    break
                if key in mapping:
                    problem = f"hypothesis {key} appears twice"
                    break
                mapping[key] = value
            if problem:
                refused.append({"path": f"probes[{index}].predictions", "reason": problem,
                                "hint": "pairs are moved only when the outcome is one of "
                                        "INCREASE/DECREASE/NO_CHANGE/UNKNOWN"})
            elif mapping:
                probe["predictions"] = mapping
                changes.append({"path": f"probes[{index}].predictions",
                                "from": f"list[{len(predictions)}]",
                                "to": "mapping hypothesis->outcome"})

    for path, value in (("proposed_premise.scope",
                         (work.get("proposed_premise") or {}).get("scope")
                         if isinstance(work.get("proposed_premise"), dict) else None),):
        if isinstance(value, str):
            refused.append({"path": path,
                            "reason": "one string, not a mapping",
                            "hint": "split it yourself into dataset/input/unit/outcome: "
                                    "which key holds which phrase is a scientific choice"})

    hoisted = sorted(k for k in work if k in PRIOR_EXECUTION_FIELDS)
    if hoisted:
        refused.append({"path": ", ".join(hoisted),
                        "reason": "execution fields at the top level",
                        "hint": "move them into the one probe they describe; with more than "
                                "one probe, which probe they belong to is not inferable"})

    return {
        "packet": work if changes else original,
        "changes": changes,
        "refused": refused,
        "note": ("Only lossless structural moves. Predictions, evidence references, "
                 "premises and authorization values are untouched; a refused item has "
                 "to be written by the caller."),
    }
