"""Aurenza planner strategy: deterministic contribution-greedy allocation.

Contract: docs/CONTRACT.md v1.0.0-draft.4. §5.4 fixes the shared objective
(maximise net_revenue, then lower spoilage_kg, then higher fulfillment_pct) but
leaves the algorithm open. This planner is a bounded, deterministic heuristic:

1. build every feasible (batch -> destination) edge;
2. score each edge by its per-kg *effective gain* = expected_contribution per kg
   plus (for batches that would otherwise spoil by the horizon) the spoilage
   penalty per kg that shipping avoids — this is what lets the planner beat
   FEFO, which ignores the cost of leaving stock to spoil;
3. allocate greedily in descending gain order, respecting batch supply,
   destination capacity and per-produce demand (§11);
4. unlock price-capped destinations with the smallest contract-legal discount
   (5% grid) only when it strictly improves the objective (§2.3/§2.5);
5. warm-start from the baseline plan and keep whichever plan ranks higher under
   the §5.4 order (net_revenue, then lower spoilage_kg, then higher
   fulfillment_pct), so the planner is never worse than the baseline on
   net_revenue and wins equal-revenue ties on the secondary objectives.

Limitations: greedy over a transportation structure with shared destination
capacity is not proven globally optimal; it is bounded and deterministic, and
reports what it actually found. No unbounded combinatorial search is performed.
"""

from engine import core


def _is_expiring(scenario, batch):
    """True when unsold stock of this batch spoils at the horizon (§1.4)."""
    return core.remaining_at_horizon(scenario, batch) < 0


def _batch_penalty(scenario, batch):
    """Spoilage cost per kg if the batch is left unsold and expires; else 0."""
    if _is_expiring(scenario, batch):
        return core._spoilage_rate(scenario, batch)
    return 0.0


def _route_feasible(scenario, batch, dest, cfg):
    produce = batch['produce']
    if produce not in (dest.get('demand') or {}):
        return False
    if dest['type'] not in core.SUPPORTED_DESTINATION_TYPES:
        return False
    dispatch_day = float(scenario['dispatch_day'])
    remain = (float(batch['shelf_life_days']) - (dispatch_day - float(batch['harvest_day']))
              - float(dest['transit_days']))
    if remain < float(cfg['min_arrival_shelf_life_days']) - core.TOLERANCE_KG:
        return False
    if dispatch_day + float(dest['transit_days']) > float(scenario['horizon_days']) + core.TOLERANCE_KG:
        return False
    return True


def _unit_gain(scenario, batch, dest, produce, discount_pct):
    """Expected contribution per kg shipped, plus spoilage avoided per kg sold."""
    eff = core.effective_price(scenario, batch, dest, produce, discount_pct)
    c = (eff
         - float(batch['unit_cost_per_kg'])
         - float(dest['distance_km']) * float(scenario['cost_model']['transport_per_kg_km'])
         - float(scenario['cost_model']['handling_per_kg']))
    return c + _batch_penalty(scenario, batch)


def _discount_for_cap(scenario, batch, dest, produce, cfg):
    """Smallest contract-legal discount that brings price within max_price_per_kg.

    §2.3/§2.5: a destination that caps price only buys when
    effective_price <= max_price_per_kg (inclusive). Returns 0.0 when no cap
    binds or no legal step unlocks it.
    """
    cap = (dest.get('max_price_per_kg') or {}).get(produce)
    if cap is None:
        return 0.0
    base = core.effective_price(scenario, batch, dest, produce, 0.0)
    if base <= cap + core.TOLERANCE_INR:
        return 0.0
    step = float(cfg['discount']['step_pct'])
    max_disc = float(cfg['discount']['eligible_max_pct'])
    d = step
    while d <= max_disc + core.TOLERANCE_KG:
        if core.effective_price(scenario, batch, dest, produce, d) <= cap + core.TOLERANCE_INR:
            return d
        d += step
    return 0.0


def _metrics_of(scenario, flows):
    metrics, _batch, _rec = core.aggregate(scenario, core.build_dispatches(scenario, flows))
    return metrics


def _better(a, b):
    """True when metrics ``a`` outrank ``b`` under the §5.4 objective order.

    §5.4: maximise ``net_revenue``, then minimise ``spoiled_kg``, then maximise
    ``fulfillment_pct``. Comparisons are tolerance-aware so numeric noise inside
    the contract tolerances (₹0.01 / 0.001 kg) cannot flip the choice.
    """
    if a['net_revenue'] > b['net_revenue'] + core.TOLERANCE_INR:
        return True
    if b['net_revenue'] > a['net_revenue'] + core.TOLERANCE_INR:
        return False
    if a['spoiled_kg'] < b['spoiled_kg'] - core.TOLERANCE_KG:
        return True
    if b['spoiled_kg'] < a['spoiled_kg'] - core.TOLERANCE_KG:
        return False
    return a['fulfillment_pct'] > b['fulfillment_pct'] + core.TOLERANCE_KG


def plan_planner(scenario, baseline_flows=None):
    """Return the planner's plan as a list of flows (see core.build_dispatches).

    Only edges that strictly improve the objective are allocated: shipping at a
    non-positive per-kg gain would destroy value versus retaining or spoiling
    the stock, so it is skipped. With ``baseline_flows`` the better of the
    greedy and baseline plans is returned (compared under the §5.4 order:
    net_revenue, then lower spoilage, then higher fulfillment), so the planner
    is never worse than the baseline on net_revenue.
    """
    cfg = core.config_of(scenario)
    dests = scenario['destinations']

    edges = []
    for b in scenario['batches']:
        produce = b['produce']
        for d in dests:
            if not _route_feasible(scenario, b, d, cfg):
                continue
            disc = _discount_for_cap(scenario, b, d, produce, cfg)
            gain = _unit_gain(scenario, b, d, produce, disc)
            edges.append((-gain, b['batch_id'], d['destination_id'], b, d, disc))
    edges.sort(key=lambda t: (t[0], t[1], t[2]))

    cap_left = {d['destination_id']: float(d['capacity_kg']) for d in dests}
    batch_left = {b['batch_id']: float(b['quantity_kg']) for b in scenario['batches']}
    demand_left = {}
    for d in dests:
        for produce, kg in (d['demand'] or {}).items():
            demand_left[(d['destination_id'], produce)] = float(kg)

    flows = []
    for neg_gain, bid, did, b, d, disc in edges:
        if -neg_gain <= core.TOLERANCE_INR:
            continue  # non-positive gain: shipping would not improve net_revenue
        available = min(batch_left[bid], cap_left[did], demand_left.get((did, b['produce']), 0.0))
        if available <= core.TOLERANCE_KG:
            continue
        reason = (f"greedy gain {(-neg_gain):.2f}/kg; "
                  f"{'discount ' + format(disc, 'g') + '% to meet price cap; ' if disc else ''}"
                  f"avoids {_batch_penalty(scenario, b):.2f}/kg spoilage" if _batch_penalty(scenario, b) else
                  f"greedy gain {(-neg_gain):.2f}/kg")
        flows.append({
            'batch_id': bid,
            'destination_id': did,
            'quantity_kg': available,
            'discount_pct': disc,
            'reason': reason,
        })
        batch_left[bid] -= available
        cap_left[did] -= available
        demand_left[(did, b['produce'])] = demand_left.get((did, b['produce']), 0.0) - available
    if baseline_flows is not None and _better(_metrics_of(scenario, baseline_flows),
                                              _metrics_of(scenario, flows)):
        return [dict(f) for f in baseline_flows]
    return flows


def run_planner(scenario, baseline_flows=None):
    """Planner §8 block. Warm-started from the baseline plan when provided."""
    best = plan_planner(scenario, baseline_flows)
    return core.run_strategy(scenario, core.build_dispatches(scenario, best), 'planner')
