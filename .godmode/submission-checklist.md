# Aurenza — Devfolio/Hackathon Submission Checklist

**Status Legend:** ✅ VERIFIED | 🟡 PARTIALLY VERIFIED | ❌ NOT VERIFIED | 🔴 BLOCKED | ⏭️ N/A

---

## 1. Repository Requirements

| Requirement | Source | Status | Evidence | Notes |
|-------------|--------|--------|----------|-------|
| Public GitHub repo | Devfolio standard | ✅ | github.com/the-nidhi-bhat/Aurenza | Pushed `wip/dashboard-excellence-snapshot` |
| README with setup instructions | Devfolio standard | ✅ | `README.md` | Mermaid diagrams, quick start, CLI ref |
| No committed secrets | Security | ✅ | `git log --all --full-history -- .env` | Verified clean |
| License file | Devfolio standard | ❌ | — | **TODO: Add MIT LICENSE** |
| `.gitignore` appropriate | Devfolio standard | ✅ | `.gitignore` | Covers `output/`, `__pycache__/`, `.pytest_cache/` |
| Reproducible build | Devfolio standard | ✅ | `python -m pytest -q` → 50 passed | Zero runtime deps, stdlib only |

---

## 2. Documentation Requirements

| Requirement | Source | Status | Evidence | Notes |
|-------------|--------|--------|----------|-------|
| Problem statement | Devfolio judging | ✅ | README § "TL;DR" | ₹92,651 cr loss, intuition-based routing |
| Solution overview | Devfolio judging | ✅ | README § "Architecture Overview" | Null Theory First, FEFO → Planner |
| Architecture diagram | Devfolio judging | ✅ | README Mermaid diagrams | 5 diagrams: system, null theory, baseline vs planner, cost model, data flow |
| Technical approach | Devfolio judging | ✅ | README + `docs/CONTRACT.md` | Contract v1.0.0-draft.4, 14 feasibility codes |
| Demo instructions | Devfolio standard | ✅ | README § "Quick Start" | 4 commands, dashboard at localhost:8000 |
| API/Contract documentation | Project-specific | ✅ | `docs/CONTRACT.md` | 575 lines, v1.0.0-draft.4 |
| Assumptions & limitations | Project-specific | ✅ | `docs/ASSUMPTIONS.md` + README | A9 open, synthetic data, provisional disruptions |

---

## 3. Demo Requirements

| Requirement | Source | Status | Evidence | Notes |
|-------------|--------|--------|----------|-------|
| Working demo deployed | Devfolio standard | ✅ | https://aurenza-five.vercel.app/dashboard/ | Vercel auto-deploy on merge to main |
| Local run instructions | Devfolio standard | ✅ | README § "Quick Start" | `python dashboard/serve.py` |
| Demo video (2-3 min) | Devfolio standard | 🟡 | `DEMO_SCRIPT.md` created | **TODO: Record per script** |
| Screenshots (12 key views) | Devfolio standard | 🟡 | `SCREENSHOT_GUIDE.md` created | **TODO: Capture per guide** |
| Dashboard accessibility | Project quality | ✅ | `browser_check_editorial.py` 103/103 | WCAG AA, keyboard, screen-reader, reduced motion |
| Dashboard visual correctness | Project quality | ✅ | `prod_platform_smoke.py` 33/33 | Live contrast, geometry, CTA contrast verified |

---

## 4. Technical Verification

| Requirement | Source | Status | Evidence | Notes |
|-------------|--------|--------|----------|-------|
| Unit tests pass | Devfolio standard | ✅ | `pytest -q` → 50 passed | 41 engine + 9 dashboard |
| Contract tests pass | Project-specific | ✅ | `engine/tests/test_engine.py` | 41 tests, all §11 codes covered |
| Dashboard tests pass | Project-specific | ✅ | `dashboard/test_dashboard.py` | 9 tests incl. live server |
| Evaluation reproducibility | Project-specific | ✅ | `run_eval` → 120 scenarios | Deterministic: same seed = byte-identical |
| Non-vacuity verified | Project quality | ✅ | `probe_a11y_mutation.py`, `probe_guard_mutation.py` | Mutation tests catch real regressions |
| Cross-browser smoke | Project quality | ✅ | `prod_platform_smoke.py` 33/33 | Production Vercel deployment |

---

## 5. Hackathon-Specific (Devfolio)

| Requirement | Source | Status | Evidence | Notes |
|-------------|--------|--------|----------|-------|
| Hackathon track alignment | Devfolio | 🔴 BLOCKED | **NEED HACKATHON NAME** | User must authenticate Devfolio + tell me hackathon |
| Submission form fields | Devfolio | 🔴 BLOCKED | **NEED HACKATHON NAME** | Cannot access form without auth |
| Team registration | Devfolio | 🔴 BLOCKED | **NEED HACKATHON NAME** | |
| Track/category selection | Devfolio | 🔴 BLOCKED | **NEED HACKATHON NAME** | |
| Required tech stack | Devfolio | 🔴 BLOCKED | **NEED HACKATHON NAME** | |
| Mandatory integrations | Devfolio | 🔴 BLOCKED | **NEED HACKATHON NAME** | |

---

## 6. Judging Criteria Coverage

| Criterion | Typical Weight | Aurenza Evidence | Status |
|-----------|----------------|------------------|--------|
| **Problem Clarity** | High | ₹92,651 cr loss, NABCONS 2022 cited | ✅ |
| **Technical Innovation** | High | Null Theory First, contract-governed, reconciliation | ✅ |
| **Impact/Potential** | High | +24.2% median revenue, explainable, deployable | ✅ |
| **Demo Quality** | High | Live dashboard, 120 scenarios, 0 infeasible | ✅ |
| **Code Quality** | Medium | 50 tests, stdlib, deterministic, documented | ✅ |
| **Design/UX** | Medium | Dark theme, accessible, responsive, explainable tables | ✅ |
| **Completeness** | Medium | Engine + dashboard + eval + docs + deploy | ✅ |
| **Presentation** | Medium | README, demo script, pitch deck, screenshots guide | 🟡 (video pending) |

---

## 7. Submission Assets Checklist

### Required for Devfolio Submission Form
- [ ] **Project Title:** "Aurenza — Explainable Produce Allocation & Dispatch Planner"
- [ ] **Tagline:** "Null Theory First: Baseline → Optimizer → Honest Evaluation"
- [ ] **Description:** (from README TL;DR + Problem/Solution)
- [ ] **GitHub URL:** https://github.com/the-nidhi-bhat/Aurenza
- [ ] **Live Demo URL:** https://aurenza-five.vercel.app/dashboard/
- [ ] **Video URL:** (YouTube/Loom/Vimeo — **TODO: Record & upload**)
- [ ] **Screenshots:** 12 images per `SCREENSHOT_GUIDE.md` (**TODO: Capture**)
- [ ] **Team Members:** Nidhi Bhat, Arati, Iffa
- [ ] **Tech Stack:** Python, Vanilla JS, Vercel, GitHub Actions
- [ ] **Track/Category:** **NEED HACKATHON NAME**

### Required for Repository (Judges Review Code)
- [x] README with Mermaid diagrams
- [x] `docs/CONTRACT.md` (source of truth)
- [x] `docs/ASSUMPTIONS.md`
- [x] Engine code (`engine/`)
- [x] Dashboard code (`dashboard/`)
- [x] Demo fixtures (`demo/result.json`, `demo/evaluation.json`)
- [x] Test suite (`engine/tests/`, `dashboard/test_dashboard.py`)
- [x] CI/CD (GitHub Actions — verify `.github/workflows/` exists)
- [ ] LICENSE file (MIT) — **TODO**
- [ ] CONTRIBUTING.md — **TODO (optional)**

---

## 8. Pre-Submission Final Verification

Run these commands and confirm all pass:

```powershell
# 1. Full test suite
python -m pytest -q
# Expected: 50 passed

# 2. Regenerate demo output
python -m engine.scripts.run_plan --seed 1
# Expected: wrote demo\result.json

# 3. Regenerate evaluation
python -m engine.scripts.run_eval
# Expected: wrote output\evaluation.json (120 scenarios, 23 all-metric planner wins)

# 4. Dashboard loads
python dashboard/serve.py
# Open http://127.0.0.1:8000/dashboard/ — verify Overview + Evaluation tabs

# 5. Check production
# Open https://aurenza-five.vercel.app/dashboard/ — verify same data

# 6. Check GitHub
# Open https://github.com/the-nidhi-bhat/Aurenza — verify README renders, Actions green

# 7. Secrets scan
git log --all --full-history -- .env .env.* *.pem *.key id_rsa* 2>$null
# Expected: no results
```

---

## 9. Blockers Requiring User Action

| Blocker | Owner | Action Required |
|---------|-------|-----------------|
| **Devfolio authentication** | User | Sign in to Devfolio in browser → tell me hackathon name |
| **Image 1 description** | User | Which element was hard to read? (text/chart/table/button) |
| **Image 2 description** | User | Which element was hard to read? |
| **Image 5 UI/UX issue** | User | What's the problem? (layout/contrast/flow/missing info) |
| **Demo data (images 3, 4)** | User | Paste rows/values as text |
| **LICENSE file** | Me | Add MIT LICENSE |
| **Demo video recording** | User/Me | Record per `DEMO_SCRIPT.md`, upload to YouTube/Loom |
| **Screenshots capture** | User/Me | Capture 12 views per `SCREENSHOT_GUIDE.md` |

---

## 10. Sign-Off

| Role | Name | Status | Date |
|------|------|--------|------|
| Engine Lead | Nidhi Bhat | 🟡 Pending blockers | — |
| Dashboard Lead | Arati | 🟡 Pending blockers | — |
| Data Lead | Iffa | 🟡 Pending A9 | — |
| Submission Coordinator | Nidhi Bhat | 🟡 Pending Devfolio auth | — |

---

**Last Updated:** 2026-10-18  
**Next Review:** After Devfolio auth + user provides image descriptions + demo data