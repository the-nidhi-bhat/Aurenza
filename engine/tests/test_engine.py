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
        # A max_price cap forces a discount on a near-expiry batch (§2.3);
        # it must land on the 5% grid and stay within the eligible ceiling.
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 24.0},
                        transit=0.0, cap=9999.0)
        s = make_scenario([batch(qty=200.0, life=5.0, harvest=-4.5)], [d])
        flows = planner.plan_planner(s)
        discounts = [f['discount_pct'] for f in flows if f.get('discount_pct')]
        self.assertTrue(discounts, 'expected a near-expiry cap discount')
        for disc in discounts:
            self.assertAlmostEqual(disc % 5.0, 0.0, places=6)
            self.assertLessEqual(disc, 30.0)


class TestPriceCap(unittest.TestCase):
    """§2.5: a destination buys ``produce`` only when the post-discount
    ``effective_price_per_kg <= max_price_per_kg`` (inclusive); above the ceiling
    the sold quantity is 0. This is a sales rule, not a §11 infeasibility."""

    def _build(self, scenario, discount):
        b = scenario['batches'][0]
        d = scenario['destinations'][0]
        return core.build_dispatches(scenario, [{
            'batch_id': b['batch_id'], 'destination_id': d['destination_id'],
            'quantity_kg': b['quantity_kg'], 'discount_pct': discount,
        }])

    def _dispatches(self, scenario, strategy):
        s = core.apply_disruptions(scenario)
        flows = (planner.plan_planner(s) if strategy == 'planner'
                 else baseline.plan_baseline(s))
        return s, core.build_dispatches(s, flows)

    def _produce_of(self, scenario, dispatch):
        for b in scenario['batches']:
            if b['batch_id'] == dispatch['batch_id']:
                return b['produce']
        raise AssertionError('unknown batch ' + dispatch['batch_id'])

    def _assert_no_sale_above_cap(self, scenario, dispatches):
        for d in dispatches:
            produce = self._produce_of(scenario, d)
            cap = None
            for dest in scenario['destinations']:
                if dest['destination_id'] == d['destination_id']:
                    cap = core.max_price_for(dest, produce)
            if cap is not None and d['sold_kg'] > core.TOLERANCE_KG:
                self.assertLessEqual(
                    d['effective_price_per_kg'], cap + core.TOLERANCE_INR,
                    f"§2.5 sale above cap: {d['destination_id']} {produce} "
                    f"eff {d['effective_price_per_kg']} > cap {cap}")

    def test_supplied_reproduction_cap20_price30_sells_zero(self):
        # Reproduction: cap 20.0, effective price 30.0 -> sold quantity 0.
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 20.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        dp = self._build(s, 0.0)
        self.assertEqual(len(dp), 1)
        self.assertEqual(dp[0]['effective_price_per_kg'], 30.0)
        self.assertEqual(dp[0]['sold_kg'], 0.0)
        self.assertEqual(dp[0]['arrived_unsold_kg'], 300.0)
        self.assertEqual(dp[0]['gross_revenue'], 0.0)

    def test_price_below_cap_sells_fully(self):
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 40.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        self.assertEqual(self._build(s, 0.0)[0]['sold_kg'], 300.0)

    def test_price_equal_cap_is_inclusive(self):
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 30.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        self.assertEqual(self._build(s, 0.0)[0]['sold_kg'], 300.0)

    def test_price_above_cap_sells_zero(self):
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 20.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        self.assertEqual(self._build(s, 0.0)[0]['sold_kg'], 0.0)

    def test_discounted_candidate_within_cap_sells(self):
        # price 30, cap 24, discount 20% -> eff 24.0 == cap (inclusive) -> sells
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 24.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        dp = self._build(s, 20.0)
        self.assertAlmostEqual(dp[0]['effective_price_per_kg'], 24.0, places=6)
        self.assertEqual(dp[0]['sold_kg'], 300.0)

    def test_discounted_candidate_above_cap_sells_zero(self):
        # price 30, cap 24, discount 15% -> eff 25.5 > cap -> sold 0
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 24.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        dp = self._build(s, 15.0)
        self.assertAlmostEqual(dp[0]['effective_price_per_kg'], 25.5, places=6)
        self.assertEqual(dp[0]['sold_kg'], 0.0)

    def test_no_declared_cap_sells_at_base_price(self):
        d = destination(price={'tomato': 30.0}, demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        self.assertEqual(self._build(s, 0.0)[0]['sold_kg'], 300.0)

    def test_planner_never_sells_above_cap(self):
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 24.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        s, dp = self._dispatches(s, 'planner')
        self._assert_no_sale_above_cap(s, dp)

    def test_planner_skips_unreachable_cap(self):
        # cap 5.0 cannot be met even at the 30% discount ceiling -> no route
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 5.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        self.assertEqual(planner.plan_planner(s), [])

    def test_baseline_never_sells_above_cap(self):
        # baseline never discounts, so a fully-capped destination cannot be served
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 20.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        s, dp = self._dispatches(s, 'baseline')
        self._assert_no_sale_above_cap(s, dp)
        self.assertEqual(dp, [])

    def test_baseline_routes_around_capped_destination(self):
        capped = destination('D1', price={'tomato': 40.0}, max_price={'tomato': 20.0},
                             demand={'tomato': 300.0})
        open_d = destination('D2', price={'tomato': 30.0}, demand={'tomato': 300.0})
        s = make_scenario([batch(qty=200.0, life=5.0)], [capped, open_d])
        s, dp = self._dispatches(s, 'baseline')
        self.assertTrue(dp)
        self.assertTrue(all(x['destination_id'] == 'D2' for x in dp))
        self._assert_no_sale_above_cap(s, dp)

    def test_above_cap_flow_never_becomes_a_valid_sale(self):
        # A prohibited (above-cap) dispatch must not silently become a sale.
        d = destination(price={'tomato': 30.0}, max_price={'tomato': 20.0},
                        demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=300.0, life=5.0)], [d])
        dp = core.build_dispatches(s, [{'batch_id': 'B001', 'destination_id': 'D1',
                                        'quantity_kg': 300.0, 'discount_pct': 0.0}])
        self.assertEqual(dp[0]['sold_kg'], 0.0)
        self.assertEqual(dp[0]['gross_revenue'], 0.0)
        self.assertEqual(dp[0]['procurement_cost'], 0.0)

    def test_infeasible_route_is_not_dispatched(self):
        # §3: arrival shelf life below the minimum -> no planner dispatch at all
        d = destination(price={'tomato': 30.0}, demand={'tomato': 300.0}, transit=1.0)
        s = make_scenario([batch(qty=300.0, life=1.2)], [d])  # remain 0.2 < 0.5
        self.assertEqual(planner.plan_planner(s), [])


class TestNearExpiryDiscounts(unittest.TestCase):
    """§2.3/§2.5: a cap-meeting discount is lawful only for a near-expiry batch.

    Near-expiry at dispatch = shelf_life - (dispatch_day - harvest_day) is
    strictly positive and <= discount.near_expiry_days (default 1.0)."""

    def _cap_discount(self, scenario):
        cfg = core.config_of(scenario)
        b = scenario['batches'][0]
        d = scenario['destinations'][0]
        return planner._discount_for_cap(scenario, b, d, b['produce'], cfg)

    def _capped(self, price=30.0, cap=24.0, transit=0.5):
        return destination(price={'tomato': price}, max_price={'tomato': cap},
                           transit=transit, demand={'tomato': 300.0}, cap=9999.0)

    def test_non_near_expiry_batch_gets_no_discount(self):
        # remaining at dispatch = 5.0 days >> near_expiry_days (1.0)
        s = make_scenario([batch(qty=300.0, life=5.0, harvest=0)], [self._capped()])
        self.assertEqual(self._cap_discount(s), 0.0)
        # ...and the planner cannot route to the capped destination at all.
        self.assertEqual(planner.plan_planner(s), [])

    def test_near_expiry_batch_gets_cap_discount(self):
        # remaining at dispatch = 0.5 <= 1.0 -> eligible -> 30->24 is a 20% step
        s = make_scenario([batch(qty=200.0, life=5.0, harvest=-4.5)],
                          [self._capped(transit=0.0)])
        self.assertEqual(self._cap_discount(s), 20.0)
        flows = planner.plan_planner(s)
        self.assertTrue(flows)
        self.assertTrue(all(f['discount_pct'] == 20.0 for f in flows))

    def test_only_near_expiry_false_reenables_discount(self):
        s = make_scenario([batch(qty=300.0, life=5.0, harvest=0)], [self._capped()],
                          config={'discount': {'only_near_expiry': False}})
        self.assertEqual(self._cap_discount(s), 20.0)

    def test_expired_batch_is_not_eligible(self):
        # remaining at dispatch = -1.0 -> already expired, never discounted
        s = make_scenario([batch(qty=300.0, life=5.0, harvest=-6.0)], [self._capped()])
        cfg = core.config_of(s)
        self.assertFalse(planner._near_expiry_eligible(s, s['batches'][0], cfg))
        self.assertEqual(self._cap_discount(s), 0.0)

    def test_near_expiry_boundary_inclusive(self):
        # remaining == near_expiry_days (1.0) is eligible (inclusive)...
        s = make_scenario([batch(qty=200.0, life=6.0, harvest=-5.0)],
                          [self._capped(transit=0.0)])
        cfg = core.config_of(s)
        self.assertTrue(planner._near_expiry_eligible(s, s['batches'][0], cfg))
        self.assertEqual(self._cap_discount(s), 20.0)
        # ...and just beyond it (1.05 days) is not.
        s2 = make_scenario([batch(qty=200.0, life=6.05, harvest=-5.0)],
                           [self._capped()])
        cfg2 = core.config_of(s2)
        self.assertFalse(planner._near_expiry_eligible(s2, s2['batches'][0], cfg2))
        self.assertEqual(self._cap_discount(s2), 0.0)

    def test_no_cap_means_no_discount_despite_near_expiry(self):
        # T18: without a price cap there is no lawful discount, near-expiry or not
        d = destination(price={'tomato': 30.0}, demand={'tomato': 300.0}, cap=9999.0)
        s = make_scenario([batch(qty=200.0, life=5.0, harvest=-4.5)], [d])
        self.assertEqual(self._cap_discount(s), 0.0)


class TestNearExpiryDiscountEndToEnd(unittest.TestCase):
    """§2.3/§2.5 end-to-end: a near-expiry batch routed to a price-capped
    destination is discounted lawfully, sells, and reconciles through the real
    evaluation pipeline (apply_disruptions -> plan_planner -> build_dispatches ->
    aggregate/run_strategy). The unit tests above prove the *decision*; these
    prove the *accounting* of a discounted sale the fixtures never exercise."""

    def _capped_scenario(self, qty=200.0, life=5.0, harvest=-4.5, cap=24.0,
                         demand=300.0, unit=12.0, price=30.0):
        d = destination('D1', price={'tomato': price}, max_price={'tomato': cap},
                        transit=0.0, dist=10.0, demand={'tomato': demand}, cap=9999.0)
        b = batch('B001', qty=qty, life=life, harvest=harvest, unit=unit)
        return make_scenario([b], [d], horizon_days=1, dispatch_day=0)

    def _plan(self, scenario):
        s = core.apply_disruptions(scenario)
        flows = planner.plan_planner(s)
        dispatches = core.build_dispatches(s, flows)
        return s, flows, core.run_strategy(s, dispatches, 'planner'), dispatches

    def test_undiscounted_price_exceeds_cap_but_lawful_discount_meets_it(self):
        s, flows, block, dispatches = self._plan(self._capped_scenario())
        b, d = s['batches'][0], s['destinations'][0]
        self.assertEqual(core.effective_price(s, b, d, 'tomato', 0.0), 30.0)  # > cap
        self.assertEqual(core.max_price_for(d, 'tomato'), 24.0)              # cap
        self.assertTrue(core.sells_at_price(s, b, d, 'tomato', 0.0) is False)
        self.assertTrue(core.sells_at_price(s, b, d, 'tomato', 20.0) is True)
        self.assertEqual(len(dispatches), 1)
        self.assertEqual(dispatches[0]['discount_pct'], 20.0)
        self.assertAlmostEqual(dispatches[0]['effective_price_per_kg'], 24.0, places=6)
        self.assertLessEqual(dispatches[0]['effective_price_per_kg'],
                             core.max_price_for(d, 'tomato') + core.TOLERANCE_INR)

    def test_discounted_sale_contributes_to_revenue_demand_and_reconciliation(self):
        s, flows, block, dispatches = self._plan(self._capped_scenario())
        d = dispatches[0]
        m = block['metrics']
        self.assertEqual(d['sold_kg'], 200.0)
        self.assertAlmostEqual(d['gross_revenue'], 200.0 * 24.0, places=6)
        self.assertAlmostEqual(d['expected_contribution'],
                               200.0 * 24.0 - 200.0 * 12.0 - 200.0 * 10.0 * 0.8 - 200.0 * 1.0,
                               places=6)
        self.assertEqual(m['sold_kg'], 200.0)
        self.assertEqual(m['demand_kg'], 300.0)
        self.assertAlmostEqual(m['fulfillment_pct'], 200.0 / 300.0 * 100.0, places=2)
        self.assertAlmostEqual(m['net_revenue'], m['gross_revenue'] - m['procurement_cost']
                               - m['transport_cost'] - m['handling_cost'] - m['spoilage_cost'],
                               places=2)
        self.assertTrue(block['reconciliation']['check_ok'], block['reconciliation'])
        self.assertEqual(m['violations'], [])
        self.assertTrue(m['feasible'])

    def test_discounted_sale_respects_destination_demand(self):
        # demand 150 limits the planned quantity to 150 -> only 150 kg sells.
        s, flows, block, dispatches = self._plan(
            self._capped_scenario(qty=200.0, demand=150.0))
        d = dispatches[0]
        self.assertEqual(d['quantity_kg'], 150.0)
        self.assertEqual(d['sold_kg'], 150.0)
        self.assertEqual(d['arrived_unsold_kg'], 0.0)
        self.assertAlmostEqual(d['gross_revenue'], 150.0 * 24.0, places=6)
        self.assertTrue(block['reconciliation']['check_ok'])

    def test_fresh_batch_cannot_use_the_discount_workaround(self):
        # remaining at dispatch = 5.0 days -> not near-expiry -> no discount, no route.
        s, flows, block, dispatches = self._plan(
            self._capped_scenario(life=5.0, harvest=0.0))
        self.assertEqual(flows, [])
        self.assertEqual(dispatches, [])
        self.assertEqual(block['metrics']['sold_kg'], 0.0)
        self.assertTrue(block['metrics']['feasible'])

    def test_no_lawful_discount_opportunity_gets_none(self):
        # near-expiry, but cap 5.0 is unreachable even at the 30% ceiling -> no route,
        # so no arbitrary discount is invented to force a sale.
        s, flows, block, dispatches = self._plan(self._capped_scenario(cap=5.0))
        self.assertEqual(flows, [])
        self.assertEqual(dispatches, [])

    def test_baseline_does_not_discount_the_same_scenario(self):
        # FEFO never discounts: a fully-capped destination is skipped entirely.
        s = core.apply_disruptions(self._capped_scenario())
        bd = core.build_dispatches(s, baseline.plan_baseline(s))
        self.assertEqual(bd, [])

    def test_discounted_pipeline_is_deterministic(self):
        import json
        runs = [json.dumps(self._plan(self._capped_scenario())[2], sort_keys=True)
                for _ in range(2)]
        self.assertEqual(runs[0], runs[1])


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
