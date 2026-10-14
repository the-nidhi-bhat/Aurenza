# Aurenza — Data & Result Contract

> **STATUS: PROPOSED — NOT FROZEN.**
> Owner: Nidhi. Reviewers required before freeze: Arati (dashboard), Iffa (data/eval).
> Version: `1.0.0-draft.4`. Do not code against this until the owner marks it `1.0.0`.
> Change log is at the bottom. Any breaking change bumps the version.

This document is the single shared interface between three independently developed parts:

| Part | Owner | Reads | Writes |
|---|---|---|---|
| Planning engine | Nidhi | input scenario JSON | result + evaluation JSON |
| Dashboard | Arati | result + evaluation JSON | — |
| Data & evaluation | Iffa | this contract | input scenario JSON, assumptions, eval reports |

Nothing in here is implemented yet. This is the spec we agree on first.

---

## 0. Scope, units, conventions

### 0.1 Units (fixed)
| Quantity | Unit | Format |
|---|---|---|
| mass | `kg` | float, round 3 dp |
| money | `INR` | float, round 2 dp |
| time | `day` | integer or float day-index from horizon start (day 0 = first day) |
| distance | `km` | float, round 2 dp |
| discount | `percent` | float `0–100`, 2 dp |
| freshness / shelf-life | `days` for life, `percent` for freshness | 2 dp |

### 0.2 Conventions
- `schema_version` follows `MAJOR.MINOR.PATCH`. Engine rejects a file whose MAJOR differs from what it implements.
- `scenario_id` is a stable slug (`base`, `transport_strike`, ...). One scenario ⇒ one result directory.
- `seed` is an integer. **Determinism rule:** identical input file + identical `seed` ⇒ byte-identical output (apart from the `generated_at` field in eval metadata, which is excluded from determinism comparison).
- Missing *required* field ⇒ hard error (no silent default). Missing *optional* field ⇒ documented default applied and reported.
- Unknown enum value (e.g. disruption `type`) ⇒ hard error.
- All money is INR; no currency conversion anywhere in the pipeline.

### 0.3 Config block (see §13 for the decided values and remaining open item)
A `config` block centralises every behavioral assumption so both strategies and the evaluator read the same knobs. Defaults are **conservative** (do not invent demand, do not hide spoilage).

---

## 1. Inventory & spoilage accounting (revision 1)

**Problem:** earlier draft could double-count or count fresh unsold stock as spoiled.

### 1.1 Batch lifecycle
Every kg in `batch.quantity_kg` (`harvested_kg`) ends at the horizon in **exactly one** terminal state:

| Terminal state | Definition |
|---|---|
| `sold_kg` | dispatched, arrived, and sold at destination before horizon |
| `fresh_inventory_kg` | **still usable at horizon end** — any not-sold stock (never-dispatched **or** arrived-unsold) whose age at the horizon is still within `shelf_life_days` (A1, A6) |
| `spoiled_kg` | **expired at horizon** — any not-sold stock whose age at the horizon exceeds `shelf_life_days` (A1) |

**Conservation invariant (per batch, enforced by test):**
```
harvested_kg == sold_kg + fresh_inventory_kg + spoiled_kg   (±0.001 kg)
```
Aggregated over all batches, the same identity holds for the scenario.

### 1.2 Derived (non-terminal) quantities — reported, never added twice
| Quantity | Definition |
|---|---|
| `dispatched_kg` | Σ quantity that left origin = `sold_kg + arrived_unsold_kg` |
| `arrived_unsold_kg` | dispatched, arrived, not sold → resolves into `fresh_inventory_kg` or `spoiled_kg` by the expiry rule (§1.4) |

`arrived_unsold_kg` is **not** a terminal state; it is reported for explainability but is already counted inside `fresh_inventory_kg` or `spoiled_kg`. This is what prevents double counting.

### 1.3 Rules
- **A1 (decided):** unsold stock is **held** if still fresh at the horizon, and counted as **spoiled only when expired**. It is never counted as spoilage while fresh.
- Stock that never leaves origin and is still fresh at horizon ⇒ `fresh_inventory_kg`, **not** a cost and **not** spoilage.
- Fresh inventory remaining at the horizon is reported **separately** from spoiled stock (`fresh_inventory_kg` vs `spoiled_kg`) — single-day horizon (A6).

### 1.4 Expiry rule at the horizon (A1, A6)
Age of any stock is measured **since harvest** (location does not reset it):
```
age_at_horizon_days   = horizon_days − batch.harvest_day
remaining_at_horizon  = batch.shelf_life_days − age_at_horizon_days
state = "fresh_inventory"  if remaining_at_horizon >= 0
        "spoiled"          otherwise
```
This applies identically to never-dispatched stock and to arrived-unsold stock. (With the initial single-day horizon `horizon_days = 1`, `harvest_day = 0`.)

---

## 2. Demand & discounts (revision 2)

### 2.1 Discounts do not automatically create demand
Discount changes the **effective selling price**, and separately may — only if explicitly enabled — change **demand**.

- Effective price: `effective_price_per_kg = base_price_per_kg × (1 − discount_pct / 100)`.
- Base demand: `demand_kg = destination.demand[produce]` (kg), for the scenario horizon.

### 2.1a Two distinct ordering rules (A4)
- **Destination selection** (the planner choosing *where* to send stock) is ranked by a **`selection_score`**. The `selection_score` accounts for expected gross revenue, procurement of expected sold kg, transport, handling, and **expected spoilage** for the candidate routing. This internal ranking value differs from the **reported** `dispatch.expected_contribution` (§5.2), which excludes spoilage. The `selection_score` is used **only** for ranking candidate dispatches/assignments; it is **never** summed into financial aggregates (`net_revenue`, `sum_dispatch_contributions`) and is not reported as a financial metric.
- **Sales allocation** (who sells first when destination demand < supply) is ordered by `config.sales_allocation` = `highest_effective_price_first`, with deterministic tie-breaks (§12).

These are different decisions and must not be conflated.

### 2.2 Demand response (explicit, configurable, conservative default OFF)
```
config.demand_response.enabled            (bool,  default false)
config.demand_response.discount_elasticity (float, default 0.0)
config.demand_response.max_demand_multiplier (float, default 1.0)
```
When `enabled == false` **or** `discount_elasticity == 0`:
```
effective_demand_kg = demand_kg            # NO extra demand from discounting
```
When enabled:
```
effective_demand_kg = min(
    demand_kg × (1 + discount_elasticity × discount_pct / 100),
    demand_kg × max_demand_multiplier      # hard cap, default 1.0 = no growth
)
```
So **with default config, a discount can never increase sellable quantity** — it can only lower unit revenue **for the same sold quantity**.

### 2.2a Default = no discount (A3, A7)
- Because discounts do not create demand by default (A3), the default is **no discount**.
- The engine may apply a discount **only if it strictly increases net revenue under the configured demand model**, and must record the justification in the dispatch `reason`. It must **not** invent demand to make a discount look worthwhile.
- The single sanctioned non-demand mechanism is an explicit per-destination **price-threshold** (§2.4): a destination buys nothing above a declared maximum price. With no price threshold and demand response off, the model applies **no discount**.

### 2.3 Discount eligibility (A7)
```
config.discount.eligible_max_pct   (default 30.0)
config.discount.step_pct           (default 5.0)
config.discount.only_near_expiry   (bool, default true)
config.discount.near_expiry_days   (float, default 1.0)
config.discount.require_justification (bool, default true)
```
- Discounts are **configurable, near-expiry only** (`only_near_expiry = true`). **Near-expiry definition:** at dispatch, compute `remaining_at_dispatch_days = batch.shelf_life_days − age_at_dispatch_days`; a batch is eligible when it **has not expired** and `remaining_at_dispatch_days <= config.discount.near_expiry_days`. `near_expiry_days` is configurable per scenario, must be ≥ 0.
- With `require_justification = true` (default), a discount is applied only when it strictly increases net revenue (§2.2a).

### 2.5 Discount mechanics (implementability)
- **Price threshold inclusive:** `destination.max_price_per_kg` is **inclusive**. The destination buys at `effective_price_per_kg` only when `effective_price_per_kg <= max_price_per_kg`; when `effective_price_per_kg > max_price_per_kg`, sold quantity for that produce from that destination is 0 for that dispatch (price threshold not met).
- **How a discount can improve net revenue without creating extra demand (demand response OFF):** with `config.demand_response.enabled == false`, `effective_demand_kg` does not increase with discount. The only way a discount strictly improves net revenue is to **move a candidate dispatch from unsold to sold** by lowering `effective_price_per_kg` to meet a declared price threshold (or to be viable under a binding price ceiling), so the dispatch generates positive incremental contribution on those kg. In all cases where the destination would already buy the same quantity at the base price (no threshold binding), applying a discount cannot increase net revenue.
- **Interaction of factors:** Discount eligibility is evaluated at dispatch (§2.3) and restricted to near-expiry only. A discount is applied only if it improves expected net revenue under the modeled demand and constraints (§2.2a); this evaluation must include **transport costs**, **handling costs**, **procurement of sold kg**, and the effect on whether the dispatch meets demand/capacity/feasibility. The **`selection_score`** (internal, includes expected spoilage) is used for destination selection only and is never mixed into reported financial aggregates (§5.2).
- **Relationship to `selection_score`:** The `selection_score` ranks candidate routings (including expected spoilage) to minimize spoilage/choose best routing; it is distinct from `dispatch.expected_contribution` (reported, excludes spoilage) and from `net_revenue` (aggregate). Decisions to apply a discount must be justified against the **expected net revenue impact**, not the selection_score alone.

---

## 3. Shelf life (revision 3)

All shelf-life terms are evaluated **per dispatch** at planning time:

```
age_at_dispatch_days        = dispatch_day − batch.harvest_day
remaining_at_arrival_days   = batch.shelf_life_days − age_at_dispatch_days − destination.transit_days
```

Hard rule:
```
remaining_at_arrival_days >= config.min_arrival_shelf_life_days   (default 0.5 day, A2)
```
- If false ⇒ the dispatch is **rejected** (not silently accepted). The candidate may still be routed elsewhere; if no valid destination exists, the batch stays as inventory/spoilage per §1.
- Additionally, for a sale to count, arrival must occur within the horizon: `dispatch_day + transit_days <= horizon_days`; otherwise the dispatch is flagged infeasible.
- `min_arrival_shelf_life_days` is **configurable per scenario**, default **0.5** day (A2).

---

## 4. Revenue & fulfillment (revision 4)

### 4.1 Dispatches are shipments, not guaranteed sales
`quantity_kg` on a dispatch = goods **shipped**. Not all shipped goods necessarily sell.

Per dispatch we track separately:
```
sold_kg      = min(quantity_kg, remaining_effective_demand at that destination for that produce)
arrived_unsold_kg = quantity_kg − sold_kg
```
Sales are allocated deterministically (§12) so output is reproducible.

### 4.2 Revenue and fulfillment use SALES, not shipments
- `gross_revenue = Σ (sold_kg × effective_price_per_kg)`  ← sold, not shipped.
- `demand_kg = Σ destinations demand_kg` for the scenario.
- `fulfillment_pct = min(100, sold_kg_total / demand_kg × 100)` (guard: see §6.3 for zero denominator).

### 4.3 Required separation
The result **must** expose `dispatched_kg`, `sold_kg`, and `arrived_unsold_kg` distinctly so judges can see shipped-vs-sold.

---

## 5. Cost attribution & reconciliation (revision 5)

### 5.1 Attribution rules (identical for baseline and planner)
| Cost | Applied to | Formula |
|---|---|---|
| `procurement_cost` | **sold_kg** — COGS on goods actually sold (A11) | Σ `sold_kg × batch.unit_cost_per_kg` |
| `transport_cost` | **dispatched_kg** (goods physically moved, whether or not sold) | Σ `dispatched_kg × distance_km × cost_model.transport_per_kg_km` |
| `handling_cost` | **dispatched_kg** (handled on arrival; A5) | Σ `dispatched_kg × cost_model.handling_per_kg` |
| `spoilage_cost` | **spoiled_kg** (all, incl. retained) | Σ `spoiled_kg × cost_model.spoilage_penalty_per_kg` |

### 5.1a No double counting (A11, U2)
- `procurement_cost` is charged **only on `sold_kg`** (COGS). It is **not** charged on spoiled or retained-fresh kg.
- `spoilage_cost` (spoilage loss) = **unrecoverable procurement-value loss on spoiled kg**, valued at `spoilage_penalty_per_kg`. **Precedence (U2):** if `cost_model.spoilage_penalty_per_kg` is **provided**, use that scenario-wide value for all spoiled kg; if **omitted**, use the **relevant batch's `unit_cost_per_kg`** for each spoiled kg. Because procurement is charged only on sold kg, the spoilage loss and the procurement line **never overlap**.
- A **separate disposal fee**, if ever wanted, must be a **distinct cost field** (e.g. `disposal_cost`) — never folded into `spoilage_cost`. **Not modeled in v1.**
- Retained fresh inventory (`fresh_inventory_kg`) carries **no** cost in this horizon: it is still a usable asset, not an expense.
- Enforced by test T16: no kg of stock contributes to both `procurement_cost` and `spoilage_cost`.

### 5.1b Cost allocation across multiple dispatches (pre-freeze #3)
All v1 costs are **kg-proportional**, so they partition cleanly across the dispatches of a batch — there are **no fixed/shared batch-level costs** to apportion in v1:
| Quantity | Allocation basis | Identity |
|---|---|---|
| `procurement_cost` | per dispatch `sold_kg` × `batch.unit_cost_per_kg` | Σ over a batch's dispatches = batch `sold_kg` × `unit_cost_per_kg` |
| `transport_cost` | per dispatch `dispatched_kg` × its own `distance_km` | Σ dispatch(transport_cost) = Σ dispatch(`dispatched_kg` × `distance_km` × rate) |
| `handling_cost` | per dispatch `dispatched_kg` | Σ dispatch(handling_cost) = Σ dispatch(`dispatched_kg` × rate) |
| `spoilage_cost` | computed per batch (reportable for explainability), but **subtracted once at the aggregate level** (§5.3) | Σ over batches = total `spoilage_cost` |
If a future **fixed** cost (e.g. a per-trip loading fee) is added, it must be allocated by an explicit documented rule (default: proportional to `dispatched_kg`). Not in v1.

### 5.2 Dispatch-level expected contribution (excludes spoilage — pre-freeze #2)
The **reported** dispatch contribution **excludes spoilage**, so aggregate spoilage loss is subtracted exactly once (§5.3):
```
dispatch.expected_contribution
  = dispatch.gross_revenue
  − dispatch.procurement_cost        # unit_cost_per_kg × dispatch.sold_kg
  − dispatch.transport_cost
  − dispatch.handling_cost
  # spoilage is NOT subtracted here (see §5.3)
```
For **destination selection only**, the planner may rank candidates by a separate **`selection_score`** that **does include** the expected spoilage of that routing (§2.1a). The `selection_score` is an **internal, non-aggregated ranking value** and is **never** added into financial aggregates (including `net_revenue` or `sum_dispatch_contributions`). Its only purpose is to compare candidate routing decisions.

### 5.3 Aggregate reconciliation (must reconcile, enforced by test T24)
```
sum_dispatch_contributions = Σ dispatch.expected_contribution           # excludes spoilage
net_revenue                = sum_dispatch_contributions − spoilage_cost   # total spoilage subtracted ONCE
```
Expanding, identically for both strategies:
```
net_revenue = gross_revenue − procurement_cost − transport_cost − handling_cost − spoilage_cost
```
Output includes an explicit `reconciliation` block with `sum_dispatch_contributions`, `spoilage_cost`, `net_revenue`, and `check_ok` (true when `net_revenue == sum_dispatch_contributions − metrics.spoilage_cost` within ₹0.01). T24 explicitly tests this identity.

### 5.4 Planner objective (U3)
Maximize `net_revenue` **subject to all hard feasibility constraints (§11)**. When two candidate plans are equal in `net_revenue` within the accounting tolerance (`< ₹0.01`), break ties by **lower `spoilage_kg`**, then by **higher `fulfillment_pct`**, then by the deterministic ordering of §12. Both strategies use the same metric definitions and are compared against the **same baseline**.

---

## 6. Metric definitions (identical for both strategies)

### 6.1 Quantity metrics
`harvested_kg`, `dispatched_kg`, `sold_kg`, `arrived_unsold_kg`, `fresh_inventory_kg`, `spoiled_kg`, `demand_kg`.

### 6.2 Financial metrics
`gross_revenue`, `procurement_cost`, `transport_cost`, `handling_cost`, `spoilage_cost`, `net_revenue`.

`net_revenue = gross_revenue − procurement_cost − transport_cost − handling_cost − spoilage_cost` (A11, §5.3).

### 6.3 Ratio metrics & zero-denominator policy
- `fulfillment_pct = min(100, sold_kg / demand_kg × 100)`, capped at 100.
- **demand_kg definition:** `demand_kg` = total demand for supported retail/wholesale destinations only (donation/processing are not supported in v1; U4). Fulfilled demand = kilograms sold against supported retail/wholesale demand.
- **Zero-total-demand case:** if `demand_kg == 0`, no demand is unmet; `fulfillment_pct = 100.0` and `notes` records `"no_demand"` (no division by zero).
- Percentage-change fields in evaluation use their own baseline-zero rule (§9.4).
- Any case where `demand_kg == 0` and `sold_kg > 0` is treated as infeasible / a conservation/demand violation (cannot sell against zero supported demand).

### 6.4 Feasibility
`feasible` (bool) and `violations` (array of `{code, message, batch_id?, destination_id?}`). `feasible == true` iff `violations` is empty. **Feasibility is a prerequisite** for counting any improvement.

---

## 7. Input scenario schema — `data/raw/scenario_<scenario_id>.json`

```json
{
  "schema_version": "1.0.0",
  "scenario_id": "base",
  "seed": 42,
  "fixture": false,
  "units": { "mass": "kg", "currency": "INR", "time": "day",
             "distance": "km", "discount": "percent", "freshness": "percent" },
  "horizon_days": 1,
  "dispatch_day": 0,
  "config": {
    "min_arrival_shelf_life_days": 0.5,
    "demand_response": { "enabled": false, "discount_elasticity": 0.0, "max_demand_multiplier": 1.0 },
    "discount": { "eligible_max_pct": 30.0, "step_pct": 5.0, "only_near_expiry": true, "near_expiry_days": 1.0, "require_justification": true },
    "sales_allocation": "highest_effective_price_first"
  },
  "cost_model": {
    "transport_per_kg_km": 0.8,
    "handling_per_kg": 1.0,
    "spoilage_penalty_per_kg": 2.0
  },
  "batches": [
    { "batch_id": "B001", "produce": "tomato", "quantity_kg": 500.0,
      "harvest_day": 0, "shelf_life_days": 5, "freshness_pct": 100.0,
      "unit_cost_per_kg": 12.0, "base_price_per_kg": 25.0 }
  ],
  "destinations": [
    { "destination_id": "D001", "name": "City Market", "type": "retail",
      "capacity_kg": 1000.0, "transit_days": 0.5, "distance_km": 20.0,
      "demand": { "tomato": 300.0 }, "price_per_kg": { "tomato": 30.0 } }
  ],
  "disruptions": []
}
```

**Required fields:** everything above except `config` (defaulted per §0.3), `config.discount.require_justification`/`config.discount.near_expiry_days`/`config.min_arrival_shelf_life_days` (defaulted), `cost_model.spoilage_penalty_per_kg` (optional; if omitted, each batch's `unit_cost_per_kg` is used), `disruptions` (defaults `[]`), `fixture` (defaults `false`), per-destination `name` (defaults to id), and optional per-destination `max_price_per_kg` (§2.4).
**`destination.type` ∈** `retail | wholesale` **in v1** (sales destinations only). `processing` and `donation` are **out of scope for v1** (U4) and must raise `unsupported_destination_type` (§11) — do not model them as sales destinations, and do not count them as fulfilled customer demand.
**Disruption object:** `{ "type": <enum>, "params": { ... } }`; types enumerated in `docs/ASSUMPTIONS.md` (`transport_strike`, `demand_spike`, `shelf_life_shock`, `capacity_reduction`, `price_drop`). Unknown `type` ⇒ hard error.

**`freshness_pct` (U1):** a **descriptive quality indicator only** in v1. Expiry is determined **solely** by `shelf_life_days` and harvest age (§1.4) — `freshness_pct` is **not** a second expiry mechanism. In v1 it is **informational**; the planner may use it as a priority signal only if a formula is documented and covered by a test (not in v1).

---

## 8. Per-scenario result schema — `output/<scenario_id>/result.json`

```json
{
  "schema_version": "1.0.0",
  "scenario_id": "base",
  "seed": 42,
  "fixture": false,
  "generated_by": "engine/scripts/run_plan.py",
  "units": { "mass": "kg", "currency": "INR", "time": "day",
             "distance": "km", "discount": "percent", "freshness": "percent" },
  "results": {
    "baseline": { "strategy": "baseline", "dispatches": [ /* Dispatch */ ],
                  "metrics": { /* Metrics */ }, "batch_summary": [ /* BatchSummary */ ],
                  "reconciliation": { /* Reconciliation */ } },
    "planner":  { "strategy": "planner",  "dispatches": [ /* Dispatch */ ],
                  "metrics": { /* Metrics */ }, "batch_summary": [ /* BatchSummary */ ],
                  "reconciliation": { /* Reconciliation */ } }
  },
  "improvement": {
    "net_revenue":     { "baseline": 0.0, "planner": 0.0, "delta": 0.0, "delta_pct": null, "direction": "higher_better" },
    "spoilage_kg":     { "baseline": 0.0, "planner": 0.0, "delta": 0.0, "delta_pct": null, "direction": "lower_better" },
    "fulfillment_pct": { "baseline": 0.0, "planner": 0.0, "delta": 0.0, "delta_pct": null, "direction": "higher_better" }
  }
}
```

**Dispatch (identical shape in both strategies):**
```json
{
  "batch_id": "B001",
  "destination_id": "D001",
  "dispatch_day": 0,
  "quantity_kg": 300.0,
  "discount_pct": 0.0,
  "age_at_dispatch_days": 0.0,
  "remaining_at_arrival_days": 4.5,
  "effective_price_per_kg": 30.0,
  "sold_kg": 300.0,
  "arrived_unsold_kg": 0.0,
  "gross_revenue": 9000.0,
  "procurement_cost": 3600.0,
  "transport_cost": 4800.0,
  "handling_cost": 300.0,
  "expected_contribution": 300.0,
  "reason": "Tomato B001 (100% fresh, 5d life, 4.5d left at arrival): selected for highest selection_score; demand absorbs full 300kg; no discount (demand response off, no price threshold)."
}
```

**Metrics:**
```json
{
  "harvested_kg": 0.0, "dispatched_kg": 0.0, "sold_kg": 0.0, "arrived_unsold_kg": 0.0,
  "fresh_inventory_kg": 0.0, "spoiled_kg": 0.0, "demand_kg": 0.0,
  "gross_revenue": 0.0, "procurement_cost": 0.0, "transport_cost": 0.0,
  "handling_cost": 0.0, "spoilage_cost": 0.0, "net_revenue": 0.0,
  "fulfillment_pct": 0.0, "feasible": true, "violations": []
}
```

**BatchSummary (supports §1 conservation + dashboard inventory view):**
```json
{ "batch_id": "B001", "harvested_kg": 500.0, "dispatched_kg": 300.0,
  "sold_kg": 300.0, "arrived_unsold_kg": 0.0,
  "fresh_inventory_kg": 200.0, "spoiled_kg": 0.0 }
```

**Reconciliation:**
```json
{ "sum_dispatch_contributions": 0.0, "spoilage_cost": 0.0,
  "net_revenue": 0.0, "check_ok": true }
```

---

## 9. Evaluation schema — `output/evaluation.json` (multi-seed + disruptions)

Standard evaluation = **30 deterministic seeds** (`seeds = [1..30]`); `mode` reports which was run. Both strategies run on the **same generated scenario** for each seed.

```json
{
  "schema_version": "1.0.0",
  "generated_by": "engine/scripts/run_eval.py",
  "mode": "standard",
  "seeds": [1, 2, 3],
  "units": { "mass": "kg", "currency": "INR", "time": "day",
             "distance": "km", "discount": "percent", "freshness": "percent" },
  "scenarios": [
    {
      "scenario_id": "base",
      "disruption": null,
      "runs": [
        {
          "seed": 1,
          "baseline": { "metrics": { /* Metrics */ }, "feasible": true },
          "planner":  { "metrics": { /* Metrics */ }, "feasible": true },
          "improvement": {
            "net_revenue":     { "baseline": 0.0, "planner": 0.0, "delta": 0.0, "delta_pct": null, "defined": true },
            "spoilage_kg":     { "baseline": 0.0, "planner": 0.0, "delta": 0.0, "delta_pct": null, "defined": true },
            "fulfillment_pct": { "baseline": 0.0, "planner": 0.0, "delta": 0.0, "delta_pct": null, "defined": true }
          },
          "win": { "net_revenue": true, "spoilage_kg": true,
                   "fulfillment_pct": true, "all_metrics": true }
        }
      ],
      "summary": {
        "baseline": { "net_revenue": { "mean": 0, "min": 0, "max": 0, "std": 0 } },
        "planner":  { "net_revenue": { "mean": 0, "min": 0, "max": 0, "std": 0 } },
        "improvement": { "net_revenue": { "mean": 0, "min": 0, "max": 0, "std": 0 },
                         "spoilage_kg": { }, "fulfillment_pct": { } },
        "wins": { "net_revenue": 0, "spoilage_kg": 0, "fulfillment_pct": 0,
                  "all_metrics": 0, "runs": 3 },
        "infeasible_runs": { "baseline": 0, "planner": 0 }
      }
    },
    {
      "scenario_id": "transport_strike",
      "disruption": { "type": "transport_strike",
                      "params": { "affected_destination_ids": ["D002"], "capacity_multiplier": 0.0 } },
      "runs": [ /* same shape */ ],
      "summary": { /* same shape */ }
    }
  ]
}
```

### 9.4 Win counting & percentage rules (revision 6)
- **Same scenario per seed for both strategies.** No strategy gets an easier draw.
- **Win (per metric, per run):** planner strictly better than baseline in the metric's `direction` (`higher_better` / `lower_better`).
- **`all_metrics` win:** planner is at least as good on *all three* metrics and strictly better on at least one. Ties count as "not a win" but do not count as losses (documented in ASSUMPTIONS).
- **`delta_pct = (planner − baseline) / |baseline| × 100`.** If `|baseline| < ε` (ε = 1e-9) ⇒ `delta_pct = null`, `defined = false`, and a `notes` field records `"undefined_baseline"`. **Never** divide by zero; never imply a percentage.
- **Infeasible runs:** counted in `infeasible_runs`; excluded from `wins` and from any "improvement" claim. If the planner produces **any** infeasible run, the evaluation cannot claim success on that scenario.
- **No improvement may be claimed until a real evaluation produces these numbers.** Reporting is numbers-first; prose references the produced file, never a guess.

---

## 10. How the dashboard consumes the contract

1. Read `output/evaluation.json` → scenario/disruption selector + summary cards + disruption view.
2. Read the selected `output/<scenario_id>/result.json`, **or** the committed `demo/result.json` when the engine has not been run locally/deployed.
3. **Comparison cards:** `results.baseline.metrics` vs `results.planner.metrics` (+ `improvement`).
4. **Dispatch table:** `results.planner.dispatches[]` → batch_id, destination_id, quantity_kg, discount_pct, expected_contribution, reason.
5. **Inventory/spoilage view:** `results.<strategy>.batch_summary[]`.
6. **Charts:** per-seed and per-disruption values from `evaluation.json`.
7. The dashboard imports **no** engine code — it depends only on these JSON files. If the contract is not frozen, mock using `demo/result.json`.

---

## 11. Hard constraints & feasibility (revision 7)

Every run validates these before writing output; any violation ⇒ `feasible = false` and an entry in `violations`:

| Code | Constraint |
|---|---|
| `unknown_disruption_type` | every disruption `type` is in the documented enum |
| `negative_quantity` | all quantities ≥ 0 |
| `inventory_exceeded` | Σ dispatched per batch ≤ `batch.quantity_kg` |
| `capacity_exceeded` | Σ allocated per destination ≤ `destination.capacity_kg` |
| `demand_exceeded` | Σ sold per destination/produce ≤ `effective_demand_kg` |
| `shelf_life_expired` | `remaining_at_arrival_days ≥ min_arrival_shelf_life_days` for every dispatch |
| `arrival_after_horizon` | `dispatch_day + transit_days ≤ horizon_days` |
| `discount_out_of_range` | `0 ≤ discount_pct ≤ config.discount.eligible_max_pct` |
| `discount_step_mismatch` | `discount_pct` is on the `config.discount.step_pct` grid |
| `invalid_near_expiry_days` | `config.discount.near_expiry_days >= 0` |
| `unsupported_destination_type` | `destination.type ∈ {retail, wholesale}` in v1 (U4) |
| `unknown_reference` | every `batch_id` / `destination_id` exists; every `produce` exists in destination demand |
| `inventory_not_conserved` | §1.1 identity holds for every batch |
| `cost_reconciliation_failed` | §5.3 identity holds within ₹0.01 |

**Constraint coverage requirement:** every code in this table must be exercised by at least one test (§14).

**Feasibility is a prerequisite for any success claim.** A strategy that improves a headline metric while violating a constraint is reported as infeasible and cannot be counted as a win.

---

## 12. Determinism

- All randomness flows from `seed`; no wall-clock, no `random` module without an explicit seeded instance, no set-iteration order dependence.
- **Sales allocation order** (when demand < supply) is fixed by `config.sales_allocation`:
  `highest_effective_price_first` → tie-break by `destination_id` ascending, then `batch_id` ascending, then earliest expiry. This makes "who sells first" deterministic and identical in baseline and planner.
- Floating-point money is rounded once at the boundary (§0.1); comparisons use a tolerance of ₹0.01 and 0.001 kg.
- `evaluation.json` excludes `generated_at` from the determinism comparison.

---

## 13. Assumptions & decisions

Status legend: **DECIDED** (confirmed by Nidhi) · **OPEN** (needs a decision) · **OWNED** (delegated).

### 13.1 Decided
| ID | Decision |
|---|---|
| **A1** | Unsold stock is **held if still fresh** at the horizon and counted **as spoiled only when expired** (§1.3, §1.4). |
| **A2** | `min_arrival_shelf_life_days = 0.5` day by default, configurable per scenario. |
| **A3** | Demand response **OFF by default**; do not assume discounts create demand. |
| **A4** | Sales allocation = `highest_effective_price_first` with deterministic tie-breaks. **Destination selection considers expected net contribution, not selling price alone** (§2.1a). |
| **A5** | Handling cost is based on **dispatched_kg**. |
| **A6** | **Single-day** planning horizon (`horizon_days = 1`); report fresh inventory remaining at the horizon **separately** from spoiled stock. |
| **A1** | Unsold stock is **held if still fresh** at the horizon and counted **as spoiled only when expired** (§1.3, §1.4). |
...
| **A7** | Discounts: configurable, **near-expiry only** (based on remaining shelf life at dispatch ≤ `near_expiry_days`; default 1.0), in **5-pp increments**, capped at **30%**. With demand response off, **default = no discount** unless the model justifies it without inventing demand (§2.2a, §2.3). |
| **A8** | Evaluation sizes: dev `10`, standard `30`, optional large `200`. |
| **A10** | Currency = **INR**. |
| **A11** | Include **procurement cost for sold goods** in net revenue (COGS). Spoilage cost defined as the unrecoverable loss on spoiled kg; **no double-counting** of procurement losses and spoilage penalties (§5.1a). |
| **U1** | `freshness_pct` = **descriptive quality indicator only**; expiry determined **solely** by shelf life + harvest age (§1.4); not a second expiry mechanism; **informational in v1** unless a documented, tested formula is added later. |
## 13. Assumptions & decisions
...

### 13.1 Decided
...
| **U1** | `freshness_pct` = **descriptive quality indicator only**; expiry determined **solely** by shelf life + harvest age (§1.4); not a second expiry mechanism; **informational in v1** unless a documented, tested formula is added later. |
| **U2** | `spoilage_penalty_per_kg` = **unrecoverable procurement-value loss** on spoiled goods; **precedence:** if provided in `cost_model.spoilage_penalty_per_kg`, use scenario-wide; else use the relevant batch's `unit_cost_per_kg`; any disposal fee is a **separate** field (§5.1a). |
| **U3** | Planner objective: **maximize net revenue** subject to hard constraints; ties broken by lower `spoilage_kg`, then higher `fulfillment_pct`; same baseline (§5.4). |
| **U3** | Planner objective: **maximize net revenue** subject to hard constraints; ties broken by lower `spoilage_kg`, then higher `fulfillment_pct`; same baseline (§5.4). |
| **U4** | `donation` and `processing` destinations are **out of scope for v1**; sales destinations (`retail`, `wholesale`) only; not counted as fulfilled customer demand (§7, §11). |
| **U5** | Discounts justified only via the §2.4 price-threshold mechanism; with demand response off, never assume discounting increases demand; apply a discount only if it improves expected net revenue, else zero. |

### 13.2 Still open
| ID | Question | Action |
|---|---|---|
| **A9 (OWNED — Iffa)** | Produce catalogue & prices (types, price/shelf-life/quantity ranges). Contract fixes only unit/semantics. | **Iffa must confirm A9 before the team treats the catalogue as finalized.** |

---

## 14. Proposed tests (`engine/tests/test_engine.py`, stdlib `unittest`)

| # | Test | Asserts |
|---|---|---|
| T1 | Inventory conservation | per batch & aggregate: `harvested == sold + fresh_inventory + spoiled` |
| T2 | No fresh-as-spoiled | a batch with fresh retained stock reports `spoiled_kg == 0` and `fresh_inventory_kg > 0` |
| T3 | Demand limit | Σ sold per destination ≤ effective demand |
| T4 | Capacity limit | Σ allocated per destination ≤ capacity |
| T5 | Inventory limit | Σ dispatched per batch ≤ harvested |
| T6 | Shelf-life rejection | dispatch with `remaining_at_arrival < min` is rejected/flagged, never accepted |
| T7 | Arrival-after-horizon | flagged `arrival_after_horizon` |
| T8 | Discount bounds | discount > eligible_max ⇒ `discount_out_of_range` |
| T9 | Unknown disruption type | raises hard error / `unknown_disruption_type` |
| T10 | Unknown reference | unknown batch/destination id ⇒ `unknown_reference` |
| T11 | Determinism | same input + seed ⇒ identical result JSON (bar `generated_at`) |
| T12 | Metric consistency | baseline & planner compute metrics via the same function; `reconciliation.check_ok == true` for both |
| T13 | Zero-demand ratio | `demand_kg == 0` ⇒ `fulfillment_pct == 100.0` and `notes` contains `"no_demand"` (no divide-by-zero) |
| T14 | Demand-response OFF | with default config, discounting changes price but never `effective_demand` |
| T15 | Infeasible exclusion | an infeasible run is not counted as a win in evaluation summary |
| T16 | No procurement/spoilage double-count | no kg contributes to both `procurement_cost` and `spoilage_cost` (§5.1a); procurement charged only on `sold_kg` |
| T17 | Net-revenue identity (both strategies) | `net_revenue == gross_revenue − procurement_cost − transport_cost − handling_cost − spoilage_cost` within ₹0.01; `check_ok == true` and `net_revenue == sum_dispatch_contributions − spoilage_cost` |
| T18 | Default = no discount | with demand response off and no `max_price_per_kg`, every dispatch has `discount_pct == 0` |
| T19 | Hold-if-fresh (A1) | arrived-unsold stock still within shelf life at horizon ⇒ `fresh_inventory_kg`, `spoiled_kg == 0` for that kg |
| T20 | Transport allocation | Σ dispatch `transport_cost` over a batch equals Σ dispatch(`dispatched_kg` × `distance_km` × `transport_per_kg_km`) |
| T21 | Handling allocation | Σ dispatch `handling_cost` over a batch equals Σ dispatch(`dispatched_kg` × `handling_per_kg`) |
| T22 | Procurement allocation | Σ dispatch procurement over a batch == batch `sold_kg × unit_cost_per_kg`; multi-dispatch batch splits correctly (§5.1b) |
| T23 | Spoilage default penalty (U2) | if `cost_model.spoilage_penalty_per_kg` omitted ⇒ per-batch `unit_cost_per_kg`; if provided ⇒ global penalty applied; `spoilage_cost == spoiled_kg × penalty` |
| T24 | Reconciliation (single subtraction) | `net_revenue == sum_dispatch_contributions − metrics.spoilage_cost` within ₹0.01 (and `check_ok == true`) — tests the aggregate identity (§5.3) |
| T25 | Unsupported destination type (U4) | `processing`/`donation` ⇒ `unsupported_destination_type`, run infeasible |
| T26 | Discount step grid (A7) | off-grid `discount_pct` ⇒ `discount_step_mismatch` |
| T27 | Objective tie-break (U3) | equal `net_revenue` within ₹0.01 ⇒ pick lower `spoilage_kg`, then higher `fulfillment_pct` |
| T28 | Constraint-code coverage (meta) | every code in §11 has ≥1 test that triggers it |

---

## 15. Change log

| Version | Date | Change |
|---|---|---|
| `1.0.0-draft` | 2026-10-14 | Initial proposed contract (revisions 1–7 applied). **Not frozen.** |
| `1.0.0-draft.2` | 2026-10-14 | Applied decisions A1–A8, A11: hold-if-fresh (§1.3–1.4), min arrival shelf 0.5 d (A2), destination selection by expected net contribution vs sales allocation (A4/§2.1a), procurement COGS + no double-count (§5.1a), default no-discount + price-threshold mechanism (§2.2a/§2.4), added tests T16–T19, restructured §13 into decided/open. **Not frozen.** |
| `1.0.0-draft.4` | 2026-10-14 | Documentation-only revision addressing review findings: removed dispatch-level spoilage_cost; made spoilage penalty optional (scenario-wide if provided, else batch unit_cost); removed unsold_stock_disposition; added selection_score and §2.5 discount mechanics; updated reconciliation/T12/T17/T24/T20/T21/T23; added near_expiry_days and zero-demand=100%; added invalid_near_expiry_days constraint. **Not frozen.** |

