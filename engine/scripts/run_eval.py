"""Run the deterministic evaluation across seeds and disruption scenarios (§9).

Usage:
    python -m engine.scripts.run_eval                 # standard: 30 seeds
    python -m engine.scripts.run_eval --mode dev      # 10 seeds
    python -m engine.scripts.run_eval --mode large --out output/evaluation.json

Output follows the §9 evaluation.json shape. Results are synthetic-fixture
outputs, not observed real-world performance.
"""

import argparse
import os
import statistics

from engine import baseline, core, fixtures, planner

GENERATED_BY = 'engine/scripts/run_eval.py'
MODE_SEEDS = {'dev': 10, 'standard': 30, 'large': 200}


def _stats(values):
    return {
        'mean': round(statistics.fmean(values), 4) if values else None,
        'min': round(min(values), 4) if values else None,
        'max': round(max(values), 4) if values else None,
        'std': round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
    }


def _improvement_block(bm, pm):
    spec = (('net_revenue', 'net_revenue', 'higher_better'),
            ('spoilage_kg', 'spoiled_kg', 'lower_better'),
            ('fulfillment_pct', 'fulfillment_pct', 'higher_better'))
    out = {}
    for key, metric_key, direction in spec:
        b = bm[metric_key]
        p = pm[metric_key]
        delta = p - b
        defined = abs(b) >= core.EPS_PCT
        out[key] = {
            'baseline': b, 'planner': p, 'delta': round(delta, 4),
            'delta_pct': round(delta / abs(b) * 100.0, 4) if defined else None,
            'defined': defined, 'direction': direction,
        }
    return out


def _win(bm, pm):
    nr = pm['net_revenue'] > bm['net_revenue'] + core.TOLERANCE_INR
    sp = pm['spoiled_kg'] < bm['spoiled_kg'] - core.TOLERANCE_KG
    fp = pm['fulfillment_pct'] > bm['fulfillment_pct'] + core.TOLERANCE_KG
    all_metrics = (pm['net_revenue'] >= bm['net_revenue'] - core.TOLERANCE_INR
                   and pm['spoiled_kg'] <= bm['spoiled_kg'] + core.TOLERANCE_KG
                   and pm['fulfillment_pct'] >= bm['fulfillment_pct'] - core.TOLERANCE_KG
                   and (nr or sp or fp))
    return {'net_revenue': nr, 'spoilage_kg': sp,
            'fulfillment_pct': fp, 'all_metrics': all_metrics}


def _run_one(scenario):
    s = core.apply_disruptions(scenario)
    b_flows = baseline.plan_baseline(s)
    p_flows = planner.plan_planner(s, b_flows)
    b_metrics, _, _ = core.aggregate(s, core.build_dispatches(s, b_flows))
    p_metrics, _, _ = core.aggregate(s, core.build_dispatches(s, p_flows))
    return s, b_metrics, p_metrics


def evaluate(mode='standard'):
    n = MODE_SEEDS[mode]
    scenarios_out = []
    for seed in range(1, n + 1):
        base = fixtures.generate_scenario(seed)
        variants = [(base, None)] + [
            (fixtures.generate_scenario(seed, disruptions=[d]), d)
            for d in fixtures.disruptions_for(base)]
        for scenario, disruption in variants:
            s, bm, pm = _run_one(scenario)
            improvement = _improvement_block(bm, pm)
            feasible_both = bm['feasible'] and pm['feasible']
            win = _win(bm, pm) if feasible_both else {
                'net_revenue': False, 'spoilage_kg': False,
                'fulfillment_pct': False, 'all_metrics': False}
            run = {
                'seed': s['seed'],
                'baseline': {'metrics': bm, 'feasible': bm['feasible']},
                'planner': {'metrics': pm, 'feasible': pm['feasible']},
                'improvement': improvement,
                'win': win,
            }
            scenarios_out.append({'scenario_id': s['scenario_id'],
                                  'disruption': disruption,
                                  'runs': [run],
                                  'summary': _summary([run]),
                                  '_bm': bm, '_pm': pm})
    # scenario_id collides across disruption variants; make unique + drop helpers
    for sc in scenarios_out:
        if sc['disruption']:
            sc['scenario_id'] = f"{sc['scenario_id']}_{sc['disruption']['type']}"
        del sc['_bm'], sc['_pm']
    return {
        'schema_version': core.SCHEMA_VERSION,
        'generated_by': GENERATED_BY,
        'mode': mode,
        'seeds': list(range(1, n + 1)),
        'units': dict(core.DEFAULT_UNITS),
        'scenarios': scenarios_out,
    }


def _summary(runs):
    b_nr = [r['baseline']['metrics']['net_revenue'] for r in runs]
    p_nr = [r['planner']['metrics']['net_revenue'] for r in runs]
    imp = {k: [r['improvement'][k]['delta'] for r in runs]
           for k in ('net_revenue', 'spoilage_kg', 'fulfillment_pct')}
    wins = {k: sum(1 for r in runs if r['win'][k])
            for k in ('net_revenue', 'spoilage_kg', 'fulfillment_pct', 'all_metrics')}
    infeasible = {
        'baseline': sum(1 for r in runs if not r['baseline']['feasible']),
        'planner': sum(1 for r in runs if not r['planner']['feasible']),
    }
    return {
        'baseline': {'net_revenue': _stats(b_nr)},
        'planner': {'net_revenue': _stats(p_nr)},
        'improvement': {k: _stats(v) for k, v in imp.items()},
        'wins': {'net_revenue': wins['net_revenue'], 'spoilage_kg': wins['spoilage_kg'],
                 'fulfillment_pct': wins['fulfillment_pct'], 'all_metrics': wins['all_metrics'],
                 'runs': len(runs)},
        'infeasible_runs': infeasible,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description='Aurenza evaluation runner')
    ap.add_argument('--mode', choices=sorted(MODE_SEEDS), default='standard')
    ap.add_argument('--out', default=os.path.join('output', 'evaluation.json'))
    args = ap.parse_args(argv)
    result = evaluate(args.mode)
    core.save_json(result, args.out)
    total = len(result['scenarios'])
    wins = sum(sc['summary']['wins']['all_metrics'] for sc in result['scenarios'])
    print(f'wrote {args.out} ({total} scenarios, {wins} all-metric planner wins)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
