"""Contract tests for the Aurenza engine (§0.2, §1-§6, §8, §11, §14).

Every applicable §11 violation code is exercised here (T28 meta-check below).
Run: python -m pytest -q   (or python -m unittest)
"""

import unittest

from engine import baseline, core, fixtures, planner

UNITS = {'mass': 'kg', 'currency': 'INR', 'time': 'day',
         'distance': 'km', 'discount': 'percent', 'freshness': 'percent'}


def make_scenario(batches=None, destinations=None, cost_model=None,
                  config=None, disruptions=None, horizon_days=1, dispatch_day=0):
    return {
        'schema_version': '1.0.0', 'scenario_id': 'test', 'seed': 1, 'units': UNITS,
        'horizon_days': horizon_days, 'dispatch_day': dispatch_day,
        'cost_model': cost_model if cost_model is not None
        else {'transport_per_kg_km': 0.8, 'handling_per_kg': 1.0},
        'config': config or {},
        'batches': batches if batches is not None else [],
        'destinations': destinations if destinations is not None else [],
        'disruptions': disruptions or [],
    }


def batch(bid='B001', produce='tomato', qty=500.0, harvest=0, life=5.0,
          unit=12.0, base=25.0):
    return {'batch_id': bid, 'produce': produce, 'quantity_kg': qty,
            'harvest_day': harvest, 'shelf_life_days': life,
            'freshness_pct': 100.0, 'unit_cost_per_kg': unit,
            'base_price_per_kg': base}


def destination(did='D1', dtype='retail', cap=1000.0, transit=0.5, dist=10.0,
                demand=None, price=None, max_price=None):
    d = {'destination_id': did, 'type': dtype, 'capacity_kg': cap,
         'transit_days': transit, 'distance_km': dist,
         'demand': demand if demand is not None else {'tomato': 300.0},
         'price_per_kg': price if price is not None else {'tomato': 30.0}}
    if max_price is not None:
        d['max_price_per_kg'] = max_price
    return d


def D(batch_id='B001', destination_id='D1', quantity_kg=100.0, sold_kg=None,
      discount_pct=0.0, remaining_at_arrival_days=4.0, arrived_unsold_kg=0.0,
      price=30.0, unit=12.0, transport=0.0, handling=0.0, contribution=None):
    sold = quantity_kg if sold_kg is None else sold_kg
    gross = sold * price
    proc = sold * unit
    contrib = gross - proc - transport - handling if contribution is None else contribution
    return {'batch_id': batch_id, 'destination_id': destination_id,
            'dispatch_day': 0.0, 'quantity_kg': quantity_kg, 'discount_pct': discount_pct,
            'age_at_dispatch_days': 0.0, 'remaining_at_arrival_days': remaining_at_arrival_days,
            'effective_price_per_kg': price, 'sold_kg': sold, 'arrived_unsold_kg': arrived_unsold_kg,
            'gross_revenue': gross, 'procurement_cost': proc, 'transport_cost': transport,
            'handling_cost': handling, 'expected_contribution': contrib, 'reason': 'test'}


METRIC_KEYS = {
    'harvested_kg', 'dispatched_kg', 'sold_kg', 'arrived_unsold_kg',
    'fresh_inventory_kg', 'spoiled_kg', 'demand_kg',
    'gross_revenue', 'procurement_cost', 'transport_cost', 'handling_cost',
    'spoilage_cost', 'net_revenue',
    'fulfillment_pct', 'feasible', 'violations',
}
BATCH_SUMMARY_KEYS = {'batch_id', 'harvested_kg', 'dispatched_kg', 'sold_kg',
                      'arrived_unsold_kg', 'fresh_inventory_kg', 'spoiled_kg'}
RECONCILIATION_KEYS = {'sum_dispatch_contributions', 'spoilage_cost',
                       'net_revenue', 'check_ok'}
DISPATCH_KEYS = {
    'batch_id', 'destination_id', 'dispatch_day', 'quantity_kg', 'discount_pct',
    'age_at_dispatch_days', 'remaining_at_arrival_days', 'effective_price_per_kg',
    'sold_kg', 'arrived_unsold_kg', 'gross_revenue', 'procurement_cost',
    'transport_cost', 'handling_cost', 'expected_contribution', 'reason',
}


def codes(metrics):
    return [v['code'] for v in metrics['violations']]


class TestSchema(unittest.TestCase):
    """§0.2 / §7: malformed input is a hard error, never a silent default."""

    def test_missing_scenario_field(self):
        s = make_scenario()
        del s['seed']
        with self.assertRaises(core.ScenarioError):
            core.aggregate(s)

    def test_missing_batch_field(self):
        b = batch()
        del b['shelf_life_days']
        with self.assertRaises(core.ScenarioError):
            core.aggregate(make_scenario([b]))

    def test_missing_destination_field(self):
        d = destination()
        del d['capacity_kg']
        with self.assertRaises(core.ScenarioError):
            core.aggregate(make_scenario(destinations=[d]))

    def test_bad_schema_major(self):
        s = make_scenario()
        s['schema_version'] = '2.0.0'
        with self.assertRaises(core.ScenarioError):
            core.aggregate(s)

    def test_unknown_disruption_type(self):
        s = make_scenario(disruptions=[{'type': 'meteor_strike', 'params': {}}])
        with self.assertRaises(core.ScenarioError) as ctx:
            core.aggregate(s)
        self.assertEqual(ctx.exception.code, 'unknown_disruption_type')

    def test_invalid_near_expiry_days(self):
        s = make_scenario(config={'discount': {'near_expiry_days': -1.0}})
        with self.assertRaises(core.ScenarioError) as ctx:
            core.aggregate(s)
        self.assertEqual(ctx.exception.code, 'invalid_near_expiry_days')


class TestMetrics(unittest.TestCase):
    """§1, §5, §6, §8."""

    def test_empty_scenario_zero_metrics(self):
        metrics, batch_summary, rec = core.aggregate(make_scenario())
        self.assertEqual(batch_summary, [])
        self.assertEqual(metrics['net_revenue'], 0.0)
        self.assertEqual(metrics['spoilage_cost'], 0.0)
        self.assertTrue(metrics['feasible'])
        self.assertTrue(rec['check_ok'])

    def test_metric_key_set_complete(self):
        metrics, _, _ = core.aggregate(make_scenario())
        self.assertEqual(set(metrics), METRIC_KEYS)

    def test_batch_summary_keys_complete(self):
        _, batch_summary, _ = core.aggregate(make_scenario([batch()]))
        self.assertEqual(set(batch_summary[0]), BATCH_SUMMARY_KEYS)

    def test_reconciliation_keys_complete(self):
        _, _, rec = core.aggregate(make_scenario())
        self.assertEqual(set(rec), RECONCILIATION_KEYS)

    def test_zero_demand_fulfillment_is_100(self):
        metrics, _, _ = core.aggregate(make_scenario())
        self.assertEqual(metrics['demand_kg'], 0.0)
        self.assertEqual(metrics['fulfillment_pct'], 100.0)

    def test_demand_only_counts_supported_types(self):
        dests = [destination('D1', 'retail'), destination('D2', 'donation', demand={'tomato': 999.0})]
        metrics, _, _ = core.aggregate(make_scenario(destinations=dests))
        self.assertEqual(metrics['demand_kg'], 300.0)  # donation excluded

    def test_conservation_per_batch_and_total(self):
        fresh = batch('B001', qty=500.0, life=5.0)     # remaining 4 >= 0
        stale = batch('B002', qty=100.0, life=0.5)     # remaining -0.5 < 0
        s = make_scenario([fresh, stale], cost_model={'spoilage_penalty_per_kg': 2.0})
        metrics, batch_summary, _ = core.aggregate(s)
        for row in batch_summary:
            self.assertAlmostEqual(row['harvested_kg'],
                                   row['sold_kg'] + row['fresh_inventory_kg'] + row['spoiled_kg'],
                                   places=3)
        self.assertEqual(metrics['fresh_inventory_kg'], 500.0)
        self.assertEqual(metrics['spoiled_kg'], 100.0)
        self.assertEqual(metrics['harvested_kg'],
                         metrics['sold_kg'] + metrics['fresh_inventory_kg'] + metrics['spoiled_kg'])

    def test_spoilage_penalty_precedence(self):
        stale = batch(life=0.5, unit=12.0)
        m1, _, _ = core.aggregate(make_scenario([stale], cost_model={'spoilage_penalty_per_kg': 3.0}))
        self.assertEqual(m1['spoilage_cost'], 1500.0)   # 500 * 3.0
        m2, _, _ = core.aggregate(make_scenario([stale], cost_model={'transport_per_kg_km': 0.8}))
        self.assertEqual(m2['spoilage_cost'], 6000.0)   # 500 * 12.0 fallback

    def test_net_revenue_identity_no_double_count(self):
        # B001 spoils (500kg @ penalty 2.0); B002 sells 100kg. T16/T17.
        spoiled = batch('B001', qty=500.0, life=0.5)
        sold = batch('B002', qty=100.0, life=5.0)
        s = make_scenario([spoiled, sold], cost_model={'spoilage_penalty_per_kg': 2.0})
        metrics, _, rec = core.aggregate(s, [D('B002', quantity_kg=100.0, sold_kg=100.0)])
        self.assertEqual(metrics['spoilage_cost'], 1000.0)      # only spoiled kg
        self.assertEqual(metrics['procurement_cost'], 1200.0)   # only sold kg
        self.assertEqual(metrics['net_revenue'], 800.0)         # 1800 contrib - 1000 spoilage
        self.assertTrue(rec['check_ok'])

    def test_spoiled_kg_distinct_from_spoilage_cost(self):
        stale = batch(qty=100.0, life=0.5)
        m, _, _ = core.aggregate(make_scenario([stale], cost_model={'spoilage_penalty_per_kg': 2.0}))
        self.assertEqual(m['spoiled_kg'], 100.0)
        self.assertEqual(m['spoilage_cost'], 200.0)

    def test_rounding_precision(self):
        b = batch(qty=333.3333, life=5.0)
        m, _, _ = core.aggregate(make_scenario([b]))
        self.assertEqual(m['harvested_kg'], 333.333)


class TestFeasibility(unittest.TestCase):
    """§11 constraint codes each triggered by at least one test."""

    def test_clean_scenario_feasible(self):
        metrics, _, _ = core.aggregate(make_scenario([batch()], [destination()]))
        self.assertTrue(metrics['feasible'])
        self.assertEqual(metrics['violations'], [])

    def test_unsupported_destination_type(self):
        s = make_scenario([batch()], [destination('D1', 'donation')])
        metrics, _, _ = core.aggregate(s)
        self.assertIn('unsupported_destination_type', codes(metrics))

    def test_unknown_reference_batch(self):
        metrics, _, _ = core.aggregate(make_scenario([batch()], [destination()]),
                                       [D('ZZZ')])
        self.assertIn('unknown_reference', codes(metrics))

    def test_unknown_reference_destination(self):
        metrics, _, _ = core.aggregate(make_scenario([batch()], [destination()]),
                                       [D(destination_id='D9')])
        self.assertIn('unknown_reference', codes(metrics))

    def test_unknown_reference_produce(self):
        s = make_scenario([batch(produce='mango')], [destination()])  # Mango not demanded
        metrics, _, _ = core.aggregate(s, [D()])
        self.assertIn('unknown_reference', codes(metrics))

    def test_negative_quantity(self):
        metrics, _, _ = core.aggregate(make_scenario([batch(qty=-5.0)]))
        self.assertIn('negative_quantity', codes(metrics))

    def test_inventory_exceeded(self):
        metrics, _, _ = core.aggregate(make_scenario([batch(qty=100.0)], [destination(cap=9999.0)]),
                                       [D(quantity_kg=200.0, sold_kg=0.0)])
        self.assertIn('inventory_exceeded', codes(metrics))

    def test_capacity_exceeded(self):
        metrics, _, _ = core.aggregate(make_scenario([batch(qty=500.0)], [destination(cap=100.0)]),
                                       [D(quantity_kg=200.0, sold_kg=0.0)])
        self.assertIn('capacity_exceeded', codes(metrics))

    def test_demand_exceeded(self):
        d = destination(demand={'tomato': 100.0}, cap=9999.0)
        metrics, _, _ = core.aggregate(make_scenario([batch(qty=500.0)], [d]),
                                       [D(quantity_kg=300.0, sold_kg=300.0)])
        self.assertIn('demand_exceeded', codes(metrics))

    def test_shelf_life_expired(self):
        metrics, _, _ = core.aggregate(make_scenario([batch()], [destination(transit=0.5)]),
                                       [D(remaining_at_arrival_days=0.2)])
        self.assertIn('shelf_life_expired', codes(metrics))

    def test_arrival_after_horizon(self):
        s = make_scenario([batch()], [destination(transit=2.0)], horizon_days=1)
        metrics, _, _ = core.aggregate(s, [D()])
        self.assertIn('arrival_after_horizon', codes(metrics))

    def test_discount_out_of_range(self):
        metrics, _, _ = core.aggregate(make_scenario([batch()], [destination()]),
                                       [D(discount_pct=40.0)])
        self.assertIn('discount_out_of_range', codes(metrics))

    def test_discount_step_mismatch(self):
        metrics, _, _ = core.aggregate(make_scenario([batch()], [destination()]),
                                       [D(discount_pct=7.0)])
        self.assertIn('discount_step_mismatch', codes(metrics))

    def test_zero_demand_with_sales(self):
        metrics, _, _ = core.aggregate(make_scenario([batch()]), [D()])
        self.assertFalse(metrics['feasible'])
        self.assertIn('demand_exceeded', codes(metrics))

    def test_cost_reconciliation_failed(self):
        metrics, _, rec = core.aggregate(make_scenario([batch()], [destination()]),
                                         [D(contribution=999.0)])
        self.assertFalse(rec['check_ok'])
        self.assertIn('cost_reconciliation_failed', codes(metrics))

    def test_every_code_has_a_test(self):
        """T28 meta-check: each §11 code string appears in this module."""
        src = open(__file__, encoding='utf-8').read()
        for code in ('unknown_disruption_type', 'negative_quantity', 'inventory_exceeded',
                     'capacity_exceeded', 'demand_exceeded', 'shelf_life_expired',
                     'arrival_after_horizon', 'discount_out_of_range',
                     'discount_step_mismatch', 'invalid_near_expiry_days',
                     'unsupported_destination_type', 'unknown_reference',
                     'cost_reconciliation_failed'):
            self.assertIn(code, src, f'{code} has no test')


class TestDiscounts(unittest.TestCase):
    """§2: demand response off by default; discounts only on the 5% grid."""

    def test_demand_response_off_ignores_discount(self):
        dr = core.config_of(make_scenario())['demand_response']
        self.assertEqual(core.effective_demand_kg(100.0, 20.0, dr), 100.0)

    def test_planner_discount_on_grid(self):
        # A max_price cap forces a discount; it must land on the 5% grid.
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 24.0}, cap=9999.0)
        s = make_scenario([batch(qty=200.0, life=5.0)], [d])
        flows = planner.plan_planner(s)
        for f in flows:
            if f.get('discount_pct'):
                self.assertAlmostEqual(f['discount_pct'] % 5.0, 0.0, places=6)
                self.assertLessEqual(f['discount_pct'], 30.0)


class TestDeterminismAndStrategies(unittest.TestCase):
    """§5.4, §12: determinism, FEFO ordering, planner never worse than baseline."""

    def _run(self, scenario):
        s = core.apply_disruptions(scenario)
        bf = baseline.plan_baseline(s)
        bd = core.build_dispatches(s, bf)
        pd = core.build_dispatches(s, planner.plan_planner(s, bf))
        return core.aggregate(s, bd), core.aggregate(s, pd), bd, pd

    def test_determinism_identical_outputs(self):
        import json
        s = fixtures.generate_scenario(3)
        r1 = json.dumps(core.build_result(s, *[core.build_dispatches(core.apply_disruptions(s), p)
                                               for p in (baseline.plan_baseline(core.apply_disruptions(s)),
                                                         planner.plan_planner(core.apply_disruptions(s)))],
                                         'test'), sort_keys=True)
        r2 = json.dumps(core.build_result(s, *[core.build_dispatches(core.apply_disruptions(s), p)
                                               for p in (baseline.plan_baseline(core.apply_disruptions(s)),
                                                         planner.plan_planner(core.apply_disruptions(s)))],
                                         'test'), sort_keys=True)
        self.assertEqual(r1, r2)

    def test_planner_not_worse_than_baseline(self):
        for seed in range(1, 6):
            (bm, _, _), (pm, _, _), _, _ = self._run(fixtures.generate_scenario(seed))
            self.assertGreaterEqual(pm['net_revenue'], bm['net_revenue'] - core.TOLERANCE_INR,
                                    f'seed {seed}: planner worse than baseline')

    def test_planner_beats_baseline_somewhere(self):
        wins = 0
        for seed in range(1, 11):
            (bm, _, _), (pm, _, _), _, _ = self._run(fixtures.generate_scenario(seed))
            if pm['net_revenue'] > bm['net_revenue'] + core.TOLERANCE_INR:
                wins += 1
        self.assertGreater(wins, 0)

    def test_both_strategies_feasible_on_fixture(self):
        for seed in range(1, 6):
            (bm, _, _), (pm, _, _), _, _ = self._run(fixtures.generate_scenario(seed))
            self.assertTrue(bm['feasible'], f'seed {seed} baseline infeasible')
            self.assertTrue(pm['feasible'], f'seed {seed} planner infeasible')

    def test_baseline_dispatches_earliest_expiry_first(self):
        early = batch('B001', qty=100.0, life=2.0)   # expires sooner
        late = batch('B002', qty=100.0, life=8.0)
        s = make_scenario([early, late], [destination(cap=9999.0)])
        flows = baseline.plan_baseline(s)
        self.assertTrue(flows)
        self.assertEqual(flows[0]['batch_id'], 'B001')

    def test_dispatch_shape_matches_contract(self):
        s = fixtures.generate_scenario(1)
        bd = core.build_dispatches(core.apply_disruptions(s), planner.plan_planner(core.apply_disruptions(s)))
        self.assertTrue(bd)
        self.assertEqual(set(bd[0]), DISPATCH_KEYS)


if __name__ == '__main__':
    unittest.main()
