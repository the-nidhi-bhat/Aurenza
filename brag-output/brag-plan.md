# Brag Plan: Aurenza

## What is this app?
Aurenza is an explainable produce allocation engine that proves every dispatch decision — comparing a credible FEFO baseline against a revenue-optimizing planner across 120 synthetic scenarios, with full accounting reconciliation and zero runtime dependencies.

## The angle
Null Theory First discipline applied to perishable logistics. The baseline (FEFO) is the domain standard — the optimizer must *earn* its keep by beating it on net revenue. No strawmen. No black boxes. Every dispatch has a `reason` field. The result: +24.2% median revenue improvement, 0 infeasible runs.

## Hook (first 2-3 seconds)
**Text on dark:** "India loses ₹92,651 crore/year to post-harvest waste."
**Cut to:** Dashboard KPI cards — Baseline ₹13,387 → Planner ₹15,818 **(+18.2%)**
**Audio:** Low cinematic swell, single decisive card-reveal sound.

## Key moments (the middle)
1. **Dispatch table with reasons** — Planner rows show "greedy gain 37.36/kg", Baseline shows "FEFO: expiring day 3.5 → highest price". The `reason` column *is* the explainability.
2. **Batch inventory split** — Planner holds 200kg onions as fresh inventory (worth more later), Baseline ships all at negative contribution (-₹233, -₹1,397). Visual proof of the optimizer's restraint.
3. **Reconciliation check_ok: true** — Accounting identity holds within ₹0.01. `net_revenue = sum_contributions - spoilage_cost`. Trust, verified.
4. **Evaluation scale** — 120 scenarios, 115/120 net revenue wins, 23/120 all-metric wins, 0 infeasible. The "Synthetic data" badge stays visible throughout.

## Outro / punchline
**Text:** "Null Theory First. Baseline first. Optimizer second. Honest evaluation always."
**Logo mark** (the SVG path) draws in with accent green.
**Audio:** Music fades, clean logo hit SFX rings out.

## User flow worth showing
Dashboard loads → Overview tab: KPI cards animate in → Planner dispatch table rows appear with reasons → Switch to Evaluation tab → Scenario selector dropdown → 120-scenario win counts → Reconciliation check_ok true.

## Tone
- Preset: **polished**
- Creative direction: **quiet premium product film for a technical tool that earns trust**
- Interpretation: Restrained pacing. Long holds on real UI. No flashy transitions. Green accent as the only chromatic voice. Text reads fully before moving. Audio is a warm bed with sparse professional SFX — card reveals, logo hit.

## Format: landscape — 1920x1080
## Duration: 20 seconds

## Visual identity (from the project)
- Background: `#080b11`
- Accent: `#2fbf7f` (primary green)
- Accent bright: `#5ee0a8`
- Text: `#e9eef6`
- Muted: `#9bacc2`
- Warning: `#e2a53a`
- Danger: `#e5717a`
- Display font: System UI stack (`ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`)
- Body font: Same
- Strongest visual element: The KPI compare cards (baseline vs planner side-by-side with arrow delta), and the brand SVG mark (path animation)

## Share copy (draft)
Aurenza: an explainable produce allocation engine. FEFO baseline → greedy planner. +24.2% median revenue. 120 scenarios. 0 infeasible runs. Every dispatch has a reason. github.com/the-nidhi-bhat/Aurenza

## Audio direction
- Role: **warm bed** — cinematic but restrained, supports the technical credibility
- Music: **candidate track** — low ambient bed, ~80-90 BPM, minor key, subtle swell at hook and outro
- Music treatment: Fade in under hook (0.5s), hold steady through key moments, duck slightly under text-heavy scenes, fade out over final 2s with logo hit
- Music cue guidance: **detect at composition via analyze_music_cues.py** — target strong cues for hook reveal (beat 1), dispatch table reveal (beat 3), reconciliation check (beat 5), logo landing (final beat)
- Audio-reactive treatment: **subtle** — use music RMS to make the accent green glow and card presence breathe (0.05-0.1 intensity), not waveform bars
- SFX posture: **sparse** — card reveal pop (0.1s) for each KPI card, table row, and final logo; key-tick for typing animation on hook line; professional restraint
- Audio-coupled moments:
  - Hook line types out character-by-character with subtle key ticks
  - KPI cards arrive one by one (3 cards, beat-aligned)
  - Dispatch table rows slide in sequentially with card sounds
  - Reconciliation checkmark draws in with soft confirmation chime
  - Brand SVG path draws with logo hit SFX
- Restraint rule: Music never competes with text readability. SFX only on deliberate reveals, never on passive holds.

## Storyboard

### Scene 1 — Hook — 3.5s
**Visual:** Dark screen (`#080b11`). Hook line types out: "India loses ₹92,651 crore/year to post-harvest waste." Character-by-character with key-tick SFX. Hold 1.5s settled.
**Sequential/interaction:** Yes — text types out with keyboard sounds.
**Audio intent:** Gravity. The problem lands before the solution.
**Audio-coupled idea:** Typing animation with subtle key-tick SFX per character.
**Music:** Fade in warm bed (0.5s attack).
**Transition mood:** Clean crossfade → Scene 2

### Scene 2 — Reveal: Dashboard KPI Cards — 4s
**Visual:** Dashboard loads. Three KPI cards animate in sequentially (beat-aligned):
1. Net Revenue: Baseline ₹13,387 → Planner ₹15,818 **(+18.2%)** — green delta chip
2. Spoilage: Both 0 kg — tie chip
3. Fulfillment: Baseline 12.93% → Planner 9.48% — trade-off noted
Each card slams in fast (0.3s), holds. Arrow between baseline/planner values.
**Sequential/interaction:** Yes — 3 cards arrive one by one on consecutive beats, card-reveal SFX each.
**Audio intent:** Confidence. The numbers speak.
**Audio-coupled idea:** Beat-aligned card reveals (3 cards, every other beat at ~85 BPM = ~0.7s spacing).
**Music:** Steady bed.
**Transition mood:** Clean crossfade → Scene 3

### Scene 3 — Dispatch Tables: Reasons — 4s
**Visual:** Planner dispatch table — 2 rows visible. Highlight `reason` column: "greedy gain 37.36/kg", "greedy gain 13.71/kg". Rows slide in from left sequentially.
Cut to Baseline table — "FEFO: expiring day 3.5 → highest price", ships onions at loss.
**Sequential/interaction:** Yes — rows slide in one by one (2 planner, then 2 baseline), card SFX.
**Audio intent:** Proof. The `reason` column *is* the product.
**Audio-coupled idea:** Beat-aligned row reveals (4 rows total).
**Music:** Steady bed.
**Transition mood:** Hard cut → Scene 4

### Scene 4 — Batch Inventory: Restraint — 3.5s
**Visual:** Batch inventory table. Planner column: B001 onions → 200kg fresh_inventory, 0 spoiled. Baseline column: B001 → 0 fresh, 0 spoiled (all shipped at loss). Highlight the difference with a subtle green glow on the planner's fresh_inventory cell.
**Sequential/interaction:** Yes — cells populate sequentially, planner's fresh_inventory glows on arrival.
**Audio intent:** Insight. The optimizer *doesn't* ship — that's the win.
**Audio-coupled idea:** Soft glow pulse synced to music RMS on planner's fresh_inventory cell.
**Music:** Steady bed, slight swell.
**Transition mood:** Soft crossfade → Scene 5

### Scene 5 — Reconciliation: Trust — 2.5s
**Visual:** Reconciliation panel. `sum_dispatch_contributions: 15818.00` → `spoilage_cost: 0.00` → `net_revenue: 15818.00` → **check_ok: true** (green checkmark draws in).
**Sequential/interaction:** Yes — lines populate top to bottom, checkmark animates in with confirmation chime.
**Audio intent:** Verification. Math holds.
**Audio-coupled idea:** Checkmark draw with soft confirmation SFX.
**Music:** Begin fade out (1.5s).
**Transition mood:** Slow crossfade → Scene 6

### Scene 6 — Evaluation Scale — 2.5s
**Visual:** Evaluation tab. Win count cards: "Net Revenue: 115/120", "Spoilage: 118 ties", "All-metric: 23/120", "Infeasible: 0". Cards pop in one by one. "Synthetic data" amber badge visible in app bar throughout.
**Sequential/interaction:** Yes — 4 cards arrive sequentially, beat-aligned.
**Audio intent:** Scale. This isn't a demo — it's an evaluation.
**Audio-coupled idea:** Beat-aligned card pops.
**Music:** Fading out.
**Transition mood:** Slow crossfade → Scene 7

### Scene 7 — Outro — 2s
**Visual:** Dark screen. Brand SVG mark draws in (path animation, 1.2s). "Aurenza" name fades in below. Tagline: "Produce allocation & dispatch". URL: github.com/the-nidhi-bhat/Aurenza
**Sequential/interaction:** Yes — SVG path draws, then text fades.
**Audio intent:** Closure. The mark remains.
**Audio-coupled idea:** Logo hit SFX on path completion, rings over music fade.
**Music:** Fade out complete. Logo hit rings.
**Transition mood:** End.

---

**Music mood for this video:** cinematic / warm ambient bed, ~85 BPM
**Audio summary:** Warm cinematic bed enters under hook, holds steady through KPI/dispatch/inventory/reconciliation scenes with beat-aligned reveals and subtle RMS-reactive glow on accent elements, fades under evaluation cards, clean logo hit SFX rings over final fade.