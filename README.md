# Aurenza

> **The Null Theory First Project** — An explainable produce allocation & dispatch planning engine for perishable fruits and vegetables.

Aurenza compares a deterministic **FEFO baseline** against an optimizing **planner**, allocating harvested inventory to feasible retail/wholesale destinations while respecting shelf life, demand, capacity, transport & handling costs, discounts, and disruptions — and explains every dispatch.

> **Governing reference:** [`docs/CONTRACT.md`](docs/CONTRACT.md) **v1.0.0-draft.4** (status: PROPOSED — NOT FROZEN)  
> **Assumptions & clarifications:** [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md)

---

## TL;DR — Why This Project Matters

| Aspect | What We Built |
|--------|---------------|
| **Problem** | ₹92,651 crore annual post-harvest losses in India (NABCONS 2022) — perishables routed by intuition, not optimization |
| **Approach** | Null Theory First: build a *credible baseline* (FEFO) first, then an optimizer that must *provably beat it* on net revenue |
| **Engine** | Pure Python stdlib — deterministic, auditable, zero runtime deps |
| **Strategies** | **Baseline** (FEFO: earliest expiry → highest price) vs **Planner** (greedy by per-kg gain + spoilage avoidance, warm-started from baseline) |
| **Contract** | Formal schema v1.0.0-draft.4 governing input/output/feasibility — engine, dashboard, and evaluation all conform |
| **Evaluation** | 120 scenarios (30 seeds × 4 disruption types), median **+24.2% net revenue**, 0 infeasible runs |
| **Dashboard** | Dependency-free, accessible, dark-theme UI reading *only* generated JSON — no engine coupling |

---

## Architecture Overview

```mermaid
graph TB
    subgraph Input["Input Layer"]
        S["Scenario JSON<br/>(seed + config)"]
        D["Disruptions<br/>(optional)"]
        C["Contract v1.0.0<br/>(docs/CONTRACT.md)"]
    end

    subgraph Engine["Engine Core (engine/core.py)"]
        V["Validate Schema<br/>& Config"]
        A["Apply Disruptions<br/>(5 types)"]
        P["Pricing & Demand<br/>Helpers"]
        F["Feasibility Checks<br/>(14 codes)"]
        AG["Aggregation<br/>§5-§6 Metrics"]
        RC["Reconciliation<br/>§5.3 Identity"]
    end

    subgraph Strategies["Strategies (Pure Functions)"]
        B["Baseline: FEFO<br/>(engine/baseline.py)"]
        PL["Planner: Greedy<br/>(engine/planner.py)"]
    end

    subgraph Output["Output Layer"]
        R["result.json<br/>§8 Schema"]
        E["evaluation.json<br/>§9 Schema"]
    end

    subgraph Dashboard["Dashboard (Zero-Deps)"]
        HTML["index.html"]
        CSS["styles.css"]
        JS["app.js"]
        SRV["serve.py"]
    end

    S --> V
    D --> A
    C -.-> V
    C -.-> A
    C -.-> P
    C -.-> F
    C -.-> AG
    C -.-> RC
    V --> A
    A --> P
    P --> B
    P --> PL
    B --> F
    PL --> F
    F --> AG
    AG --> RC
    RC --> R
    R --> E
    R --> HTML
    E --> HTML
    HTML --> CSS
    HTML --> JS
    JS --> SRV
```

---

## Core Concepts — Visualized

### 1. The Null Theory First Principle

```mermaid
flowchart LR
    subgraph NT["Null Theory First Methodology"]
        direction TB
        N1["Define the Problem<br/>Precisely"]
        N2["Build Credible Baseline<br/>FEFO = Domain Standard"]
        N3["Specify Objective<br/>Net Revenue + Tie-breaks"]
        N4["Build Optimizer<br/>Must Beat Baseline"]
        N5["Warm-Start<br/>Never Worse Than Baseline"]
        N6["Evaluate Honestly<br/>120 Scenarios"]
    end

    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
    N5 --> N6
```

### 2. Baseline vs Planner — Decision Flow

```mermaid
flowchart TD
    subgraph Shared["Shared Foundation (engine/core.py)"]
        SC["Scenario<br/>Validation"]
        DC["Disruption<br/>Application"]
        PH["Pricing<br/>Helpers"]
        FC["Feasibility<br/>Engine"]
        AG["Aggregation &<br/>Reconciliation"]
    end

    subgraph Baseline["Baseline Strategy (FEFO)"]
        B1["Sort Batches by<br/>Expiry ASC"]
        B2["For Each Batch:<br/>Rank Destinations by<br/>Effective Price DESC"]
        B3["Allocate at<br/>Discount = 0%"]
        B4["Respect All<br/>Hard Constraints"]
    end

    subgraph Planner["Planner Strategy (Greedy)"]
        P1["Build All Feasible<br/>Batch-Dest Edges"]
        P2["Score Each Edge by<br/>Per-Kg Gain +<br/>Spoilage Avoided"]
        P3["Apply Min Discount<br/>to Unlock Price Caps<br/>(5% grid, up to 30%)"]
        P4["Allocate Greedy<br/>by Gain DESC"]
        P5["Warm-Start from<br/>Baseline Plan"]
        P6["Keep Better Plan<br/>Under §5.4 Order"]
    end

    SC --> DC
    DC --> PH
    PH --> B1
    PH --> P1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    B4 --> P5
    P5 --> P6
    B4 --> AG
    P6 --> AG
    AG --> FC
    FC --> AG
    AG --> RC["Reconciliation<br/>Check OK"]
```

### 3. Cost & Revenue Model (§5)

```mermaid
graph LR
    subgraph Dispatch["Per-Dispatch Accounting"]
        QK["Quantity Dispatched<br/>(dispatched_kg)"]
        SK["Quantity Sold<br/>(sold_kg)"]
        AUS["Arrived Unsold<br/>(arrived_unsold_kg)"]
    end

    subgraph Revenue["Revenue (Sold Only)"]
        EP["Effective Price<br/>= base x (1 - disc%)"]
        GR["Gross Revenue<br/>= sold_kg x EP"]
    end

    subgraph Costs["Costs"]
        PC["Procurement<br/>= sold_kg x unit_cost<br/>(COGS only on sold)"]
        TC["Transport<br/>= dispatched_kg x distance x rate"]
        HC["Handling<br/>= dispatched_kg x rate"]
        SC["Spoilage<br/>= spoiled_kg x penalty<br/>(once, at aggregate)"]
    end

    subgraph Aggregates["Aggregate (§5.3)"]
        EC["Expected Contribution<br/>= GR - PC - TC - HC<br/>(excludes spoilage)"]
        SDE["Sum Dispatch<br/>Contributions"]
        NR["Net Revenue<br/>= SDE - Spoilage Cost"]
    end

    QK --> SK
    QK --> AUS
    SK --> EP
    EP --> GR
    SK --> PC
    QK --> TC
    QK --> HC
    GR --> EC
    PC --> EC
    TC --> EC
    HC --> EC
    EC --> SDE
    SC --> NR
    SDE --> NR
```

### 4. Inventory Conservation (§1.4)

```mermaid
flowchart TD
    H["Harvested kg<br/>batch.quantity_kg"]
    
    subgraph Terminal["Terminal States at Horizon"]
        S["Sold kg<br/>dispatched, arrived, sold"]
        FI["Fresh Inventory kg<br/>still usable at horizon"]
        SP["Spoiled kg<br/>expired at horizon"]
    end

    H == Conservation ==> S
    H == Conservation ==> FI
    H == Conservation ==> SP
    
    style H fill:#fef3c7,stroke:#f59e0b
    style S fill:#d1fae5,stroke:#10b981
    style FI fill:#dbeafe,stroke:#3b82f6
    style SP fill:#fee2e2,stroke:#ef4444
```

**Invariant (enforced by test T1):**
```
harvested_kg == sold_kg + fresh_inventory_kg + spoiled_kg   (±0.001 kg)
```

---

## Data Flow — End to End

```mermaid
sequenceDiagram
    participant User
    participant CLI as run_plan.py
    participant Core as engine.core
    participant Baseline as engine.baseline
    participant Planner as engine.planner
    participant Output as result.json
    participant Dashboard as app.js

    User->>CLI: python -m engine.scripts.run_plan --seed 1
    CLI->>Core: load_scenario() → validate_scenario()
    Core-->>CLI: Validated Scenario
    CLI->>Core: apply_disruptions()
    Core-->>CLI: Disrupted Scenario
    CLI->>Baseline: plan_baseline(scenario)
    Baseline-->>CLI: Baseline Flows
    CLI->>Planner: plan_planner(scenario, baseline_flows)
    Planner-->>CLI: Planner Flows (warm-started)
    CLI->>Core: build_dispatches() × 2
    Core-->>CLI: Dispatches with §5 Cost Attribution
    CLI->>Core: aggregate() × 2
    Core-->>CLI: Metrics, BatchSummary, Reconciliation
    CLI->>Core: compute_improvement()
    Core-->>CLI: Improvement Block
    CLI->>Core: build_result()
    Core-->>CLI: Full §8 Result Object
    CLI->>Output: save_json(result.json)
    Output-->>Dashboard: fetch(result.json)
    Dashboard->>User: Render Decision Detail + Evaluation
```

---

## Evaluation — 120 Scenarios, Honest Numbers

```mermaid
graph TD
    subgraph Gen["Scenario Generation (fixtures.py)"]
        G1["30 Seeds x 4 Configs = 120"]
        G2["Base Scenario"]
        G3["Transport Strike"]
        G4["Demand Spike"]
        G5["Shelf Life Shock"]
        G6["Capacity Reduction"]
        G7["Price Drop"]
    end

    subgraph Run["Evaluation Run (run_eval.py)"]
        R1["Same Scenario -> Both Strategies"]
        R2["Compute Metrics Per Run"]
        R3["Win Counting §9.4 Rules"]
        R4["Aggregate Stats Mean/Min/Max/Std"]
    end

    subgraph Results["Key Results (demo/evaluation.json)"]
        Res1["Net Revenue: Planner Wins 115/120"]
        Res2["Median Improvement: +24.2%"]
        Res3["Spoilage: Tied 118/120 (Baseline Strong)"]
        Res4["Fulfillment: Planner Lower 91/120 (Trade-off)"]
        Res5["0 Infeasible Runs"]
    end

    G1 --> G2
    G1 --> G3
    G1 --> G4
    G1 --> G5
    G1 --> G6
    G1 --> G7
    G2 --> R1
    G3 --> R1
    G4 --> R1
    G5 --> R1
    G6 --> R1
    G7 --> R1
    R1 --> R2
    R2 --> R3
    R3 --> R4
    R4 --> Res1
    R4 --> Res2
    R4 --> Res3
    R4 --> Res4
    R4 --> Res5
```

### Evaluation Dashboard View

```mermaid
graph LR
    subgraph EvalUI["Evaluation Tab (dashboard/index.html)"]
        EC["Summary Cards<br/>Net Revenue / Spoilage / Fulfillment<br/>Win Counts + %"]
        CH["Charts<br/>Per-Seed & Per-Disruption"]
        SE["Scenario Explorer<br/>Dropdown -> Detail View"]
    end

    EC --> CH
    CH --> SE
```

---

## Dashboard — Zero Dependencies, Full Fidelity

```mermaid
graph TB
    subgraph Dash["Dashboard Architecture"]
        HTML["index.html<br/>Semantic, Accessible"]
        CSS["styles.css<br/>Responsive, Dark Theme,<br/>CSS Variables"]
        JS["app.js<br/>Vanilla ES6, No Framework"]
        SRV["serve.py<br/>stdlib http.server"]
    end

    subgraph Data["Data Sources (Read-Only)"]
        DR["demo/result.json<br/>Committed Fixture"]
        DE["demo/evaluation.json<br/>120-Scenario Fixture"]
        OR["output/*.json<br/>Local Regenerated"]
    end

    subgraph Views["Two Views"]
        OV["Overview Tab<br/>Single Scenario Detail"]
        EV["Evaluation Tab<br/>120-Scenario Aggregate"]
    end

    HTML --> CSS
    HTML --> JS
    JS --> SRV
    DR --> JS
    DE --> JS
    OR --> JS
    JS --> OV
    JS --> EV
```

### Dashboard Features

| View | What You See |
|------|--------------|
| **Overview** | KPI cards (Net Revenue, Spoilage, Fulfillment), both dispatch tables with quantities, destinations, discounts, reasons, batch inventory & spoilage table, accounting reconciliation |
| **Evaluation** | Aggregate win counts across 120 runs, per-metric charts, scenario selector with per-scenario drill-down |

---

## Quick Start

### Prerequisites
- **Python 3.11+** (stdlib only — no pip install needed for engine)
- `pytest` for tests (`pip install pytest`)

### Run Everything

```powershell
# 1. Run the full test suite (48 tests: 41 engine + 7 dashboard)
python -m pytest -q

# 2. Generate the committed demo output (baseline vs planner, one scenario)
python -m engine.scripts.run_plan --seed 1

# 3. Regenerate the multi-seed evaluation summary (120 scenarios)
python -m engine.scripts.run_eval

# 4. Open the dashboard (serves repo root on 127.0.0.1:8000)
python dashboard/serve.py
# Then open http://127.0.0.1:8000/dashboard/
```

### Outputs Generated

| File | Description |
|------|-------------|
| `demo/result.json` | One generated demo scenario, both strategies (committed fixture) |
| `demo/evaluation.json` | 120 scenarios, aggregate stats (committed fixture) |
| `output/<scenario_id>/result.json` | Per-scenario outputs (gitignored, regenerable) |
| `output/evaluation.json` | Same as demo/evaluation.json (gitignored) |

> **All outputs are produced by the real engine** — they are synthetic demo data from labelled fixtures, not observed real-world performance.

---

## Repository Structure

```
Aurenza/
├── docs/
│   ├── CONTRACT.md          # Interface contract v1.0.0-draft.4 (source of truth)
│   └── ASSUMPTIONS.md       # Assumptions, clarifications, open items (A9)
├── engine/
│   ├── core.py              # Shared logic: validation, disruptions, pricing, aggregation, feasibility, reconciliation
│   ├── baseline.py          # FEFO baseline strategy
│   ├── planner.py           # Greedy planner strategy (warm-started from baseline)
│   ├── fixtures.py          # Deterministic synthetic scenario generator
│   ├── scripts/
│   │   ├── run_plan.py      # Single-scenario CLI → result.json
│   │   └── run_eval.py      # Multi-seed evaluation CLI → evaluation.json
│   └── tests/
│       └── test_engine.py   # Contract test suite (41 tests)
├── dashboard/
│   ├── index.html           # Markup (semantic, accessible, no framework)
│   ├── styles.css           # Styling (responsive, dark theme, CSS vars)
│   ├── app.js               # Logic — reads generated JSON only (no engine import)
│   ├── serve.py             # stdlib static server
│   └── test_dashboard.py    # Dashboard tests (7 tests, includes live server test)
├── demo/
│   ├── result.json          # Committed generated demo output (seed 1)
│   └── evaluation.json      # Committed generated evaluation (120 scenarios)
├── output/                  # Gitignored generated outputs (regenerable)
└── README.md                # This file
```

---

## CLI Reference

```powershell
# Single scenario
python -m engine.scripts.run_plan [--seed N] [--scenario PATH] [--out PATH] [--also-output]

# Multi-seed evaluation
python -m engine.scripts.run_eval [--mode dev|standard|large] [--out PATH]
```

| Flag | Description |
|------|-------------|
| `--seed N` | Scenario seed (default: 1) |
| `--scenario PATH` | External scenario JSON instead of generated fixture |
| `--out PATH` | Output path (default: `demo/result.json` or `demo/evaluation.json`) |
| `--also-output` | Also write `output/<scenario_id>/result.json` |
| `--mode` | `dev`=10 seeds, `standard`=30 seeds, `large`=200 seeds |

---

## Constraints Enforced (§11) — All Tested

| Code | Constraint |
|------|------------|
| `unknown_disruption_type` | Every disruption type in documented enum |
| `negative_quantity` | All quantities ≥ 0 |
| `inventory_exceeded` | Σ dispatched per batch ≤ harvested |
| `capacity_exceeded` | Σ allocated per destination ≤ capacity |
| `demand_exceeded` | Σ sold per dest/produce ≤ effective demand |
| `shelf_life_expired` | Remaining at arrival ≥ min_arrival_shelf_life_days |
| `arrival_after_horizon` | dispatch_day + transit_days ≤ horizon_days |
| `discount_out_of_range` | 0 ≤ discount_pct ≤ eligible_max_pct |
| `discount_step_mismatch` | discount_pct on step_pct grid |
| `invalid_near_expiry_days` | near_expiry_days ≥ 0 |
| `unsupported_destination_type` | type ∈ {retail, wholesale} in v1 |
| `unknown_reference` | All batch_id/destination_id/produce exist |
| `inventory_not_conserved` | §1.1 identity holds per batch |
| `cost_reconciliation_failed` | §5.3 identity holds within ₹0.01 |

**Feasibility is a prerequisite for any success claim.** A strategy that improves a headline metric while violating a constraint is reported as infeasible and cannot be counted as a win.

---

## Verification — All Green

```mermaid
graph LR
    subgraph Tests["Test Suite"]
        T1["pytest -q<br/>48 Tests Pass"]
        T2["engine/tests/test_engine.py<br/>41 Contract Tests"]
        T3["dashboard/test_dashboard.py<br/>7 Tests + Live Server"]
    end

    subgraph Browser["Browser Verification"]
        B1["browser_check_platform.py<br/>115/115 Pass"]
        B2["browser_check_editorial.py<br/>103/103 Pass"]
        B3["prod_platform_smoke.py<br/>33/33 vs Prod"]
        B4["check_contrast.py<br/>132 Pairs"]
        B5["verify_fixes.py<br/>64 Checks"]
        B6["audit_landing.py<br/>Exit 0, Zero Findings"]
    end

    subgraph NonVacuity["Non-Vacuity Proofs"]
        NV1["probe_a11y_mutation.py"]
        NV2["probe_guard_mutation.py"]
    end

    T1 --> B1
    T2 --> B2
    T3 --> B3
    B1 --> NV1
    B2 --> NV2
```

### Run Verification Locally

```powershell
# Unit tests (from repo root)
python -m pytest -q                    # 48 tests

# Dashboard tests (from worktree)
# Note: pytest from repo root picks up old engine on sys.path
# Use the worktree: C:\Users\theni\AppData\Local\Temp\opencode\aurenza-ui
cd C:\Users\theni\AppData\Local\Temp\opencode\aurenza-ui
python -m pytest dashboard -q          # 10 tests
python -m pytest -q                    # 77 tests
```

---

## Key Design Decisions (From Contract)

| ID | Decision | Impact |
|----|----------|--------|
| **A1** | Unsold stock held if fresh at horizon; spoiled only when expired | No double-counting, realistic inventory |
| **A2** | `min_arrival_shelf_life_days = 0.5` default | Configurable quality floor |
| **A3** | Demand response OFF by default | Discounts don't invent demand |
| **A4** | Sales allocation = highest effective price first | Deterministic, fair |
| **A5** | Handling cost on dispatched_kg | Matches physical reality |
| **A6** | Single-day horizon (`horizon_days = 1`) | Simplicity, fresh inventory reported separately |
| **A7** | Discounts: near-expiry only, 5% grid, ≤30%, justified | Prevents gaming, auditable |
| **A8** | Evaluation sizes: dev=10, standard=30, large=200 | Reproducible scales |
| **A11** | Procurement COGS on sold_kg only; spoilage penalty separate | No double-counting (test T16) |
| **U3** | Planner objective: max net_revenue → min spoilage → max fulfillment | Clear, contract-specified ordering |
| **U4** | Donation/processing out of scope for v1 | Focus on sales destinations |

> **Open:** **A9** — Produce catalogue & prices (owner: Iffa). Current `engine/fixtures.py` uses synthetic placeholders.

---

## Honest Limitations

| Limitation | Status |
|------------|--------|
| **Synthetic data only** | `engine/fixtures.py` clearly labelled; real data awaits A9 |
| **Disruption effects provisional** | Contract names 5 types but not parameters (see ASSUMPTIONS.md) |
| **Baseline undefined by contract** | FEFO is team decision; strong baseline = honest comparison |
| **Planner not globally optimal** | Bounded deterministic heuristic, not combinatorial search |
| **Spoilage reduction typically 0** | FEFO already dispatches expiring stock first — planner gain is net revenue |
| **`notes="no_demand"` absent from §8 schema** | Engine omits to stay schema-exact (CLARIFICATION-1) |

---

## Roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **v1.0 (Current)** | Contract v1.0.0-draft.4 | PROPOSED |
| | Engine + Baseline + Planner | IMPLEMENTED |
| | Dashboard + Tests | IMPLEMENTED |
| | 120-Scenario Evaluation | COMPLETE |
| **v1.1 (Next)** | Freeze Contract v1.0.0 | PENDING REVIEW |
| | A9 Produce Catalogue (Iffa) | OPEN |
| | Real Market Data Integration | PLANNED |
| **v2.0 (Future)** | Multi-Day Horizon | DESIGNED |
| | Stochastic Demand | RESEARCH |
| | ML-Assisted Price Forecasting | EXPLORATORY |
| | Multi-Objective Pareto | EXPLORATORY |

---

## Contributing

1. **Read the contract first** — `docs/CONTRACT.md` is the source of truth
2. **Run tests before changing** — `python -m pytest -q`
3. **Follow the Null Theory First principle** — any new strategy must beat the baseline on net revenue
4. **Maintain determinism** — same seed = byte-identical output
5. **Update tests** — every new constraint code needs a test (§11, §14)

---

## License

MIT License — see `LICENSE` (to be added).

---

## Acknowledgments

- **Nidhi** — Engine architecture, contract, baseline, planner, evaluation
- **Arati** — Dashboard (HTML/CSS/JS), accessibility, visual design
- **Iffa** — Data & evaluation (A9 produce catalogue, market data) — *open*

---

## Live Demo

**Production:** https://aurenza-five.vercel.app  
**Dashboard:** `/dashboard/` (after running `python dashboard/serve.py`)

---

> **Built with Null Theory First discipline.**  
> *Baseline first. Optimizer second. Honest evaluation always.*