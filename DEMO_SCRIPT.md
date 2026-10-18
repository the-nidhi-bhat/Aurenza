# Aurenza — Demo Video Script (2-3 minutes)

## Target: Hackathon Submission / Devfolio / Portfolio

---

### 0:00–0:15 — Hook & Problem Statement
**Visual:** Terminal showing `python -m engine.scripts.run_eval` → "120 scenarios, 23 all-metric wins"
**Audio:**
> "India loses ₹92,651 crore annually to post-harvest waste. Perishables are routed by intuition, not optimization. Aurenza changes that — an explainable allocation engine that proves every dispatch decision."

---

### 0:15–0:45 — Null Theory First (The Methodology)
**Visual:** Architecture diagram (Mermaid from README) — highlight "Baseline → Planner → Warm-Start"
**Audio:**
> "We follow Null Theory First: build a credible baseline first — FEFO, the domain standard. Then build an optimizer that must *provably beat it* on net revenue. The planner warm-starts from the baseline, so it's never worse. Honest comparison, no strawmen."

---

### 0:45–1:30 — Live Dashboard Walkthrough
**Visual:** Browser at `http://localhost:8000/dashboard/`

**Tab 1: Overview (Decision Detail)**
- Show KPI cards: Baseline ₹13,387 vs Planner ₹15,818 (+18.2%)
- Click through dispatch tables — highlight `reason` column (explainability)
- Show batch inventory: Planner holds 200kg onions fresh (baseline shipped at loss)
- Show reconciliation: `check_ok: true` — accounting identity holds

**Tab 2: Evaluation (120 Scenarios)**
- Show aggregate win counts: Net Revenue 115/120, Spoilage tied 118/120
- Select a disruption scenario (transport_strike) — show planner adapts
- Point: 0 infeasible runs — every plan respects all hard constraints

---

### 1:30–2:00 — Under the Hood (Technical Credibility)
**Visual:** Split screen — `engine/core.py` (shared logic) + `engine/planner.py` (greedy edges)
**Audio:**
> "Pure Python stdlib — zero runtime dependencies. Contract v1.0.0-draft.4 governs everything: input schema, 14 feasibility codes, cost attribution, reconciliation. 48 tests cover every constraint. Deterministic: same seed = byte-identical output."

---

### 2:00–2:20 — Results That Matter
**Visual:** Key metrics from `demo/evaluation.json`
- Median net revenue improvement: **+24.2%**
- Spoilage: tied (FEFO already strong) — planner gain is *revenue*, not waste reduction
- Fulfillment trade-off documented honestly (planner lower in 91/120)

---

### 2:20–2:40 — What's Next & Call to Action
**Visual:** Roadmap timeline from README
**Audio:**
> "Contract freeze pending review. A9 produce catalogue (real market data) is the open item. Deployed at aurenza-five.vercel.app. Code at github.com/the-nidhi-bhat/Aurenza. Ready for real data and real impact."

---

### 2:40 — End Card
**Visual:** Logo + GitHub URL + Vercel URL + "Null Theory First"
**Audio:** (silence or gentle music fade)

---

## Recording Checklist
- [ ] Record at 1080p/30fps minimum
- [ ] Use OBS or similar (screen + audio)
- [ ] Test microphone levels first
- [ ] Run `python dashboard/serve.py` before recording
- [ ] Have `demo/result.json` and `demo/evaluation.json` present
- [ ] Browser zoom at 100% for clean text
- [ ] Dark theme shows well on recording

---

## Fallback: Static Screenshots (If Video Fails)
Capture these 6 frames for submission gallery:
1. **Overview KPI cards** — baseline vs planner net revenue
2. **Planner dispatch table** — with reasons visible
3. **Batch inventory table** — fresh vs spoiled split
4. **Evaluation summary cards** — win counts
5. **Scenario selector + disruption detail**
6. **Reconciliation block** — `check_ok: true`

---

## Talking Points for Judges (Q&A Prep)
| Question | Answer |
|----------|--------|
| "Why not use OR-Tools/CP-SAT?" | Bounded heuristic is deterministic, auditable, explains every decision. Global optimum not required — *beating FEFO credibly* is. |
| "Is the planner optimal?" | No — it's a greedy heuristic with warm-start. Contract §5.4 doesn't require optimality, only improvement on net revenue. |
| "Why is spoilage tied?" | FEFO already dispatches expiring stock first. Planner's gain is routing high-value produce to better margins, not waste reduction. |
| "How do you handle real demand uncertainty?" | Contract §2.2 has configurable demand response (OFF by default). A9 catalogue will inform elasticity parameters. |
| "Can this scale?" | Single-day horizon, kg-proportional costs — O(batches × destinations) per scenario. 120 scenarios in <2s. Multi-day is v2. |
| "What about donation/processing?" | Out of scope for v1 (U4). Contract §7/§11 rejects them as unsupported destination types. |