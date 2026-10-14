"""Deterministic synthetic scenarios for the Aurenza demo and evaluation.

EVERYTHING HERE IS SYNTHETIC DEMO DATA, NOT OBSERVED REAL-WORLD VALUES.
Prices, demand, costs, shelf lives and distances are invented placeholders so
the engine can be demonstrated and tested deterministically. They must be
replaced with the team's real inputs (Iffa's A9 produce catalogue and market
data) before any results are presented as real. See docs/ASSUMPTIONS.md.

A batch of fixtures carries `fixture: true`; the disruption example mirrors the
§9 contract example shape ({type, params}).
"""

import random

from engine import core

# SYNTHETIC produce catalogue — placeholder shelf lives (days) and unit costs.
# NOT real data. A9 (Iffa) is open: these values are invented for the demo.
PRODUCE = {
    'tomato':  {'shelf_life_days': 5.0,  'unit_cost_per_kg': 12.0, 'base_price_per_kg': 25.0},
    'spinach': {'shelf_life_days': 2.8,  'unit_cost_per_kg': 20.0, 'base_price_per_kg': 40.0},
    'banana':  {'shelf_life_days': 6.0,  'unit_cost_per_kg': 15.0, 'base_price_per_kg': 30.0},
    'mango':   {'shelf_life_days': 4.0,  'unit_cost_per_kg': 35.0, 'base_price_per_kg': 70.0},
    'onion':   {'shelf_life_days': 20.0, 'unit_cost_per_kg': 8.0,  'base_price_per_kg': 18.0},
}
PRODUCE_NAMES = tuple(PRODUCE)

DESTINATIONS = (
    {'destination_id': 'D001', 'type': 'retail',    'name': 'City Retail',      'transit_days': 0.25, 'distance_km': 6.0},
    {'destination_id': 'D002', 'type': 'retail',    'name': 'Suburb Retail',    'transit_days': 0.5,  'distance_km': 18.0},
    {'destination_id': 'D003', 'type': 'wholesale', 'name': 'Wholesale Market', 'transit_days': 0.25, 'distance_km': 10.0},
    {'destination_id': 'D004', 'type': 'wholesale', 'name': 'Regional Depot',   'transit_days': 1.0,  'distance_km': 30.0},
)


def _destinations(rng, produce_names):
    dests = []
    for d in DESTINATIONS:
        demand = {p: float(rng.choice([0, 100, 200, 300, 450, 600])) for p in produce_names}
        price = {}
        for p in produce_names:
            base = PRODUCE[p]['base_price_per_kg']
            price[p] = round(base * rng.uniform(0.9, 1.3), 2)
        dest = dict(d)
        dest['capacity_kg'] = float(rng.choice([400, 600, 800, 1000, 1500]))
        dest['demand'] = demand
        dest['price_per_kg'] = price
        # Optional per §7; leave most destinations uncapped.
        if rng.random() < 0.3:
            p = rng.choice(produce_names)
            if demand[p] > 0:
                dest['max_price_per_kg'] = {p: round(price[p] * rng.uniform(0.75, 0.95), 2)}
        dests.append(dest)
    return dests


def _batches(rng, produce_names):
    batches = []
    n = rng.randint(3, 5)
    for i in range(n):
        produce = rng.choice(produce_names)
        spec = PRODUCE[produce]
        harvest = rng.choice([-2, -1, 0])
        shelf = max(0.5, spec['shelf_life_days'] + rng.choice([-1.0, -0.5, 0.0, 0.5]))
        batches.append({
            'batch_id': f'B{i + 1:03d}',
            'produce': produce,
            'quantity_kg': float(rng.choice([200, 350, 500, 700])),
            'harvest_day': harvest,
            'shelf_life_days': shelf,
            'freshness_pct': round(rng.uniform(70.0, 100.0), 2),
            'unit_cost_per_kg': spec['unit_cost_per_kg'],
            'base_price_per_kg': spec['base_price_per_kg'],
        })
    return batches


def generate_scenario(seed, disruptions=None):
    """Deterministic synthetic scenario for `seed` (fixture: true)."""
    rng = random.Random(seed)
    produce_names = list(PRODUCE_NAMES)
    return {
        'schema_version': core.SCHEMA_VERSION,
        'scenario_id': f'demo_seed_{seed}',
        'seed': seed,
        'fixture': True,
        'units': dict(core.DEFAULT_UNITS),
        'horizon_days': 1,
        'dispatch_day': 0,
        'cost_model': {
            'transport_per_kg_km': 0.8,
            'handling_per_kg': 1.0,
            'spoilage_penalty_per_kg': 2.0,
        },
        'config': {},
        'batches': _batches(rng, produce_names),
        'destinations': _destinations(rng, produce_names),
        'disruptions': disruptions or [],
    }


def disruptions_for(scenario):
    """Deterministic disruption scenarios derived from a base scenario (§7/§9)."""
    dests = [d['destination_id'] for d in scenario['destinations']]
    batches = [b['batch_id'] for b in scenario['batches']]
    out = []
    if dests:
        out.append({'type': 'transport_strike',
                    'params': {'affected_destination_ids': [dests[1] if len(dests) > 1 else dests[0]],
                               'capacity_multiplier': 0.0}})
        out.append({'type': 'demand_spike',
                    'params': {'affected_destination_ids': [dests[0]], 'demand_multiplier': 1.5}})
    if batches:
        out.append({'type': 'shelf_life_shock',
                    'params': {'affected_batch_ids': [batches[0]], 'shelf_life_delta_days': -1.0}})
    return out


def evaluation_scenarios():
    """Base + disruption scenarios for a seed range (used by run_eval)."""
    scenarios = []
    for seed in range(1, 31):
        base = generate_scenario(seed)
        scenarios.append((base, None))
        for dis in disruptions_for(base):
            scenarios.append((generate_scenario(seed, disruptions=[dis]), dis))
    return scenarios
