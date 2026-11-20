"""Compare *declared* probe discriminability against ordinal resource cost.

No scientific outcomes, citation forecasts, authority, or experiment execution
are inferred from a Pareto hint. Actual source evidence belongs to PD-RW.

Three kinds of candidate are not "the decisive experiment to run next" even if
they are cheap:

* a probe that separates no declared hypothesis pair cannot change the
  judgment (CASE-08), so it is exploratory, not informative;
* a probe whose reference condition needs test-time truth is not a legal
  comparison (CASE-02/CASE-12); it stays visible as a diagnostic upper bound,
  but is never recommended as a lawful decisive experiment;
* a probe that already ran on the *same premise* cannot supply new information
  by running again (CASE-20/CASE-21). A valid past run makes it historical
  evidence, an invalid one asks for a targeted repair, an inconclusive one
  asks for new information first, and a probe that needs an authorization
  nobody has granted is a candidate, not a currently executable step.

None is deleted and none becomes an automatic stop: the point is to stop
naming them as the next experiment, not to forbid thinking about them.
"""

_COST_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

# Findings that make a comparison illegal at prediction time. Only legality is
# disqualifying here: an unresolved independent-unit question is a request to
# verify the unit, not a reason to ban every window/frame-level observable.
_DISQUALIFYING = frozenset({"REFERENCE_NOT_LEGAL"})
_UNIT_VERIFICATION = "PROBE_UNIT_NOT_INDEPENDENT"

# Only a probe that has not already answered this premise *and* can be started
# under the current authorization is a next action. Everything else keeps a
# named, non-executable role.
_RUNNABLE = "NOT_YET_RUN"


def summarize_declared_probe_frontier(summaries: list[dict]) -> dict:
    """Return non-dominated candidate IDs using pair-set coverage and known cost.

    Unknown cost remains incomparable. Two probes with equal pair sets and
    equal cost both remain eligible. Fewer predicted pairs alone cannot
    establish that a probe is inferior: the *specific* pairs must be a subset.
    Dominance is only computed between probes that are themselves runnable, so
    a blind, illegal, already-closed or unauthorized probe can never eliminate
    a decisive one.
    """
    known = {s["id"]: s for s in summaries
             if s["declared_cost_band"] in _COST_ORDER}
    pairsets = {
        ident: {tuple(pair) for pair in s["distinguishable_hypothesis_pairs_as_declared"]}
        for ident, s in known.items()
    }
    costs = {ident: _COST_ORDER[s["declared_cost_band"]] for ident, s in known.items()}
    findings = {ident: frozenset(s.get("findings") or ()) for ident, s in known.items()}
    applicability = {ident: s.get("applicability", _RUNNABLE) for ident, s in known.items()}
    discriminating = {ident for ident, pairs in pairsets.items() if pairs}
    disqualified = {ident for ident, codes in findings.items() if codes & _DISQUALIFYING}
    legal_decisive = discriminating - disqualified
    runnable = {ident for ident in legal_decisive if applicability[ident] == _RUNNABLE}
    dominated = {}
    for ident in runnable:
        for other_id in runnable:
            if other_id == ident:
                continue
            cheaper = costs[other_id] <= costs[ident]
            coverage = pairsets[other_id] >= pairsets[ident]
            strictly_better = costs[other_id] < costs[ident] or pairsets[other_id] > pairsets[ident]
            if cheaper and coverage and strictly_better:
                dominated.setdefault(ident, []).append(other_id)

    def with_role(role: str) -> list[str]:
        return [ident for ident in known if applicability[ident] == role]

    return {
        # Only a probe that separates at least one declared pair, has no
        # already-known illegal input, and has not already answered this
        # premise is an informative next action. When nothing qualifies, the
        # honest answer is "there is no executable decisive probe", not a
        # Pareto winner among candidates that cannot change the judgment.
        "frontier_candidate_ids_as_declared": [
            ident for ident in known if ident in runnable and ident not in dominated
        ],
        "dominated_candidates_as_declared": [
            {"id": ident, "dominated_by": dominators}
            for ident, dominators in dominated.items()
        ],
        # Not candidates for the decisive experiment, still legitimate to run:
        # a blind probe can be a pilot, an oracle-referenced probe can bound
        # what is achievable. Both keep their findings attached upstream.
        "exploratory_probe_ids": [i for i in known if i not in discriminating],
        "diagnostic_upper_bound_ids": [
            i for i in known if i in disqualified and i in discriminating
        ],
        # CASE-11/EXT-X3: confirm the number of *independent* units before
        # trusting the comparison; window/frame metrics are not banned.
        "needs_unit_verification_ids": [
            i for i, codes in findings.items() if _UNIT_VERIFICATION in codes
        ],
        # CASE-20/CASE-21: the probe already produced its answer for this
        # premise. Re-running it cannot add information; it supports the next
        # judgment as recorded evidence only.
        "historical_evidence_ids": with_role("HISTORICAL_EVIDENCE_ONLY"),
        "repair_required_ids": with_role("TARGETED_REPAIR"),
        "awaiting_new_information_ids": with_role("AWAIT_NEW_INFORMATION"),
        "revisit_on_new_information_ids": with_role("REVISIT_ON_NEW_INFORMATION"),
        "needs_authorization_ids": with_role("NEEDS_AUTHORIZATION"),
        "blocked_ids": with_role("BLOCKER_UNRESOLVED"),
        # A caller-declared closure with no Run reference is neither accepted
        # as closed nor safe to duplicate: verify the Run first.
        "unverified_closure_ids": with_role("CLOSURE_DECLARED_NOT_VERIFIED"),
        # A closure that never named its premise, or a Run record that
        # contradicts the declaration: neither closes this premise, and neither
        # may be used to eliminate a live probe.
        "premise_unbound_ids": with_role("CLOSURE_PREMISE_UNBOUND"),
        "status_conflict_ids": with_role("STATUS_CONFLICT"),
        "no_discriminating_probe": bool(known) and not discriminating,
        "no_legal_decisive_probe": bool(known) and not legal_decisive,
        "no_executable_next_probe": bool(known) and bool(legal_decisive) and not runnable,
        "unknown_cost_ids": [
            s["id"] for s in summaries if s["declared_cost_band"] not in _COST_ORDER
        ],
        "scientifically_ranked": False,
        "automatically_selected": False,
        "source_predictions_verified": False,
        "note": ("Declared pairs, cost bands and declared execution state only: compare "
                 "original evidence, scientific importance, independent groups and legal "
                 "scope before acting. No candidate is rejected by this hint."),
    }
