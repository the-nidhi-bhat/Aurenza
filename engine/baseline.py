"""Aurenza baseline strategy: deterministic FEFO (First-Expired-First-Out).

Contract: docs/CONTRACT.md v1.0.0-draft.4. §5.4 fixes the shared objective and
metric definitions but does NOT define the baseline algorithm; the team asked
for a credible, domain-standard comparison, so this implements FEFO:

- process batches by earliest expiry (harvest_day + shelf_life_days), then
  batch_id ascending;
- for each batch, prefer the feasible destination with the highest effective
  selling price, then destination_id ascending;
- ship as much as the batch, destination capacity and destination (per-produce)
  demand allow, at discount 0 (no discounting);
- enforce exactly the same §11 hard constraints and §5 accounting as the planner.

FEFO is a heuristic, not a globally optimal solution. Accounting is shared with
the planner via `engine.core` so neither strategy can "cheat" the metrics.
"""

from engine import core


def _feasible_route(scenario, batch, dest, cfg):
    """§3 hard route feasibility: produce demanded, shelf life at arrival, horizon."""
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


def plan_baseline(scenario):
    """Return the FEFO plan as a list of flows (see core.build_dispatches)."""
    cfg = core.config_of(scenario)
    dests = scenario['destinations']
    cap_left = {d['destination_id']: float(d['capacity_kg']) for d in dests}
    demand_left = {}
    for d in dests:
        for produce, kg in (d['demand'] or {}).items():
            demand_left[(d['destination_id'], produce)] = float(kg)

    order = sorted(scenario['batches'],
                   key=lambda b: (float(b['harvest_day']) + float(b['shelf_life_days']),
                                  b['batch_id']))
    flows = []
    for b in order:
        produce = b['produce']
        remaining = float(b['quantity_kg'])
        if remaining <= core.TOLERANCE_KG:
            continue
        ranked = []
        for d in dests:
            if not _feasible_route(scenario, b, d, cfg):
                continue
            eff = core.effective_price(scenario, b, d, produce, 0.0)
            ranked.append((-eff, d['destination_id'], d))
        ranked.sort(key=lambda t: (t[0], t[1]))
        for _neg_eff, did, d in ranked:
            if remaining <= core.TOLERANCE_KG:
                break
            avail = min(remaining, cap_left[did], demand_left.get((did, produce), 0.0))
            if avail <= core.TOLERANCE_KG:
                continue
            flows.append({
                'batch_id': b['batch_id'],
                'destination_id': did,
                'quantity_kg': avail,
                'discount_pct': 0.0,
                'reason': f"FEFO: {produce} batch expiring day "
                          f"{float(b['harvest_day']) + float(b['shelf_life_days']):g} "
                          f"-> {d.get('name', did)} at full price",
            })
            remaining -= avail
            cap_left[did] -= avail
            demand_left[(did, produce)] = demand_left.get((did, produce), 0.0) - avail
    return flows


def run_baseline(scenario):
    """Baseline §8 per-strategy block (convenience wrapper)."""
    return core.run_strategy(scenario, core.build_dispatches(scenario, plan_baseline(scenario)),
                             'baseline')
