"""Aurenza core: shared contract logic for every strategy.

Contract: docs/CONTRACT.md v1.0.0-draft.4 (see §0.2, §1-§6, §8, §11, §12).

This module holds everything both strategies share so baseline and planner are
guaranteed to use identical validation, accounting and feasibility rules:

- strict scenario validation (§0.2, §7);
- disruption application (§7, §11);
- FEFO-independent dispatch construction with §5 cost attribution;
- the §6 metrics + §8 batch_summary/reconciliation aggregator;
- improvement + top-level result assembly (§8).

Proposed clarifications that are NOT part of the frozen contract are marked
`CONTRADICTION-n` / `CLARIFICATION-n` inline and in docs/ASSUMPTIONS.md.
"""

import copy
import json
import os

# --- §0.2 / §7 constants -------------------------------------------------

TOLERANCE_INR = 0.01          # §12: money comparisons use a 0.01 tolerance
TOLERANCE_KG = 0.001          # §12: mass comparisons use a 0.001 kg tolerance
EPS_PCT = 1e-9               # §9.4: baseline-zero threshold for delta_pct
SCHEMA_MAJOR = '1'            # §0.2: engine implements schema MAJOR version 1
SCHEMA_VERSION = '1.0.0'
SUPPORTED_DESTINATION_TYPES = ('retail', 'wholesale')            # §7 / U4
DISRUPTION_TYPES = ('transport_strike', 'demand_spike', 'shelf_life_shock',
                    'capacity_reduction', 'price_drop')           # §7

DEFAULT_CONFIG = {
    'min_arrival_shelf_life_days': 0.5,                            # A2
    'demand_response': {'enabled': False, 'discount_elasticity': 0.0,
                        'max_demand_multiplier': 1.0},              # §2.2 / A3
    'discount': {'eligible_max_pct': 30.0, 'step_pct': 5.0,
                 'only_near_expiry': True, 'near_expiry_days': 1.0,
                 'require_justification': True},                   # §2.3 / A7
    'sales_allocation': 'highest_effective_price_first',           # §12 / A4
}
DEFAULT_UNITS = {'mass': 'kg', 'currency': 'INR', 'time': 'day',
                 'distance': 'km', 'discount': 'percent', 'freshness': 'percent'}

REQUIRED_SCENARIO_FIELDS = (
    'schema_version', 'scenario_id', 'seed', 'units', 'horizon_days',
    'dispatch_day', 'cost_model', 'batches', 'destinations',
)
REQUIRED_BATCH_FIELDS = (
    'batch_id', 'produce', 'quantity_kg', 'harvest_day', 'shelf_life_days',
    'freshness_pct', 'unit_cost_per_kg', 'base_price_per_kg',
)
REQUIRED_DESTINATION_FIELDS = (
    'destination_id', 'type', 'capacity_kg', 'transit_days', 'distance_km',
    'demand', 'price_per_kg',
)


class ScenarioError(ValueError):
    """Malformed scenario input (§0.2: missing required field / bad enum)."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


# --- loading / validation ------------------------------------------------

def load_scenario(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(obj, path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write('\n')


def _require_fields(obj, fields, where):
    if not isinstance(obj, dict):
        raise ScenarioError(f'{where}: expected an object, got {type(obj).__name__}')
    missing = [f for f in fields if f not in obj]
    if missing:
        raise ScenarioError(f'{where}: missing required field(s): {", ".join(missing)}')


def validate_scenario(scenario):
    """§0.2/§7: reject malformed input instead of silently defaulting."""
    _require_fields(scenario, REQUIRED_SCENARIO_FIELDS, 'scenario')
    major = str(scenario['schema_version']).split('.')[0]
    if major != SCHEMA_MAJOR:
        raise ScenarioError(
            f"scenario: unsupported schema_version {scenario['schema_version']!r} "
            f"(engine implements MAJOR {SCHEMA_MAJOR})")
    for i, b in enumerate(scenario['batches']):
        _require_fields(b, REQUIRED_BATCH_FIELDS, f'batches[{i}]')
    for i, d in enumerate(scenario['destinations']):
        _require_fields(d, REQUIRED_DESTINATION_FIELDS, f'destinations[{i}]')
    for i, dis in enumerate(scenario.get('disruptions') or []):
        _require_fields(dis, ('type',), f'disruptions[{i}]')
        if dis['type'] not in DISRUPTION_TYPES:
            # §0.2 hard error takes precedence over §11 violation entry for enums.
            raise ScenarioError(
                f"disruptions[{i}]: unknown_disruption_type {dis['type']!r} "
                f"(documented: {', '.join(DISRUPTION_TYPES)})",
                code='unknown_disruption_type')
    _config(scenario)  # forces discount config validation (invalid_near_expiry_days)


def config_of(scenario):
    """§0.3: resolve the config block against the conservative defaults."""
    return _config(scenario)


def _config(scenario):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy of defaults
    given = scenario.get('config') or {}
    for k, v in given.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    if float(cfg['discount']['near_expiry_days']) < 0:
        raise ScenarioError('config.discount.near_expiry_days must be >= 0',
                            code='invalid_near_expiry_days')
    return cfg


# --- disruptions (§7) ----------------------------------------------------
# CONTRADICTION-2: the contract names 5 disruption types but does not define
# their parameter effects. docs/ASSUMPTIONS.md documents the effects below;
# they are PROVISIONAL and need Iffa/owner sign-off (A9 is also open).

def apply_disruptions(scenario):
    """Return a deep-copied scenario with documented disruption effects applied."""
    s = json.loads(json.dumps(scenario))
    dests = {d['destination_id']: d for d in s['destinations']}
    batches = {b['batch_id']: b for b in s['batches']}

    for dis in s.get('disruptions') or []:
        p = dis.get('params') or {}
        dtype = dis['type']
        if dtype in ('transport_strike', 'capacity_reduction'):
            mult = float(p.get('capacity_multiplier',
                               0.0 if dtype == 'transport_strike' else 0.5))
            for did in p.get('affected_destination_ids', []):
                if did in dests:
                    dests[did]['capacity_kg'] = float(dests[did]['capacity_kg']) * mult
        elif dtype == 'demand_spike':
            mult = float(p.get('demand_multiplier', 1.0))
            produce = p.get('produce')
            for did in p.get('affected_destination_ids', []):
                d = dests.get(did)
                if not d:
                    continue
                for pr in (d['demand'] or {}):
                    if produce is None or pr == produce:
                        d['demand'][pr] = float(d['demand'][pr]) * mult
        elif dtype == 'price_drop':
            mult = float(p.get('price_multiplier', 1.0))
            produce = p.get('produce')
            targets = p.get('affected_destination_ids') or list(dests)
            for did in targets:
                d = dests.get(did)
                if not d:
                    continue
                for pr in (d['price_per_kg'] or {}):
                    if produce is None or pr == produce:
                        d['price_per_kg'][pr] = float(d['price_per_kg'][pr]) * mult
        elif dtype == 'shelf_life_shock':
            delta = float(p.get('shelf_life_delta_days', 0.0))
            for bid in p.get('affected_batch_ids', []):
                b = batches.get(bid)
                if b:
                    b['shelf_life_days'] = max(0.0, float(b['shelf_life_days']) + delta)
    return s


# --- expiry / price / demand helpers -------------------------------------

def age_at_horizon(scenario, batch):
    return float(scenario['horizon_days']) - float(batch['harvest_day'])


def remaining_at_horizon(scenario, batch):
    return float(batch['shelf_life_days']) - age_at_horizon(scenario, batch)


def price_basis(scenario, batch, dest, produce):
    """Selling price for a produce at a destination.

    CONTRADICTION-1: §2.1 writes `base_price_per_kg x (1 - disc/100)` but the
    §8 example equals the destination's `price_per_kg` (30.0), not the batch
    base (25.0). We use the destination price with the batch base as fallback
    so revenue reflects the point of sale. Documented in ASSUMPTIONS.md.
    """
    prices = dest.get('price_per_kg') or {}
    if produce in prices:
        return float(prices[produce])
    return float(batch['base_price_per_kg'])


def discount_factor(discount_pct):
    return 1.0 - float(discount_pct) / 100.0


def effective_price(scenario, batch, dest, produce, discount_pct):
    return price_basis(scenario, batch, dest, produce) * discount_factor(discount_pct)


def effective_demand_kg(demand_kg, discount_pct, dr_config):
    """§2.2 demand response. Off (default) => no extra demand from discounting."""
    if not dr_config.get('enabled') or float(dr_config.get('discount_elasticity', 0.0)) == 0.0:
        return float(demand_kg)
    grown = float(demand_kg) * (1.0 + float(dr_config['discount_elasticity']) * float(discount_pct) / 100.0)
    capped = float(demand_kg) * float(dr_config.get('max_demand_multiplier', 1.0))
    return min(grown, capped)


def supported_demand_kg(scenario):
    """§6.3: total base demand of supported retail/wholesale destinations only."""
    total = 0.0
    for dest in scenario['destinations']:
        if dest['type'] in SUPPORTED_DESTINATION_TYPES:
            for v in (dest['demand'] or {}).values():
                total += float(v)
    return total


def effective_demand_map(scenario, discount_map=None):
    """(dest_id, produce) -> effective demand kg. discount_map optional (§2.2)."""
    dr = config_of(scenario)['demand_response']
    out = {}
    for dest in scenario['destinations']:
        if dest['type'] not in SUPPORTED_DESTINATION_TYPES:
            continue
        for produce, kg in (dest['demand'] or {}).items():
            disc = 0.0
            if discount_map:
                disc = discount_map.get((dest['destination_id'], produce), 0.0)
            out[(dest['destination_id'], produce)] = effective_demand_kg(kg, disc, dr)
    return out


# --- dispatch construction ----------------------------------------------

def _batch_index(scenario):
    return {b['batch_id']: b for b in scenario['batches']}


def _dest_index(scenario):
    return {d['destination_id']: d for d in scenario['destinations']}


def build_dispatches(scenario, flows):
    """Turn raw planned flows into §8 Dispatch dicts with §5 cost attribution.

    A flow is a dict: {batch_id, destination_id, quantity_kg, discount_pct,
    reason?}. Sales are allocated deterministically (§12) per destination and
    produce: highest effective price first, then destination_id, batch_id,
    earliest expiry. Internal values are UNROUNDED (rounding happens once at
    the §8 output boundary).
    """
    cfg = config_of(scenario)
    batches = _batch_index(scenario)
    dests = _dest_index(scenario)
    min_life = float(cfg['min_arrival_shelf_life_days'])
    dispatch_day = float(scenario['dispatch_day'])
    horizon = float(scenario['horizon_days'])
    tr_rate = float(scenario['cost_model']['transport_per_kg_km'])
    hd_rate = float(scenario['cost_model']['handling_per_kg'])

    # Streams grouped per (destination, produce); each carries its own discount.
    by_dp = {}
    ordered = []
    for i, f in enumerate(flows):
        b = batches[f['batch_id']]
        d = dests[f['destination_id']]
        produce = b['produce']
        eff = effective_price(scenario, b, d, produce, f['discount_pct'])
        remain = float(b['shelf_life_days']) - (dispatch_day - float(b['harvest_day'])) - float(d['transit_days'])
        stream = {
            'idx': i, 'flow': f, 'batch': b, 'dest': d, 'produce': produce,
            'eff': eff, 'remaining_at_arrival': remain,
            'remaining_at_dispatch': float(b['shelf_life_days']) - (dispatch_day - float(b['harvest_day'])),
        }
        by_dp.setdefault((d['destination_id'], produce), []).append(stream)
        ordered.append(stream)

    # §12 sales allocation order within each (destination, produce).
    sold = {}
    for (_did, _pr), streams in by_dp.items():
        streams.sort(key=lambda s: (-s['eff'], s['dest']['destination_id'],
                                    s['batch']['batch_id'], s['remaining_at_dispatch']))
        remaining = effective_demand_kg(
            streams[0]['dest']['demand'].get(_pr, 0.0), streams[0]['flow']['discount_pct'],
            cfg['demand_response'])
        for s in streams:
            take = min(float(s['flow']['quantity_kg']), remaining)
            sold[s['idx']] = take
            remaining -= take

    dispatches = []
    for s in ordered:
        f = s['flow']
        b = s['batch']
        d = s['dest']
        produce = s['produce']
        qty = float(f['quantity_kg'])
        sold_kg = sold.get(s['idx'], 0.0)
        arrived_unsold = qty - sold_kg
        gross = sold_kg * s['eff']
        procurement = sold_kg * float(b['unit_cost_per_kg'])
        transport = qty * float(d['distance_km']) * tr_rate
        handling = qty * hd_rate
        dispatch = {
            'batch_id': b['batch_id'],
            'destination_id': d['destination_id'],
            'dispatch_day': dispatch_day,
            'quantity_kg': qty,
            'discount_pct': float(f['discount_pct']),
            'age_at_dispatch_days': dispatch_day - float(b['harvest_day']),
            'remaining_at_arrival_days': s['remaining_at_arrival'],
            'effective_price_per_kg': s['eff'],
            'sold_kg': sold_kg,
            'arrived_unsold_kg': arrived_unsold,
            'gross_revenue': gross,
            'procurement_cost': procurement,
            'transport_cost': transport,
            'handling_cost': handling,
            'expected_contribution': gross - procurement - transport - handling,
            'reason': f.get('reason', ''),
        }
        dispatches.append(dispatch)
    return dispatches


# --- feasibility (§11) ---------------------------------------------------

def feasibility_violations(scenario, dispatches):
    """Applicable §11 checks. Returns list of {code, message, batch_id?, destination_id?}."""
    cfg = config_of(scenario)
    batches = _batch_index(scenario)
    dests = _dest_index(scenario)
    min_life = float(cfg['min_arrival_shelf_life_days'])
    horizon = float(scenario['horizon_days'])
    dispatch_day = float(scenario['dispatch_day'])
    max_disc = float(cfg['discount']['eligible_max_pct'])
    step = float(cfg['discount']['step_pct'])
    v = []

    def add(code, message, batch_id=None, destination_id=None):
        entry = {'code': code, 'message': message}
        if batch_id is not None:
            entry['batch_id'] = batch_id
        if destination_id is not None:
            entry['destination_id'] = destination_id
        v.append(entry)

    for d in scenario['destinations']:
        if d['type'] not in SUPPORTED_DESTINATION_TYPES:
            add('unsupported_destination_type',
                f"destination type {d['type']!r} is not supported in v1",
                destination_id=d['destination_id'])
        if float(d['capacity_kg']) < 0:
            add('negative_quantity', f"destination capacity_kg is negative ({d['capacity_kg']})",
                destination_id=d['destination_id'])

    for b in scenario['batches']:
        if float(b['quantity_kg']) < 0:
            add('negative_quantity', f"batch quantity_kg is negative ({b['quantity_kg']})",
                batch_id=b['batch_id'])

    disc_map = {}
    disp_by_batch = {}
    disp_by_dest = {}
    for d in dispatches:
        bid = d.get('batch_id')
        did = d.get('destination_id')
        if bid not in batches:
            add('unknown_reference', f"dispatch references unknown batch_id {bid!r}", batch_id=bid)
            continue
        if did not in dests:
            add('unknown_reference', f"dispatch references unknown destination_id {did!r}",
                destination_id=did)
            continue
        b = batches[bid]
        dest = dests[did]
        produce = b['produce']
        if produce not in (dest['demand'] or {}):
            add('unknown_reference',
                f"produce {produce!r} is not in destination {did} demand",
                batch_id=bid, destination_id=did)
        for f in ('quantity_kg', 'sold_kg', 'arrived_unsold_kg'):
            if float(d.get(f, 0.0)) < 0:
                add('negative_quantity', f"dispatch {f} is negative ({d.get(f)})",
                    batch_id=bid, destination_id=did)
        disp_by_batch[bid] = disp_by_batch.get(bid, 0.0) + float(d.get('quantity_kg', 0.0))
        disp_by_dest[did] = disp_by_dest.get(did, 0.0) + float(d.get('quantity_kg', 0.0))

        remain = float(d.get('remaining_at_arrival_days', 0.0))
        if remain < min_life - TOLERANCE_KG:
            add('shelf_life_expired',
                f"remaining_at_arrival_days {remain} < min {min_life}",
                batch_id=bid, destination_id=did)
        if dispatch_day + float(dest['transit_days']) > horizon + TOLERANCE_KG:
            add('arrival_after_horizon',
                f"dispatch_day+transit_days {dispatch_day + float(dest['transit_days'])} > horizon {horizon}",
                batch_id=bid, destination_id=did)

        dp = float(d.get('discount_pct', 0.0))
        if dp < -TOLERANCE_KG or dp > max_disc + TOLERANCE_KG:
            add('discount_out_of_range', f"discount_pct {dp} outside [0, {max_disc}]",
                batch_id=bid, destination_id=did)
        elif step > 0 and abs(round(dp / step) * step - dp) > TOLERANCE_KG:
            add('discount_step_mismatch', f"discount_pct {dp} not on {step} grid",
                batch_id=bid, destination_id=did)
        key = (did, produce)
        disc_map[key] = max(disc_map.get(key, 0.0), dp)

    # inventory_exceeded (§11)
    for b in scenario['batches']:
        used = disp_by_batch.get(b['batch_id'], 0.0)
        if used > float(b['quantity_kg']) + TOLERANCE_KG:
            add('inventory_exceeded',
                f"dispatched {used} > harvested {b['quantity_kg']}", batch_id=b['batch_id'])
    # capacity_exceeded (§11)
    for dest in scenario['destinations']:
        used = disp_by_dest.get(dest['destination_id'], 0.0)
        if used > float(dest['capacity_kg']) + TOLERANCE_KG:
            add('capacity_exceeded',
                f"allocated {used} > capacity {dest['capacity_kg']}",
                destination_id=dest['destination_id'])
    # demand_exceeded (§11) per destination/produce
    eff = effective_demand_map(scenario, disc_map)
    sold_by_dp = {}
    for d in dispatches:
        bid = d.get('batch_id')
        did = d.get('destination_id')
        if bid in batches and did in dests:
            produce = batches[bid]['produce']
            sold_by_dp[(did, produce)] = sold_by_dp.get((did, produce), 0.0) + float(d.get('sold_kg', 0.0))
    for key, s in sold_by_dp.items():
        allowed = eff.get(key, 0.0)
        if s > allowed + TOLERANCE_KG:
            add('demand_exceeded',
                f"sold {s} for {key[1]!r} at {key[0]} > effective demand {allowed}",
                destination_id=key[0])
    # §6.3: selling against zero supported demand
    total_demand = supported_demand_kg(scenario)
    total_sold = sum(float(d.get('sold_kg', 0.0)) for d in dispatches)
    if total_demand == 0.0 and total_sold > 0.0:
        add('demand_exceeded', 'sold_kg > 0 while supported demand_kg == 0 (§6.3)')
    # inventory_not_conserved (§1.1) — checked per batch in aggregate; here for completeness
    for b in scenario['batches']:
        pass
    return v


# --- aggregation (§6, §8) ------------------------------------------------

def _spoilage_rate(scenario, batch):
    """§5.1a / U2: scenario-wide penalty if provided, else the batch unit cost."""
    cm = scenario['cost_model']
    if 'spoilage_penalty_per_kg' in cm:
        return float(cm['spoilage_penalty_per_kg'])
    return float(batch['unit_cost_per_kg'])


def _terminal_state(scenario, batch, sold_kg):
    """§1.1 / §1.4: split unsold kg into fresh vs spoiled by expiry at horizon."""
    harvested = float(batch['quantity_kg'])
    sold = min(float(sold_kg), harvested)
    unsold = harvested - sold
    remaining = remaining_at_horizon(scenario, batch)
    if remaining >= 0:
        return harvested, sold, unsold, 0.0
    return harvested, sold, 0.0, unsold


def aggregate(scenario, dispatches=None):
    """Build (Metrics, BatchSummary, Reconciliation) for one strategy per §8."""
    validate_scenario(scenario)
    batches = scenario['batches']
    dispatches = dispatches or []

    metrics = {
        'harvested_kg': 0.0, 'dispatched_kg': 0.0, 'sold_kg': 0.0, 'arrived_unsold_kg': 0.0,
        'fresh_inventory_kg': 0.0, 'spoiled_kg': 0.0, 'demand_kg': 0.0,
        'gross_revenue': 0.0, 'procurement_cost': 0.0, 'transport_cost': 0.0,
        'handling_cost': 0.0, 'spoilage_cost': 0.0, 'net_revenue': 0.0,
        'fulfillment_pct': 0.0, 'feasible': True, 'violations': [],
    }
    sum_contributions = 0.0
    dispatched_by_batch, sold_by_batch, arrived_unsold_by_batch = {}, {}, {}
    for d in dispatches:
        metrics['dispatched_kg'] += float(d.get('quantity_kg', 0.0))
        metrics['sold_kg'] += float(d.get('sold_kg', 0.0))
        metrics['arrived_unsold_kg'] += float(d.get('arrived_unsold_kg', 0.0))
        metrics['gross_revenue'] += float(d.get('gross_revenue', 0.0))
        metrics['procurement_cost'] += float(d.get('procurement_cost', 0.0))
        metrics['transport_cost'] += float(d.get('transport_cost', 0.0))
        metrics['handling_cost'] += float(d.get('handling_cost', 0.0))
        sum_contributions += float(d.get('expected_contribution', 0.0))
        bid = d.get('batch_id')
        dispatched_by_batch[bid] = dispatched_by_batch.get(bid, 0.0) + float(d.get('quantity_kg', 0.0))
        sold_by_batch[bid] = sold_by_batch.get(bid, 0.0) + float(d.get('sold_kg', 0.0))
        arrived_unsold_by_batch[bid] = arrived_unsold_by_batch.get(bid, 0.0) + float(d.get('arrived_unsold_kg', 0.0))

    spoilage_cost = 0.0
    batch_summary = []
    conserved = True
    for b in batches:
        bid = b['batch_id']
        harvested, sold, fresh, spoiled = _terminal_state(scenario, b, sold_by_batch.get(bid, 0.0))
        spoilage_cost += spoiled * _spoilage_rate(scenario, b)
        metrics['harvested_kg'] += harvested
        metrics['fresh_inventory_kg'] += fresh
        metrics['spoiled_kg'] += spoiled
        if abs(harvested - (sold + fresh + spoiled)) > TOLERANCE_KG:
            conserved = False
        batch_summary.append({
            'batch_id': bid,
            'harvested_kg': round(harvested, 3),
            'dispatched_kg': round(dispatched_by_batch.get(bid, 0.0), 3),
            'sold_kg': round(sold, 3),
            'arrived_unsold_kg': round(arrived_unsold_by_batch.get(bid, 0.0), 3),
            'fresh_inventory_kg': round(fresh, 3),
            'spoiled_kg': round(spoiled, 3),
        })

    metrics['demand_kg'] = supported_demand_kg(scenario)
    metrics['spoilage_cost'] = spoilage_cost
    # §5.3 / §6.2: net_revenue = gross - procurement - transport - handling - spoilage
    metrics['net_revenue'] = (metrics['gross_revenue'] - metrics['procurement_cost']
                              - metrics['transport_cost'] - metrics['handling_cost'] - spoilage_cost)
    net_revenue = metrics['net_revenue']

    demand = metrics['demand_kg']
    metrics['fulfillment_pct'] = 100.0 if demand == 0 else min(100.0, metrics['sold_kg'] / demand * 100.0)

    # §5.3 identity on UNROUNDED internal values (mission default: reconcile unrounded).
    check_ok = abs(net_revenue - (sum_contributions - spoilage_cost)) <= TOLERANCE_INR

    for k in ('harvested_kg', 'dispatched_kg', 'sold_kg', 'arrived_unsold_kg',
              'fresh_inventory_kg', 'spoiled_kg', 'demand_kg'):
        metrics[k] = round(metrics[k], 3)
    for k in ('gross_revenue', 'procurement_cost', 'transport_cost', 'handling_cost',
              'spoilage_cost', 'net_revenue'):
        metrics[k] = round(metrics[k], 2)
    metrics['fulfillment_pct'] = round(metrics['fulfillment_pct'], 2)

    reconciliation = {
        'sum_dispatch_contributions': round(sum_contributions, 2),
        'spoilage_cost': metrics['spoilage_cost'],
        'net_revenue': metrics['net_revenue'],
        'check_ok': check_ok,
    }

    violations = feasibility_violations(scenario, dispatches)
    if not conserved:
        violations.append({'code': 'inventory_not_conserved',
                           'message': '§1.1 identity failed for at least one batch'})
    if not check_ok:
        violations.append({'code': 'cost_reconciliation_failed',
                           'message': '§5.3 identity failed beyond ₹0.01'})
    metrics['violations'] = violations
    metrics['feasible'] = len(violations) == 0

    return metrics, batch_summary, reconciliation


_ROUND_KG_KEYS = ('quantity_kg', 'sold_kg', 'arrived_unsold_kg',
                  'age_at_dispatch_days', 'remaining_at_arrival_days')
_ROUND_INR_KEYS = ('effective_price_per_kg', 'gross_revenue', 'procurement_cost',
                   'transport_cost', 'handling_cost', 'expected_contribution')


def round_dispatch(d):
    """§0.1 output precision. Internal reconciliation used unrounded values."""
    out = dict(d)
    for k in _ROUND_KG_KEYS:
        if k in out:
            out[k] = round(out[k], 3)
    for k in _ROUND_INR_KEYS:
        if k in out:
            out[k] = round(out[k], 2)
    if 'discount_pct' in out:
        out['discount_pct'] = round(out['discount_pct'], 2)
    return out


def run_strategy(scenario, dispatches, strategy_name):
    """One §8 per-strategy block."""
    metrics, batch_summary, reconciliation = aggregate(scenario, dispatches)
    return {
        'strategy': strategy_name,
        'dispatches': [round_dispatch(d) for d in dispatches],
        'metrics': metrics,
        'batch_summary': batch_summary,
        'reconciliation': reconciliation,
    }


# --- improvement + result assembly (§8, §9.4) ----------------------------

def compute_improvement(baseline_metrics, planner_metrics):
    """§8/§9.4 improvement block. delta_pct null when |baseline| < eps."""
    # §8 names the improvement key 'spoilage_kg' while the metric is 'spoiled_kg'.
    spec = (('net_revenue', 'net_revenue', 'higher_better'),
            ('spoilage_kg', 'spoiled_kg', 'lower_better'),
            ('fulfillment_pct', 'fulfillment_pct', 'higher_better'))
    out = {}
    for key, metric_key, direction in spec:
        b = baseline_metrics[metric_key]
        p = planner_metrics[metric_key]
        delta = p - b
        if abs(b) < EPS_PCT:
            delta_pct = None
        else:
            delta_pct = delta / abs(b) * 100.0
        out[key] = {
            'baseline': b, 'planner': p,
            'delta': round(delta, 4),
            'delta_pct': None if delta_pct is None else round(delta_pct, 4),
            'direction': direction,
        }
    return out


def build_result(scenario, baseline_dispatches, planner_dispatches, generated_by):
    """Assemble the §8 top-level result.json object."""
    baseline = run_strategy(scenario, baseline_dispatches, 'baseline')
    planner = run_strategy(scenario, planner_dispatches, 'planner')
    return {
        'schema_version': SCHEMA_VERSION,
        'scenario_id': scenario['scenario_id'],
        'seed': scenario['seed'],
        'fixture': scenario.get('fixture', False),
        'generated_by': generated_by,
        'units': scenario.get('units', DEFAULT_UNITS),
        'results': {'baseline': baseline, 'planner': planner},
        'improvement': compute_improvement(baseline['metrics'], planner['metrics']),
    }
