# Aurenza — Assumptions, Clarifications & Open Data

This file records every assumption, contract clarification, and piece of missing
input the engine currently relies on. Nothing here is ratified contract text.

- Contract: `docs/CONTRACT.md` **v1.0.0-draft.4** (status: PROPOSED — NOT FROZEN)
- All assumptions below are **implemented** unless marked *proposed*.

---

## 1. Proposed contract clarifications

These are contradictions/ambiguities found while implementing draft.4. They are
recorded here for the contract owner (Nidhi) to ratify. The engine follows the
documented choice so it stays runnable.

### CLARIFICATION-1 — `notes="no_demand"` has no home in the schema
- **Where:** §6.3 says zero supported demand ⇒ `fulfillment_pct = 100.0` *and*
  `notes` records `"no_demand"`. §8's Metrics schema has **no `notes` key**.
- **Conflict:** the required field cannot be emitted without violating the exact
  §8 metric key set (16 keys).
- **Engine choice:** emit `fulfillment_pct = 100.0` and **omit `notes`**, keeping
  output schema-exact. No compatibility shim is added.
- **Needed from owner:** either add `notes` to the §8 Metrics schema, or drop the
  §6.3 sentence.

### CONTRADICTION-1 — revenue price basis
- **Where:** §2.1 writes `effective_price_per_kg = base_price_per_kg × (1 − disc/100)`,
  but the §8 worked example uses the **destination** `price_per_kg` (30.0), not the
  batch `base_price_per_kg` (25.0).
- **Engine choice:** sell at the destination price for the produce; fall back to the
  batch `base_price_per_kg` only when the destination has no price for that produce.
  See `engine/core.py: price_basis()`.
- **Needed from owner:** confirm destination price is the point-of-sale basis.

### CONTRADICTION-2 — disruption effects are undefined
- **Where:** §7 names five disruption types (`transport_strike`, `demand_spike`,
  `shelf_life_shock`, `capacity_reduction`, `price_drop`) but does **not** define
  the parameter names or how each mutates the scenario.
- **Engine choice (PROVISIONAL):** `engine/core.py: apply_disruptions()` implements
  the parameter effects documented in §2 below. These need sign-off.

### CLARIFICATION-2 — the contract does not define the baseline algorithm
- §5.4 fixes only the shared objective and that both strategies use the same
  metric definitions. It never says what a "baseline" must compute.
- **Project decision (per mission):** the baseline is a **deterministic FEFO
  heuristic** — see `engine/baseline.py`. This is a team decision, not contract text.

---

## 2. Disruption parameter effects (PROVISIONAL)

| Type | Params | Effect |
|------|--------|--------|
| `transport_strike` | `affected_destination_ids[]`, `capacity_multiplier` (default `0.0`) | multiply affected `capacity_kg` by the multiplier |
| `capacity_reduction` | `affected_destination_ids[]`, `capacity_multiplier` (default `0.5`) | same, different default |
| `demand_spike` | `affected_destination_ids[]`, `demand_multiplier` (default `1.0`), optional `produce` | multiply affected `demand[produce]` |
| `price_drop` | `affected_destination_ids[]` (default: all), `price_multiplier` (default `1.0`), optional `produce` | multiply affected `price_per_kg[produce]` |
| `shelf_life_shock` | `affected_batch_ids[]`, `shelf_life_delta_days` (default `0.0`) | add delta to `shelf_life_days`, clamped ≥ 0 |

---

## 3. Synthetic demo data (NOT real)

`engine/fixtures.py` generates a **labelled synthetic fixture** (`fixture: true`)
so the engine and demo are runnable. **No value here is a real market price,
supplier cost, or observed demand.**

Placeholder produce catalogue (shelf life days / unit cost ₹/kg / base price ₹/kg):

| Produce | shelf_life_days | unit_cost_per_kg | base_price_per_kg |
|---------|-----------------|------------------|-------------------|
| tomato  | 5.0 | 12.0 | 25.0 |
| spinach | 2.8 | 20.0 | 40.0 |
| banana  | 6.0 | 15.0 | 30.0 |
| mango   | 4.0 | 35.0 | 70.0 |
| onion   | 20.0 | 8.0 | 18.0 |

Destinations (id / type / transit_days / distance_km):

| id | type | transit_days | distance_km |
|----|------|--------------|-------------|
| D001 | retail | 0.25 | 6.0 |
| D002 | retail | 0.5 | 18.0 |
| D003 | wholesale | 0.25 | 10.0 |
| D004 | wholesale | 1.0 | 30.0 |

Cost model used in fixtures: `transport_per_kg_km 0.8`, `handling_per_kg 1.0`,
`spoilage_penalty_per_kg 2.0`. Horizon 1 day, dispatch day 0.

## 4. Open data needed from the responsible teammate (Iffa — A9)

1. Real produce catalogue: per produce, `shelf_life_days`, `unit_cost_per_kg`,
   `base_price_per_kg` (and any `freshness_pct` decay model).
2. Real destination set: `type`, `capacity_kg`, `transit_days`, `distance_km`,
   `demand[produce]`, `price_per_kg[produce]`, optional `max_price_per_kg[produce]`.
3. Confirmation of disruption parameter names/effects (§2) and their realistic ranges.
4. Whether the A9 catalogue is expected to ship as a fixture file (path/schema).

Until (1)–(4) arrive, the engine runs on the synthetic fixture above, which is
explicitly labelled and reproducible by seed.
