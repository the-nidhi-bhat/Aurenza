"""Generate a baseline-vs-planner result.json from the real engine (§8).

Usage:
    python -m engine.scripts.run_plan                       # demo fixture, seed 1
    python -m engine.scripts.run_plan --seed 7
    python -m engine.scripts.run_plan --scenario path.json --out out/result.json
    python -m engine.scripts.run_plan --scenario path.json --also-output

The emitted file is generated demo output, not observed real-world performance.
"""

import argparse
import os

from engine import baseline, core, fixtures, planner

GENERATED_BY = 'engine/scripts/run_plan.py'


def run(scenario):
    """Run both strategies on one scenario and return the §8 result object."""
    validate = core.apply_disruptions(scenario)  # idempotent if already applied
    baseline_flows = baseline.plan_baseline(validate)
    planner_flows = planner.plan_planner(validate, baseline_flows)
    return core.build_result(validate, core.build_dispatches(validate, baseline_flows),
                             core.build_dispatches(validate, planner_flows), GENERATED_BY)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Aurenza plan runner')
    ap.add_argument('--scenario', help='input scenario JSON (omit to use a synthetic fixture)')
    ap.add_argument('--seed', type=int, default=1, help='fixture seed when no --scenario')
    ap.add_argument('--out', default=os.path.join('demo', 'result.json'), help='output path')
    ap.add_argument('--also-output', action='store_true',
                    help='also write output/<scenario_id>/result.json (contract §8 path)')
    args = ap.parse_args(argv)

    if args.scenario:
        scenario = core.load_scenario(args.scenario)
    else:
        scenario = fixtures.generate_scenario(args.seed)

    result = run(scenario)
    core.save_json(result, args.out)
    print(f'wrote {args.out}')
    if args.also_output:
        path = os.path.join('output', scenario['scenario_id'], 'result.json')
        core.save_json(result, path)
        print(f'wrote {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
