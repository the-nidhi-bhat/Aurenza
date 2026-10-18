# Hyperframes Composition Brief: Aurenza

## Objective
Create a short launch-style brag video for Aurenza — an explainable produce allocation engine.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `C:\Users\theni\OneDrive\Desktop\projects main\Aurenza`
- Primary files read: `dashboard/index.html`, `dashboard/styles.css`, `README.md`, `demo/result.json`
- Product name: Aurenza
- Tagline / strongest claim: "Null Theory First. Baseline first. Optimizer second. Honest evaluation always."
- Key UI or visual moment to recreate: Dashboard KPI compare cards (baseline vs planner side-by-side), dispatch tables with `reason` column, batch inventory split, reconciliation check_ok
- Copy that must appear verbatim:
  - "India loses ₹92,651 crore/year to post-harvest waste."
  - "Null Theory First. Baseline first. Optimizer second. Honest evaluation always."
  - "Aurenza — Produce allocation & dispatch"
  - "github.com/the-nidhi-bhat/Aurenza"

## Creative Direction
- Tone preset: polished
- Creative direction: quiet premium product film for a technical tool that earns trust
- Interpretation: Restrained pacing. Long holds on real UI. No flashy transitions. Green accent as the only chromatic voice. Text reads fully before moving. Audio is a warm bed with sparse professional SFX.
- Angle: Null Theory First discipline applied to perishable logistics. The baseline (FEFO) is the domain standard — the optimizer must earn its keep by beating it on net revenue. No strawmen. No black boxes. Every dispatch has a `reason` field. Result: +24.2% median revenue improvement, 0 infeasible runs.
- Hook: "India loses ₹92,651 crore/year to post-harvest waste." → Dashboard KPI cards animate in.
- Outro / punchline: "Null Theory First. Baseline first. Optimizer second. Honest evaluation always." + brand SVG mark draws in.
- Avoid:
  - Generic SaaS language ("streamline your workflow")
  - Abstract filler visuals (color washes, particle systems)
  - Unrelated visual redesign (stick to the dashboard's actual dark theme + green accent)

## Visual Identity
- Background: `#080b11`
- Text: `#e9eef6`
- Accent: `#2fbf7f` (primary green)
- Accent bright: `#5ee0a8`
- Muted: `#9bacc2`
- Warning: `#e2a53a`
- Danger: `#e5717a`
- Display font: System UI stack (`ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`)
- Body font: Same
- Visual references from the project:
  - Brand SVG mark (path animation on the two paths + circle)
  - KPI compare cards (baseline/planner side-by-side with arrow delta)
  - Dispatch tables with `reason` column
  - Batch inventory table (fresh_inventory vs spoiled split)
  - Reconciliation panel (check_ok: true with green checkmark)
  - Evaluation win count cards
  - "Synthetic data" amber badge in app bar

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook — 3.5s — Problem statement types out character-by-character
2. Reveal: Dashboard KPI Cards — 4s — 3 cards arrive sequentially (Net Revenue +18.2%, Spoilage tie, Fulfillment trade-off)
3. Dispatch Tables: Reasons — 4s — Planner rows with "greedy gain X/kg", Baseline rows with "FEFO..." reasons
4. Batch Inventory: Restraint — 3.5s — Planner holds 200kg onions fresh, Baseline ships all at loss
5. Reconciliation: Trust — 2.5s — Accounting identity lines populate, check_ok: true checkmark draws
6. Evaluation Scale — 2.5s — 120-scenario win counts pop in, Synthetic data badge visible
7. Outro — 2s — Brand SVG path draws, name + tagline + GitHub URL

## Audio
- Audio role: warm bed — cinematic but restrained, supports technical credibility
- Audio arc: Fade in under hook → steady through middle scenes with beat-aligned reveals → fade under evaluation → logo hit rings over final fade
- Music: candidate track — low ambient bed, ~85 BPM, minor key, subtle swell
- Music treatment: Fade in 0.5s, hold steady, duck slightly under text-heavy scenes, fade out over final 2s
- Music cue guidance: detect at composition via analyze_music_cues.py — target strong cues for hook reveal, dispatch table reveal, reconciliation check, logo landing
- Audio-reactive treatment: subtle — use music RMS to make accent green glow and card presence breathe (0.05-0.1 intensity), not waveform bars
- Audio-coupled moments:
  - Scene 1: Hook line types out character-by-character with subtle key-tick SFX
  - Scene 2: 3 KPI cards arrive one by one on consecutive beats (beat-aligned)
  - Scene 3: 4 dispatch table rows slide in sequentially (beat-aligned)
  - Scene 4: Batch inventory cells populate, planner's fresh_inventory glows on RMS
  - Scene 5: Reconciliation lines populate top-to-bottom, checkmark draws with confirmation chime
  - Scene 6: 4 evaluation cards pop in sequentially (beat-aligned)
  - Scene 7: Brand SVG path draws (1.2s), logo hit SFX rings over music fade
- SFX selection guidance: Sparse professional SFX — card reveal pop (0.1s) for each card/row reveal, key-tick for typing, soft confirmation chime for checkmark, logo hit for brand mark. Use lower high-frequency-risk sounds for repeated moments. Match SFX to motion exactly.
- SFX analysis guidance: Use `skills/brag/assets/sfx/sfx-analysis.md` for selection guidance. Prefer low high-frequency-risk files for repeated or polished moments.
- Exact SFX choice: Hyperframes should choose filenames, timestamps, density, and volume based on the implemented animation.
- Audio files: Copy chosen music and SFX into `brag-output/composition/assets/`

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core` (composition contract + `data-*` timing), `hyperframes-animation` (motion), `hyperframes-creative` (design spec, beats, audio-reactive), `hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli` (lint/check/render). /brag is its own workflow: do not enter the `hyperframes` entry-point intent interview and do not route into its generic promo / launch-video workflow. Prefer native Hyperframes conventions over anything in `/brag`.

Requirements:
- Show at least one real UI, copy, or visual element from the source project.
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds.
- Include the planned music/SFX layer.
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after the visual animation exists.
- Treat music cue metadata as optional timing hints. Hyperframes decides exact animation timing and should ignore cues that hurt readability, scene pacing, or the product story.
- Major reveals may move toward nearby strong cues within about 0.15s. Smaller entrances may align to nearby beat points within about 0.10s. Use only 1-3 strong cue locks in a 15-25s video unless the edit clearly benefits from more.
- Use SFX to support motion and interaction: card sounds for card-like reveals, short announcement cues for major payoffs, key/click sounds for text or user actions, and restraint when the edit is already busy.
- Honor planned music treatment such as fade-outs, ducking, beat-aligned reveals, or letting a final SFX ring over the music, using the best Hyperframes-supported implementation.
- When music is present and the treatment is not `none`, consider Hyperframes audio-reactive workflow: extract audio data and use RMS/frequency bands for subtle, brand-specific motion. Good targets are glow, depth, background warmth, card presence, title emphasis, or other existing visual elements. Avoid waveform/equalizer visuals, musical-note graphics, generic particle systems, strobing, or heavy pulsing.
- Use local assets for audio and any required runtime/media dependencies when possible.
- Run `hyperframes check` before render — it is brag's single gate.

## Self-review checklist
- [ ] `brag-output/composition-brief.md` exists.
- [ ] The brief clearly identifies the exact product moments to show.
- [ ] The composition uses the current Hyperframes workflow, not a hardcoded `/brag` template.
- [ ] Music file is copied into `brag-output/composition/assets/music/`.
- [ ] At least one visual element subtly reacts to the music (audio-reactive treatment present), or extraction failure is documented.
- [ ] At least 1 major tween is beat-locked to a strong cue (a `strongCue`, or the highest-`strength` beat from `hyperframes beats`) within ±0.15s, marked `// beat-locked` (or natural timing was chosen for readability).
- [ ] Sequential events (cards, stats, list items) snap to consecutive `beats[]` timestamps (±0.10s), marked `// beat-grid` (or natural timing was chosen for readability).
- [ ] The composition shows at least one real UI, copy, or visual element from the project.
- [ ] Total duration is 15-25 seconds.
- [ ] Hyperframes check passes, or any blocker is documented for the user.