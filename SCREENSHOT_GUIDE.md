# Aurenza — Screenshot Guide for Submission

## Required Screenshots (Capture These Exact Views)

### 1. Overview — KPI Cards (Money Shot)
**URL:** `http://localhost:8000/dashboard/` (Overview tab active)
**What to show:**
- Net Revenue: Baseline ₹13,387 → Planner ₹15,818 **(+18.2%)**
- Spoilage: Both 0 kg (tied)
- Fulfillment: Baseline 12.93% → Planner 9.48%
- Verdict badge: "Planner wins on net revenue"
**Crop:** Top 600px of viewport
**Filename:** `01-overview-kpi.png`

---

### 2. Overview — Planner Dispatch Table (Explainability)
**URL:** Same, scroll to "Planner plan" section
**What to show:**
- All dispatch rows with: batch_id, destination_id, quantity_kg, discount_pct, expected_contribution, **reason**
- Highlight: `reason` column shows "greedy gain 37.36/kg" — every decision explained
**Crop:** Full table + panel header
**Filename:** `02-planner-dispatches.png`

---

### 3. Overview — Baseline Dispatch Table (Comparison)
**URL:** Same, scroll to "Baseline plan (FEFO)" section
**What to show:**
- FEFO reasoning: "FEFO: mango batch expiring day 3.5 → City Retail at full price"
- Contrast: baseline ships onions at negative contribution (-₹233, -₹1,397)
**Crop:** Full table + panel header
**Filename:** `03-baseline-dispatches.png`

---

### 4. Overview — Batch Inventory & Spoilage (Conservation Proof)
**URL:** Same, scroll to "Batch inventory & spoilage" panel
**What to show:**
- Planner column: B001 (onions) → 200 kg fresh_inventory, 0 spoiled
- Baseline column: B001 → 0 fresh, 0 spoiled (all shipped)
- Conservation invariant holds: harvested = sold + fresh + spoiled
**Crop:** Full table
**Filename:** `04-batch-inventory.png`

---

### 5. Overview — Accounting Reconciliation (Trust)
**URL:** Same, scroll to "Accounting reconciliation" panel
**What to show:**
- `sum_dispatch_contributions`: 15,818.00
- `spoilage_cost`: 0.00
- `net_revenue`: 15,818.00
- `check_ok`: **true** (green checkmark)
**Crop:** Full panel
**Filename:** `05-reconciliation.png`

---

### 6. Evaluation — Aggregate Win Counts (Scale)
**URL:** `http://localhost:8000/dashboard/` → Click "Evaluation" tab
**What to show:**
- Three summary cards: Net Revenue (115 wins), Spoilage (0 wins, 118 ties), Fulfillment (5 wins)
- "All metrics" win: 23/120
- 0 infeasible runs for both strategies
**Crop:** Full kpi-row + eval-cards
**Filename:** `06-eval-summary.png`

---

### 7. Evaluation — Per-Seed Chart (Depth)
**URL:** Same, scroll to charts section
**What to show:**
- Net revenue per seed: planner line consistently above baseline
- Hover tooltip showing exact values (if interactive)
**Crop:** Chart area + legend
**Filename:** `07-eval-chart.png`

---

### 8. Evaluation — Scenario Explorer (Drill-Down)
**URL:** Same, use dropdown "Scenario" → select "demo_seed_1 (transport_strike)"
**What to show:**
- Disruption badge: "transport_strike"
- Per-scenario KPIs showing planner adapts to capacity loss
- Dispatch table for that specific disrupted scenario
**Crop:** Full scenario view
**Filename:** `08-scenario-drilldown.png`

---

### 9. Terminal — Tests Passing (Credibility)
**Command:** `python -m pytest -q`
**What to show:**
- `50 passed in 1.xx s`
- Clean, no warnings
**Crop:** Terminal window showing command + output
**Filename:** `09-tests-passing.png`

---

### 10. Terminal — Evaluation Run (Reproducibility)
**Command:** `python -m engine.scripts.run_eval`
**What to show:**
- `wrote output/evaluation.json (120 scenarios, 23 all-metric planner wins)`
**Crop:** Terminal window
**Filename:** `10-eval-run.png`

---

### 11. GitHub Repo — Landing Page (Open Source Proof)
**URL:** `https://github.com/the-nidhi-bhat/Aurenza`
**What to show:**
- README with Mermaid diagrams rendering
- Green check on latest commit (tests passing via Actions if configured)
- File tree visible
**Crop:** Browser viewport
**Filename:** `11-github-repo.png`

---

### 12. Vercel Production — Live Demo (Deployment)
**URL:** `https://aurenza-five.vercel.app/dashboard/`
**What to show:**
- Live dashboard loading from production
- Same data as local (demo fixtures)
**Crop:** Full dashboard view
**Filename:** `12-vercel-live.png`

---

## Capture Settings

| Setting | Value |
|---------|-------|
| Resolution | 1920×1080 minimum |
| Format | PNG (lossless) |
| Browser | Chrome/Edge (consistent rendering) |
| Zoom | 100% (Ctrl+0) |
| Theme | Dark (default) |
| DPI | 96 or 144 (system default) |

---

## Quick Capture Script (PowerShell)

```powershell
# Start dashboard
python dashboard/serve.py
# Wait for "Serving on http://127.0.0.1:8000"
# Open http://127.0.0.1:8000/dashboard/ in browser
# Use Win+Shift+S (Snip & Sketch) for each shot
# Save to .godmode/evidence/screenshots/
```

---

## Submission Gallery Order (Devfolio/Devpost)

1. `01-overview-kpi.png` — **Hero image** (biggest impact)
2. `06-eval-summary.png` — Scale proof
3. `02-planner-dispatches.png` — Explainability
4. `04-batch-inventory.png` — Conservation
5. `05-reconciliation.png` — Trust
6. `08-scenario-drilldown.png` — Disruption handling
7. `09-tests-passing.png` — Engineering rigor
8. `12-vercel-live.png` — Deployed
9. `11-github-repo.png` — Open source
10. `07-eval-chart.png` — Depth
11. `03-baseline-dispatches.png` — Comparison
12. `10-eval-run.png` — Reproducibility

---

## Alt Text for Accessibility (Submission Form)

| File | Alt Text |
|------|----------|
| 01-overview-kpi.png | "Dashboard KPI cards showing planner net revenue ₹15,818 vs baseline ₹13,387 (+18.2%), spoilage tied at 0kg, fulfillment 9.48% vs 12.93%" |
| 02-planner-dispatches.png | "Planner dispatch table with 2 rows: mango 350kg to City Retail (gain 37.36/kg), tomato 200kg to City Retail (gain 13.71/kg), each with reason column" |
| 04-batch-inventory.png | "Batch inventory table: planner holds 200kg onions as fresh inventory (not shipped at loss), baseline ships all 200kg at negative contribution" |
| 05-reconciliation.png | "Accounting reconciliation: sum_dispatch_contributions 15818.00, spoilage_cost 0.00, net_revenue 15818.00, check_ok true" |
| 06-eval-summary.png | "Evaluation summary: 115/120 net revenue wins, 118/120 spoilage ties, 23/120 all-metric wins, 0 infeasible runs" |
| 08-scenario-drilldown.png | "Transport strike disruption scenario: planner adapts routing when D002 capacity reduced to 0" |

---

## Checklist Before Submission

- [ ] All 12 screenshots captured
- [ ] Named exactly as specified
- [ ] Saved to `.godmode/evidence/screenshots/`
- [ ] Alt text documented above
- [ ] No sensitive data visible (no .env, no tokens)
- [ ] Dashboard shows "Synthetic data" badge
- [ ] README renders on GitHub with Mermaid
- [ ] Vercel deployment accessible