"""Compare *declared* probe discriminability against ordinal resource cost.

No scientific outcomes, citation forecasts, authority, or experiment execution
are inferred from a Pareto hint. Actual source evidence belongs to PD-RW.

Two kinds of candidate are not "the decisive experiment to run" even if they
are cheap:

* a probe that separates no declared hypothesis pair cannot change the
  judgment (CASE-08), so it is exploratory, not informative;
* a probe whose reference condition needs test-time truth is not a legal
  comparison (CASE-02/CASE-12); it stays visible as a diagnostic upper bound,
  but is never recommended as a lawful decisive experiment.

Neither is deleted, and neither becomes an automatic stop: the point is to
stop naming them first, not to forbid running them.
"""

_COST_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

# Findings that make a comparison illegal at prediction time. Only legality is
# disqualifying here: an unresolved independent-unit question is a request to
# verify the unit, not a reason to ban every window/frame-level observable.
_DISQUALIFYING = frozenset({"REFERENCE_NOT_LEGAL"})
_UNIT_VERIFICATION = "PROBE_UNIT_NOT_INDEPENDENT"


def summarize_declared_probe_frontier(summaries: list[dict]) -> dict:
    """Return non-dominated candidate IDs using pair-set coverage and known cost.

    Unknown cost remains incomparable. Two probes with equal pair sets and
    equal cost both remain eligible. Fewer predicted pairs alone cannot
    establish that a probe is inferior: the *specific* pairs must be a subset.
    Dominance is only computed between probes that are themselves eligible, so
    a blind or illegal probe can never eliminate a decisive one.
    """
    known = {s["id"]: s for s in summaries
             if s["declared_cost_band"] in _COST_ORDER}
    pairsets = {
        ident: {tuple(pair) for pair in s["distinguishable_hypothesis_pairs_as_declared"]}
        for ident, s in known.items()
    }
    costs = {ident: _COST_ORDER[s["declared_cost_band"]] for ident, s in known.items()}
    findings = {ident: frozenset(s.get("findings") or ()) for ident, s in known.items()}
    discriminating = {ident for ident, pairs in pairsets.items() if pairs}
    disqualified = {ident for ident, codes in findings.items() if codes & _DISQUALIFYING}
    eligible = discriminating - disqualified
    dominated = {}
    for ident in eligible:
        for other_id in eligible:
            if other_id == ident:
                continue
            cheaper = costs[other_id] <= costs[ident]
            coverage = pairsets[other_id] >= pairsets[ident]
            strictly_better = costs[other_id] < costs[ident] or pairsets[other_id] > pairsets[ident]
            if cheaper and coverage and strictly_better:
                dominated.setdefault(ident, []).append(other_id)
    return {
        # Only a probe that separates at least one declared pair, with no
        # already-known illegal input, is an informative frontier candidate.
        # When no probe qualifies, the honest answer is "there is no decisive
        # legal probe", not a Pareto winner among uninformative candidates.
        "frontier_candidate_ids_as_declared": [
            ident for ident in known if ident in eligible and ident not in dominated
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
        "no_discriminating_probe": bool(known) and not discriminating,
        "no_legal_decisive_probe": bool(known) and not eligible,
        "unknown_cost_ids": [
            s["id"] for s in summaries if s["declared_cost_band"] not in _COST_ORDER
        ],
        "scientifically_ranked": False,
        "automatically_selected": False,
        "source_predictions_verified": False,
        "note": ("Declared pairs and cost bands only: compare original evidence, "
                 "scientific importance, independent groups and legal scope before acting. "
                 "No candidate is rejected by this hint."),
    }
