# Aurenza — Pitch Deck Outline (10 Slides, 3-Minute Pitch)

---

## Slide 1: Title
**Aurenza**  
*Explainable Produce Allocation & Dispatch Planning*  
**Null Theory First** — Baseline → Optimizer → Honest Evaluation  
Nidhi Bhat · Arati · Iffa  
github.com/the-nidhi-bhat/Aurenza · aurenza-five.vercel.app

---

## Slide 2: The Problem (₹92,651 Cr Lost/Year)
- **NABCONS 2022:** India's post-harvest losses = ₹92,651 crore
- **Root cause:** Perishables routed by intuition, not optimization
- **No explainability:** Farmers/mandis can't audit dispatch decisions
- **Current tools:** Either academic (OR-Tools) or black-box SaaS — neither auditable by domain experts

---

## Slide 3: Our Approach — Null Theory First
```
1. Define the problem precisely (Contract v1.0.0)
2. Build CREDIBLE BASELINE first → FEFO (domain standard)
3. Specify objective: Maximize Net Revenue (tie-break: spoilage, fulfillment)
4. Build optimizer that MUST beat baseline — warm-started, never worse
5. Evaluate honestly: 120 scenarios, 0 infeasible runs
```
> "The baseline is the null hypothesis. The optimizer earns its keep."

---

## Slide 4: Engine Architecture (Pure Python, Zero Deps)
```
┌─────────────────────────────────────┐
│        CONTRACT v1.0.0-draft.4      │  ← Single source of truth
├─────────────────────────────────────┤
│  engine/core.py      (shared logic) │  ← Validation, pricing, feasibility,
│  engine/baseline.py  (FEFO)         │     aggregation, reconciliation
│  engine/planner.py   (Greedy)       │
│  engine/fixtures.py  (Synthetic)    │
└─────────────────────────────────────┘
        │                    │
        ▼                    ▼
   result.json          evaluation.json
        │                    │
        └────────┬───────────┘
                 ▼
        ┌─────────────────┐
        │   DASHBOARD     │  ← Zero-deps, reads JSON only
        │  (HTML/CSS/JS)  │     No engine coupling
        └─────────────────┘
```

---

## Slide 5: Cost Model — No Double Counting (Contract §5)
| Cost | Applied To | Formula |
|------|------------|---------|
| Procurement | **sold_kg** only (COGS) | sold_kg × unit_cost |
| Transport | **dispatched_kg** | dispatched_kg × distance × rate |
| Handling | **dispatched_kg** | dispatched_kg × rate |
| Spoilage | **spoiled_kg** (once) | spoiled_kg × penalty |

**Reconciliation Identity (tested):**
```
net_revenue = Σ(gross_revenue - procurement - transport - handling) - spoilage_cost
check_ok: true  (within ₹0.01)
```

---

## Slide 6: Results — 120 Scenarios, Honest Numbers
| Metric | Baseline | Planner | Win Rate |
|--------|----------|---------|----------|
| **Net Revenue** | ₹13,387 | **₹15,818** | **115/120** (+24.2% median) |
| Spoilage | 0 kg | 0 kg | 118/120 tied |
| Fulfillment | 12.93% | 9.48% | 29/120 (trade-off documented) |
| **All-Metric Wins** | — | — | **23/120** |
| Infeasible Runs | 0 | 0 | **0** |

> Planner gain is **revenue optimization**, not waste reduction (FEFO already strong on spoilage).

---

## Slide 7: Explainability — Every Decision Has a Reason
**Planner Dispatch:**
| Batch | Destination | Qty | Discount | Gain/kg | Reason |
|-------|-------------|-----|----------|---------|--------|
| B002 (Mango) | D001 City Retail | 350kg | 0% | 37.36 | "greedy gain 37.36/kg" |
| B003 (Tomato) | D001 City Retail | 200kg | 0% | 13.71 | "greedy gain 13.71/kg" |

**Baseline Dispatch (FEFO):**
| Batch | Destination | Qty | Reason |
|-------|-------------|-----|--------|
| B002 (Mango) | D004 Regional Depot | 100kg | "FEFO: expiring day 3.5 → highest price" |
| B001 (Onion) | D002 Suburb Retail | 100kg | "FEFO: expiring day 18 → full price" **(loss: -₹233)** |

> **Key insight:** Planner *holds* 200kg onions fresh (worth more later) vs baseline shipping at loss.

---

## Slide 8: Dashboard — Zero Dependencies, Full Fidelity
- **No React, no Vue, no build step** — vanilla ES6 + CSS variables
- **Reads only generated JSON** — contract §10: dashboard imports NO engine code
- **Two views:** Decision Detail (single scenario) + Evaluation (120 scenarios)
- **Accessible:** WCAG AA, keyboard nav, screen-reader labels, reduced motion
- **Dark theme, responsive, 44px touch targets**

---

## Slide 9: What's Next (Roadmap)
| Phase | Deliverable | Owner |
|-------|-------------|-------|
| **v1.0** (Now) | Contract freeze, engine, dashboard, 120-scenario eval | Nidhi, Arati |
| **v1.1** | A9 Produce Catalogue (real prices, shelf-life, demand) | **Iffa** |
| **v1.2** | Real market data integration, mandi API hooks | Team |
| **v2.0** | Multi-day horizon, stochastic demand, Pareto optimization | Research |

---

## Slide 10: Ask / Contact
**We're ready for real data.**  
A9 produce catalogue (Iffa) → production pilot.

**Links:**
- Code: github.com/the-nidhi-bhat/Aurenza
- Live: aurenza-five.vercel.app/dashboard/
- Contract: docs/CONTRACT.md

**Contact:** Nidhi Bhat — [email/LinkedIn]

---

## Backup Slides (Appendix)

### B1: Feasibility — 14 Constraint Codes, All Tested
`inventory_exceeded`, `capacity_exceeded`, `demand_exceeded`, `shelf_life_expired`, `arrival_after_horizon`, `discount_out_of_range`, `discount_step_mismatch`, `unknown_disruption_type`, `unknown_reference`, `unsupported_destination_type`, `negative_quantity`, `invalid_near_expiry_days`, `inventory_not_conserved`, `cost_reconciliation_failed`

### B2: Disruption Types Handled
Transport Strike, Demand Spike, Shelf Life Shock, Capacity Reduction, Price Drop

### B3: Determinism Guarantee
Same seed + same input = byte-identical output (excl. `generated_at`)

### B4: Test Coverage
48 tests (41 engine + 7 dashboard), 100% constraint code coverage (§11, §14)

---

## Design Notes for Deck
- **Color scheme:** Dark slate (#0f172a) + Teal accent (#14b8a6) + Amber warning (#f59e0b)
- **Typography:** Inter / JetBrains Mono for code
- **Diagrams:** Mermaid (render in Notion/Canva/PowerPoint via Mermaid Live)
- **Data:** Pull numbers directly from `demo/evaluation.json` — never manually typed
- **Screenshots:** Use `SCREENSHOT_GUIDE.md` captures