# Aurenza — Project Writeup / Portfolio Case Study

## One-Liner
An explainable produce allocation engine that proves every dispatch decision — comparing a credible FEFO baseline against a revenue-optimizing planner across 120 synthetic scenarios, with full accounting reconciliation and zero-runtime-dependency dashboard.

---

## Problem Space
**India loses ₹92,651 crore/year to post-harvest waste** (NABCONS 2022). Perishable fruits and vegetables move through mandis and supply chains based on heuristic decisions — "send the ripest to the nearest market" — without optimization, audit trails, or economic justification. Existing solutions are either:
- Academic (OR-Tools, CP-SAT) — powerful but opaque to domain experts
- Commercial SaaS — black-box, expensive, not designed for Indian mandi realities
- Spreadsheet-based — error-prone, non-deterministic, no feasibility guarantees

**Gap:** No tool that (a) uses a credible domain baseline, (b) optimizes provably against it, (c) explains every decision in domain language, (d) is auditable by non-programmers.

---

## Solution: Null Theory First
We adopted a **Null Theory First** methodology — a discipline borrowed from scientific computing:

1. **Contract First** — `docs/CONTRACT.md` v1.0.0-draft.4 defines every input, output, metric, and feasibility rule before any code exists
2. **Baseline First** — Implement FEFO (First-Expired-First-Out), the domain-standard heuristic, as the *null hypothesis*
3. **Objective Fixed by Contract** — Maximize net revenue → minimize spoilage → maximize fulfillment (§5.4)
4. **Optimizer Must Earn Its Keep** — Planner warm-starts from baseline; if it can't beat baseline on net revenue, baseline wins
5. **Honest Evaluation** — 120 scenarios (30 seeds × 4 disruptions), same input for both strategies, 0 infeasible runs

This prevents "strawman baselines" and "metric hacking" — common in ML-for-goods projects.

---

## Technical Architecture

### Engine (Pure Python Stdlib)
```
engine/
├── core.py        # Shared kernel: validation, disruptions, pricing, feasibility, aggregation, reconciliation
├── baseline.py    # FEFO: sort by expiry → route to highest effective price → discount=0
├── planner.py     # Greedy: build all feasible edges → score by per-kg gain + spoilage avoided → allocate desc
├── fixtures.py    # Deterministic synthetic scenarios (seeded RNG)
└── scripts/
    ├── run_plan.py   # Single scenario → result.json
    └── run_eval.py   # Multi-seed → evaluation.json
```

**Key Properties:**
- **Zero runtime dependencies** — stdlib only (`json`, `random`, `os`, `copy`)
- **Deterministic** — same seed = byte-identical output (excl. timestamp)
- **Contract-governed** — 14 feasibility codes, all tested (§11, §14)
- **Reconciling** — `net_revenue = sum_dispatch_contributions - spoilage_cost` within ₹0.01 (test T24)

### Cost Model (Contract §5 — No Double Counting)
| Cost | Applied To | Why |
|------|------------|-----|
| Procurement (COGS) | **sold_kg only** | Unsold/spoiled kg never procured |
| Transport | dispatched_kg | Physically moved regardless of sale |
| Handling | dispatched_kg | Handled on arrival |
| Spoilage | spoiled_kg (once) | Unrecoverable value loss |

**Innovation:** Procurement and spoilage are *mutually exclusive* per kg — enforced by test T16.

### Dashboard (Zero Dependencies)
```
dashboard/
├── index.html    # Semantic HTML, ARIA, skip links
├── styles.css    # CSS variables, dark theme, responsive, 44px touch targets
├── app.js        # Vanilla ES6, fetches JSON only — NO engine import
└── serve.py      # stdlib http.server
```

**Two Views:**
1. **Overview** — Single scenario: KPI cards, both dispatch tables with reasons, batch inventory, reconciliation
2. **Evaluation** — 120 scenarios: aggregate wins, per-seed charts, scenario selector with disruption drill-down

---

## Results (From `demo/evaluation.json` — 120 Scenarios)

| Metric | Baseline | Planner | Verdict |
|--------|----------|---------|---------|
| **Net Revenue (median)** | — | — | **Planner +24.2%** |
| Net Revenue Wins | 5 | **115** | **Planner dominates** |
| Spoilage | 0 kg | 0 kg | **Tied (118/120)** |
| Fulfillment | Higher | Lower | **Baseline wins (91/120)** — documented trade-off |
| All-Metric Wins | 0 | **23** | Planner beats baseline on all 3 simultaneously |
| Infeasible Runs | **0** | **0** | **All plans valid** |

**Critical Insight:** With FEFO baseline (which already dispatches expiring stock first), spoilage reduction is ~0. The planner's value is **routing high-value produce to higher-margin destinations** and **avoiding negative-contribution dispatches** (e.g., not shipping onions 30km at a loss).

---

## Engineering Rigor

| Practice | Evidence |
|----------|----------|
| Contract-driven development | `docs/CONTRACT.md` v1.0.0-draft.4 (575 lines) |
| Constraint coverage | 14 codes in §11, every code has ≥1 test (§14/T28) |
| Determinism | `random.Random(seed)` everywhere, no wall-clock |
| Reconciliation testing | T24: `net_revenue == sum_contributions - spoilage_cost` ±₹0.01 |
| Double-count prevention | T16: no kg in both procurement_cost and spoilage_cost |
| Browser verification | 115/115 platform checks, 103/103 editorial, 33/33 prod smoke |
| Accessibility | WCAG AA, keyboard nav, `role="alert"`, skip links, reduced motion |
| Non-vacuity proofs | Mutation tests prove a11y/guard checks catch real regressions |

---

## What Makes This Different

| Typical Hackathon Project | Aurenza |
|---------------------------|---------|
| "AI-powered optimization" | Deterministic heuristic with contract |
| Black-box model | Every dispatch has a `reason` field |
| Single happy-path demo | 120 scenarios × 2 strategies × 4 disruptions |
| Metrics claimed in slides | Metrics computed by engine, verified by tests |
| "Scalable architecture" | Single-file stdlib engine, O(batches×destinations) |
| Frontend framework du jour | Zero-dep vanilla JS reading JSON only |

---

## Honest Limitations
- **Synthetic data only** — `engine/fixtures.py` uses invented prices/demand/shelf-life (A9 open)
- **Disruption parameters provisional** — Contract names 5 types but not their effects (ASSUMPTIONS.md)
- **Single-day horizon** — Multi-day is v2 (A6)
- **Planner not globally optimal** — Bounded greedy heuristic, not combinatorial search
- **Donation/processing out of scope** — v1 = retail/wholesale only (U4)

---

## Team
| Role | Contributor |
|------|-------------|
| Engine, Contract, Baseline, Planner, Evaluation | **Nidhi Bhat** |
| Dashboard (HTML/CSS/JS), Accessibility, Visual Design | **Arati** |
| Data & Evaluation, Produce Catalogue (A9) | **Iffa** (open) |

---

## Links
- **Repository:** https://github.com/the-nidhi-bhat/Aurenza
- **Live Demo:** https://aurenza-five.vercel.app/dashboard/
- **Contract:** `docs/CONTRACT.md`
- **Assumptions:** `docs/ASSUMPTIONS.md`

---

## Tech Stack Summary
| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ (stdlib only) |
| Testing | pytest (stdlib `unittest` compatible) |
| Frontend | Vanilla HTML/CSS/JS (ES6 modules) |
| Server | `http.server` (stdlib) |
| Deployment | Vercel (static) |
| CI | GitHub Actions (pytest on push) |
| Diagrams | Mermaid (in README/docs) |

---

## Future Work (Prioritized)
1. **A9 Produce Catalogue** — Real prices, shelf-life curves, demand patterns from mandi data (Iffa)
2. **Contract Freeze** — Reviewer sign-off → v1.0.0
3. **Multi-Day Horizon** — Rolling optimization with inventory carryover
4. **Stochastic Demand** — Scenario tree optimization instead of single-point
5. **Mandi API Integration** — Real-time arrival/price feeds
6. **Farmer-Facing Interface** — Hindi/Marathi, voice input, SMS alerts