"""Compare *declared* probe discriminability against ordinal resource cost.

No scientific outcomes, citation forecasts, authority, or experiment execution
are inferred from a Pareto hint. Actual source evidence belongs to PD-RW.
"""

_COST_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def summarize_declared_probe_frontier(summaries: list[dict]) -> dict:
    """Return non-dominated candidate IDs using pair-set coverage and known cost.

    Unknown cost remains incomparable. Two probes with equal pair sets and
    equal cost both remain eligible. Fewer predicted pairs alone cannot
    establish that a probe is inferior: the *specific* pairs must be a subset.
    """
    known = {s["id"]: s for s in summaries
             if s["declared_cost_band"] in _COST_ORDER}
    pairsets = {
        ident: {tuple(pair) for pair in s["distinguishable_hypothesis_pairs_as_declared"]}
        for ident, s in known.items()
    }
    discriminating = {ident for ident, pairs in pairsets.items() if pairs}
    dominated = {}
    for ident, s in known.items():
        for other_id, other in known.items():
            if other_id == ident:
                continue
            cheaper = _COST_ORDER[other["declared_cost_band"]] <= _COST_ORDER[s["declared_cost_band"]]
            coverage = pairsets[other_id] >= pairsets[ident]
            strictly_better = (
                _COST_ORDER[other["declared_cost_band"]] < _COST_ORDER[s["declared_cost_band"]]
                or pairsets[other_id] > pairsets[ident]
            )
            if cheaper and coverage and strictly_better:
                dominated.setdefault(ident, []).append(other_id)
    return {
        # A probe that separates no hypothesis pair cannot change the judgment,
        # so it must not be named as the cheap option. When *no* probe separates
        # anything, the honest answer is "there is no decisive probe", not a
        # Pareto winner among equally uninformative candidates.
        "frontier_candidate_ids_as_declared": (
            [ident for ident in known if ident not in dominated] if discriminating else []
        ),
        "dominated_candidates_as_declared": [
            {"id": ident, "dominated_by": dominators}
            for ident, dominators in dominated.items()
        ],
        "no_discriminating_probe": bool(known) and not discriminating,
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
