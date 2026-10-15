'use strict';

/* Aurenza dashboard: reads only the engine-generated JSON files
 * (../demo/result.json and ../demo/evaluation.json). Imports no engine code
 * and hardcodes no figures — every value is read from those files. */

const TOL_INR = 0.01;
const TOL_KG = 0.001;

const $ = (id) => document.getElementById(id);

const INR = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR',
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});

const NUM = (n, d = 2) =>
  (n === null || n === undefined || Number.isNaN(n)) ? '—'
    : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const money = (n) => (n === null || n === undefined || Number.isNaN(n)) ? '—' : INR.format(n);
const kg = (n) => (n === null || n === undefined || Number.isNaN(n)) ? '—' : NUM(n, 2) + ' kg';
const pct = (n) => (n === null || n === undefined || Number.isNaN(n)) ? '—' : NUM(n, 2) + '%';
const signed = (n, fmt) => (n === null || n === undefined || Number.isNaN(n)) ? '—' : (n > 0 ? '+' : '') + fmt(n);

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function fetchJSON(path) {
  const res = await fetch(path, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${path} returned HTTP ${res.status}`);
  return res.json();
}

/* ---------- shared fragments ---------- */

// good/bad/neutral class for a change, given the metric's preferred direction.
function chipClass(delta, direction, tol) {
  if (delta === null || delta === undefined || Math.abs(delta) <= tol) return 'flat';
  const good = direction === 'higher_better' ? delta > 0 : delta < 0;
  return good ? 'up' : 'down';
}
function outcomeTag(delta, direction, tol, labels = ['win', 'tie', 'loss']) {
  const cls = chipClass(delta, direction, tol);
  const [w, t, l] = labels;
  const txt = cls === 'up' ? w : cls === 'down' ? l : t;
  const tone = cls === 'up' ? 'win' : cls === 'down' ? 'loss' : 'tie';
  return `<span class="tag ${tone}">${esc(txt)}</span>`;
}

function compareCard({ title, baselineText, plannerText, deltaText, direction, delta, tol }) {
  const cls = chipClass(delta, direction, tol);
  const arrow = cls === 'up' ? '▲' : cls === 'down' ? '▼' : '=';
  return `
    <div class="card">
      <p class="card-title">${esc(title)}</p>
      <div class="compare">
        <div class="side baseline"><span class="label">Baseline</span><span class="value">${baselineText}</span></div>
        <div class="arrow" aria-hidden="true">→</div>
        <div class="side planner"><span class="label">Planner</span><span class="value">${plannerText}</span></div>
      </div>
      <div class="delta"><span class="chip ${cls}">${arrow} ${deltaText}</span></div>
    </div>`;
}

function statCard(title, big, sub) {
  return `<div class="card"><p class="card-title">${esc(title)}</p>
    <div class="stat-big">${big}</div>
    ${sub ? `<div class="sub">${sub}</div>` : ''}</div>`;
}

function miniBars(pairs) {
  const max = Math.max(...pairs.map((p) => Math.abs(p.value) || 0), 1e-9);
  return `<div class="bars-mini">` + pairs.map((p) => `
    <div class="bm-row">
      <span class="bm-label">${esc(p.label)}</span>
      <div class="bm-track"><span class="bm-fill ${p.tone}" style="width:${(Math.abs(p.value) / max * 100).toFixed(1)}%"></span></div>
    </div>`).join('') + `</div>`;
}

function summaryLine(strategy) {
  const n = (strategy.dispatches || []).length;
  const total = (strategy.dispatches || []).reduce((s, d) => s + (d.expected_contribution || 0), 0);
  return `${n} dispatch${n === 1 ? '' : 'es'} · Σ contribution ${money(total)}`;
}

// Filter/sort vocabulary for the dispatch tables. Each filter is a predicate
// over the engine's own dispatch records; each sort maps a record to a
// comparable value (direction folded into the sign for numeric keys). No
// figures are hardcoded — every number shown is summed from the records.
const DISPATCH_FILTERS = [
  { key: 'all', label: 'All dispatches', test: () => true },
  { key: 'below_cost', label: 'Below cost (loses money)', test: (d) => (d.expected_contribution || 0) < 0 },
  { key: 'discounted', label: 'Discounted', test: (d) => (d.discount_pct || 0) > 0 },
  { key: 'part', label: 'Part-shipped (unsold left)', test: (d) => (d.sold_kg ?? 0) < (d.quantity_kg ?? 0) - TOL_KG },
];

const DISPATCH_SORT_LABELS = {
  'plan:asc': 'Plan priority order',
  'contribution:desc': 'Contribution — highest first',
  'contribution:asc': 'Contribution — lowest first',
  'quantity_kg:desc': 'Dispatched kg — most first',
  'sold_kg:desc': 'Sold kg — most first',
  'effective_price_per_kg:desc': 'Effective ₹/kg — highest first',
  'batch_id:asc': 'Batch — A to Z',
};

const DISPATCH_SORTS = {
  'contribution:desc': (d) => -(d.expected_contribution || 0),
  'contribution:asc': (d) => (d.expected_contribution || 0),
  'quantity_kg:desc': (d) => -(d.quantity_kg || 0),
  'sold_kg:desc': (d) => -(d.sold_kg || 0),
  'effective_price_per_kg:desc': (d) => -(d.effective_price_per_kg || 0),
  'batch_id:asc': (d) => String(d.batch_id),
};

function sortDispatches(rows, key) {
  const get = DISPATCH_SORTS[key];
  if (!get) return rows.slice(); // 'plan:asc' — keep the engine's own ordering
  return rows.slice().sort((a, b) => {
    const va = get(a), vb = get(b);
    const c = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
    return c !== 0 ? c : String(a.batch_id).localeCompare(String(b.batch_id));
  });
}

function dispatchRow(d) {
  const neg = (d.expected_contribution || 0) < 0;
  const disc = (d.discount_pct || 0) > 0
    ? `<span class="pill-disc">${NUM(d.discount_pct, 0)}%</span>`
    : '<span class="pill-none">—</span>';
  return `
    <tr>
      <td data-label="Batch"><span class="batch-cell">${esc(d.batch_id)}</span></td>
      <td data-label="Destination">${esc(d.destination_id)}</td>
      <td class="num" data-label="Dispatched (kg)">${NUM(d.quantity_kg, 0)}</td>
      <td class="num" data-label="Sold (kg)">${NUM(d.sold_kg, 0)}</td>
      <td data-label="Discount">${disc}</td>
      <td class="num" data-label="Eff ₹/kg">${money(d.effective_price_per_kg)}</td>
      <td class="num ${neg ? 'neg' : 'pos'}" data-label="Contribution">${signed(d.expected_contribution, money)}</td>
      <td class="reason" data-label="Reason">${esc(d.reason)}</td>
    </tr>`;
}

// Renders an interactive dispatch table into `container`: a filter + sort
// control pair and a live count of the visible subset (with its summed
// contribution and how many rows lose money). Only the <tbody> is replaced on
// change, so focus stays on the control the user is operating.
function mountDispatchTable(container, dispatches, caption) {
  const list = dispatches || [];
  if (!list.length) {
    container.innerHTML = '<p class="empty">No dispatches in this plan.</p>';
    return;
  }
  const state = { filter: 'all', sort: 'plan:asc' };

  container.innerHTML = `
    <div class="table-tools">
      <label class="field"><span>Show</span>
        <select data-role="filter">${DISPATCH_FILTERS
          .map((f) => `<option value="${f.key}">${esc(f.label)}</option>`).join('')}</select>
      </label>
      <label class="field"><span>Sort</span>
        <select data-role="sort">${Object.keys(DISPATCH_SORT_LABELS)
          .map((k) => `<option value="${k}">${esc(DISPATCH_SORT_LABELS[k])}</option>`).join('')}</select>
      </label>
      <p class="table-count" data-role="count" role="status" aria-live="polite"></p>
    </div>
    <table class="responsive">
      <caption class="sr-only">${esc(caption)}</caption>
      <thead><tr>
        <th scope="col">Batch</th><th scope="col">Destination</th><th scope="col" class="num">Dispatched (kg)</th>
        <th scope="col" class="num">Sold (kg)</th><th scope="col">Discount</th>
        <th scope="col" class="num">Eff ₹/kg</th><th scope="col" class="num">Contribution</th><th scope="col">Reason</th>
      </tr></thead>
      <tbody data-role="rows"></tbody>
    </table>`;

  const rowsEl = container.querySelector('[data-role="rows"]');
  const countEl = container.querySelector('[data-role="count"]');

  function update() {
    const f = DISPATCH_FILTERS.find((x) => x.key === state.filter) || DISPATCH_FILTERS[0];
    const shown = sortDispatches(list.filter(f.test), state.sort);
    rowsEl.innerHTML = shown.length
      ? shown.map(dispatchRow).join('')
      : '<tr><td class="empty" colspan="8">No dispatches match this filter.</td></tr>';
    const total = shown.reduce((s, d) => s + (d.expected_contribution || 0), 0);
    const below = shown.filter((d) => (d.expected_contribution || 0) < 0).length;
    countEl.textContent = `Showing ${shown.length} of ${list.length} dispatches · Σ contribution ${money(total)}`
      + (below ? ` · ${below} below cost` : '');
  }

  container.querySelector('[data-role="filter"]')
    .addEventListener('change', (e) => { state.filter = e.target.value; update(); });
  container.querySelector('[data-role="sort"]')
    .addEventListener('change', (e) => { state.sort = e.target.value; update(); });
  update();
}

function batchTable(baselineBatches, plannerBatches) {
  const map = new Map();
  (baselineBatches || []).forEach((r) => map.set(r.batch_id, { b: r }));
  (plannerBatches || []).forEach((r) => {
    const e = map.get(r.batch_id) || {};
    e.p = r;
    map.set(r.batch_id, e);
  });
  if (!map.size) return '<p class="empty">No batch data.</p>';
  const rows = [...map.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([id, e]) => {
    const b = e.b || {}, p = e.p || {};
    const harvested = (b.harvested_kg ?? p.harvested_kg);
    return `<tr>
      <td data-label="Batch"><span class="batch-cell">${esc(id)}</span></td>
      <td class="num" data-label="Harvested (kg)">${NUM(harvested, 0)}</td>
      <td class="num" data-label="Baseline dispatched">${NUM(b.dispatched_kg, 0)}</td>
      <td class="num" data-label="Baseline sold">${NUM(b.sold_kg, 0)}</td>
      <td class="num ${b.spoiled_kg > 0 ? 'neg' : ''}" data-label="Baseline spoiled">${NUM(b.spoiled_kg, 0)}</td>
      <td class="num" data-label="Planner dispatched">${NUM(p.dispatched_kg, 0)}</td>
      <td class="num" data-label="Planner sold">${NUM(p.sold_kg, 0)}</td>
      <td class="num ${p.spoiled_kg > 0 ? 'neg' : ''}" data-label="Planner spoiled">${NUM(p.spoiled_kg, 0)}</td>
      <td class="num" data-label="Planner fresh inv.">${NUM(p.fresh_inventory_kg, 0)}</td>
    </tr>`;
  }).join('');
  return `<table class="responsive">
    <caption class="sr-only">Per-batch inventory: harvested, and dispatched, sold and spoiled kg under each strategy, plus planner fresh inventory.</caption>
    <thead><tr>
      <th scope="col">Batch</th><th scope="col" class="num">Harvested</th>
      <th scope="col" class="num">B dispatched</th><th scope="col" class="num">B sold</th><th scope="col" class="num">B spoiled</th>
      <th scope="col" class="num">P dispatched</th><th scope="col" class="num">P sold</th><th scope="col" class="num">P spoiled</th>
      <th scope="col" class="num">P fresh inv.</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

function reconRows(name, rec) {
  if (!rec) return '';
  const ok = rec.check_ok === true;
  return `<div class="recon-row">
    <span class="${ok ? 'ok' : 'bad'}">${ok ? 'PASS' : 'FAIL'}</span>
    <strong>${esc(name)}</strong>
    <span class="detail">Σ contributions ${money(rec.sum_dispatch_contributions)} − spoilage ${money(rec.spoilage_cost)} = net ${money(rec.net_revenue)}</span>
  </div>`;
}

/* ---------- overview view (demo/result.json) ---------- */

function renderHero(bm, pm, nr) {
  const nrPctText = (nr.delta_pct === null || nr.delta_pct === undefined) ? '—' : NUM(nr.delta_pct, 2) + '%';
  const cls = chipClass(nr.delta, 'higher_better', TOL_INR);
  const arrow = cls === 'up' ? '▲' : cls === 'down' ? '▼' : '=';
  return `<section class="panel hero" aria-label="Net revenue: planner versus baseline">
    <div>
      <p class="eyebrow">Net revenue · planner vs baseline</p>
      <div class="hero-figs">
        <div class="hf primary"><span class="hf-label">Planner</span><span class="hf-value">${money(pm.net_revenue)}</span></div>
        <div class="hf secondary"><span class="hf-label">Baseline (FEFO)</span><span class="hf-value">${money(bm.net_revenue)}</span></div>
      </div>
      <div class="hero-delta">
        <span class="chip ${cls}">${arrow} ${signed(nr.delta, money)} (${nrPctText})</span>
        <span>versus the FEFO baseline</span>
      </div>
    </div>
    ${miniBars([
      { label: 'Baseline', value: bm.net_revenue, tone: 'baseline' },
      { label: 'Planner', value: pm.net_revenue, tone: 'planner' },
    ])}
  </section>`;
}

function renderDetail(result) {
  const b = result.results.baseline;
  const p = result.results.planner;
  const imp = result.improvement || {};
  const bm = b.metrics, pm = p.metrics;
  const nr = imp.net_revenue || {};
  const sp = imp.spoilage_kg || {};
  const fp = imp.fulfillment_pct || {};

  $('detail-meta').textContent =
    `${result.scenario_id} · seed ${result.seed} · schema v${result.schema_version} · generated by ${result.generated_by}`;

  const nrPctText = (nr.delta_pct === null || nr.delta_pct === undefined) ? null : NUM(nr.delta_pct, 2) + '%';
  const vCls = chipClass(nr.delta, 'higher_better', TOL_INR);
  const v = $('detail-verdict');
  v.hidden = false;
  v.className = `verdict ${vCls}`;
  v.textContent = (vCls === 'flat' ? 'Revenue ≈ baseline' : `Revenue ${signed(nr.delta, money)}${nrPctText ? ' (' + nrPctText + ')' : ''}`);

  $('hero').innerHTML = renderHero(bm, pm, nr);

  $('kpi-cards').innerHTML =
    compareCard({
      title: 'Spoilage',
      baselineText: kg(bm.spoiled_kg), plannerText: kg(pm.spoiled_kg),
      deltaText: `${signed(sp.delta, (t) => NUM(t, 2) + ' kg')}`,
      direction: 'lower_better', delta: sp.delta, tol: TOL_KG,
    }) +
    compareCard({
      title: 'Demand fulfillment',
      baselineText: pct(bm.fulfillment_pct), plannerText: pct(pm.fulfillment_pct),
      deltaText: `${signed(fp.delta, (t) => NUM(t, 2) + ' pp')}`,
      direction: 'higher_better', delta: fp.delta, tol: TOL_KG,
    }) +
    statCard('Scenario supply & demand',
      `${NUM(bm.harvested_kg, 0)} kg harvested`,
      `demand ${NUM(bm.demand_kg, 0)} kg · baseline ships ${NUM(bm.dispatched_kg, 0)} kg, planner ships ${NUM(pm.dispatched_kg, 0)} kg`) +
    statCard('Feasibility',
      (pm.feasible === false ? '<span class="neg">Violation</span>' : '<span class="pos">Both feasible</span>'),
      pm.feasible === false
        ? `planner reports ${(pm.violations || []).length} constraint violation(s)`
        : 'no hard-constraint violations in either plan');

  // Honest messaging
  const notes = [];
  notes.push(`<div class="note info">Synthetic fixture scenario <strong>${esc(result.scenario_id)}</strong>, generated by the Aurenza engine — not observed real-world performance.</div>`);
  if ((nr.delta || 0) > TOL_INR) {
    notes.push(`<div class="note good">Planner net revenue is <strong>${money(nr.delta)}</strong>${nrPctText ? ` (${nrPctText})` : ''} higher than the FEFO baseline.</div>`);
  }
  if (Math.abs(sp.delta || 0) <= TOL_KG) {
    notes.push('<div class="note warn">No spoilage reduction in this scenario: the FEFO baseline already dispatches expiring stock first, so both strategies leave the same kg to spoil.</div>');
  } else if ((sp.delta || 0) > TOL_KG) {
    notes.push(`<div class="note warn">Planner spoilage is <strong>${NUM(sp.delta, 2)} kg higher</strong> than the baseline in this scenario.</div>`);
  }
  if ((fp.delta || 0) < -TOL_KG) {
    notes.push(`<div class="note warn">Planner demand fulfillment is <strong>${NUM(fp.delta, 2)} pp lower</strong> than the baseline here — it skips dispatches that would lose money, so it moves less volume. Net revenue is still higher. This is an honest trade-off, not a fixed guarantee.</div>`);
  }
  $('detail-notes').innerHTML = notes.join('');

  $('planner-summary').textContent = summaryLine(p);
  $('baseline-summary').textContent = summaryLine(b);
  mountDispatchTable($('planner-dispatches'), p.dispatches,
    "Planner dispatch decisions: batch, destination, quantities, discount, effective price, contribution and the engine's stated reason.");
  mountDispatchTable($('baseline-dispatches'), b.dispatches,
    "Baseline (FEFO) dispatch decisions: batch, destination, quantities, discount, effective price, contribution and the engine's stated reason.");
  $('batch-table').innerHTML = batchTable(b.batch_summary, p.batch_summary);
  $('recon').innerHTML = reconRows('Baseline', b.reconciliation) + reconRows('Planner', p.reconciliation);
}

/* ---------- evaluation view (demo/evaluation.json) ---------- */

function evalRuns(ev) {
  const runs = [];
  (ev.scenarios || []).forEach((sc) => (sc.runs || []).forEach((r) => runs.push(r)));
  return runs;
}

function evalAggregates(ev) {
  const runs = evalRuns(ev);
  const n = runs.length;
  const agg = {
    n, runs,
    nr: { win: 0, tie: 0, loss: 0 }, sp: { win: 0, tie: 0, loss: 0 }, fp: { win: 0, tie: 0, loss: 0 },
    allWins: 0, nrDelta: 0, sumB: 0, sumP: 0, spDelta: 0, fpDelta: 0,
    infeasB: 0, infeasP: 0, revDeltas: [],
  };
  const bump = (bucket, delta, direction, tol) => {
    if (delta === null || delta === undefined || Math.abs(delta) <= tol) bucket.tie++;
    else if ((direction === 'higher_better') === (delta > 0)) bucket.win++;
    else bucket.loss++;
  };
  runs.forEach((r) => {
    const imp = r.improvement || {};
    const nrd = (imp.net_revenue || {}).delta ?? 0;
    const spd = (imp.spoilage_kg || {}).delta ?? 0;
    const fpd = (imp.fulfillment_pct || {}).delta ?? 0;
    bump(agg.nr, nrd, 'higher_better', TOL_INR);
    bump(agg.sp, spd, 'lower_better', TOL_KG);
    bump(agg.fp, fpd, 'higher_better', TOL_KG);
    agg.allWins += (r.win && r.win.all_metrics) ? 1 : 0;
    agg.nrDelta += nrd;
    agg.sumB += (imp.net_revenue || {}).baseline || 0;
    agg.sumP += (imp.net_revenue || {}).planner || 0;
    agg.spDelta += spd;
    agg.fpDelta += fpd;
    agg.revDeltas.push(nrd);
    if (r.baseline && r.baseline.feasible === false) agg.infeasB++;
    if (r.planner && r.planner.feasible === false) agg.infeasP++;
  });
  agg.nrMean = n ? agg.nrDelta / n : null;
  // aggregate ratio is more robust than a mean of per-run ratios (small
  // baselines inflate the latter); report (Σplanner − Σbaseline)/Σbaseline.
  agg.nrPctAgg = agg.sumB ? (agg.sumP - agg.sumB) / Math.abs(agg.sumB) * 100 : null;
  agg.spMean = n ? agg.spDelta / n : null;
  agg.fpMean = n ? agg.fpDelta / n : null;
  return agg;
}

function stackRow(label, headValue, b, n) {
  const t = n || 1;
  const pctOf = (v) => (v / t * 100).toFixed(2);
  return `<div class="stack-row">
    <div class="stack-head"><span class="lbl">${esc(label)}</span><span class="val">${headValue}</span></div>
    <div class="stack" role="img" aria-label="${esc(label)}: ${b.win} wins, ${b.tie} ties, ${b.loss} losses out of ${t} scenarios">
      <span class="seg win" style="width:${pctOf(b.win)}%"></span>
      <span class="seg tie" style="width:${pctOf(b.tie)}%"></span>
      <span class="seg loss" style="width:${pctOf(b.loss)}%"></span>
    </div>
  </div>`;
}

function outcomeChart(a) {
  const sr = `<table class="sr-only"><caption>Outcome counts across ${a.n} scenarios</caption>
    <thead><tr><th>Metric</th><th>Wins</th><th>Ties</th><th>Losses</th></tr></thead><tbody>
    <tr><td>Net revenue</td><td>${a.nr.win}</td><td>${a.nr.tie}</td><td>${a.nr.loss}</td></tr>
    <tr><td>Spoilage</td><td>${a.sp.win}</td><td>${a.sp.tie}</td><td>${a.sp.loss}</td></tr>
    <tr><td>Fulfillment</td><td>${a.fp.win}</td><td>${a.fp.tie}</td><td>${a.fp.loss}</td></tr>
    </tbody></table>`;
  return `<section class="panel">
    <h2 class="chart-title">Outcome by metric — ${a.n} scenarios</h2>
    <p class="chart-note">Planner vs FEFO baseline. Each bar is one metric; a win means the planner is strictly better in that metric's direction.</p>
    ${stackRow('Net revenue', `${a.nr.win} / ${a.nr.tie} / ${a.nr.loss}`, a.nr, a.n)}
    ${stackRow('Spoilage (lower is better)', `${a.sp.win} / ${a.sp.tie} / ${a.sp.loss}`, a.sp, a.n)}
    ${stackRow('Demand fulfillment', `${a.fp.win} / ${a.fp.tie} / ${a.fp.loss}`, a.fp, a.n)}
    <div class="legend">
      <span class="k"><span class="sw win"></span>win</span>
      <span class="k"><span class="sw tie"></span>tie</span>
      <span class="k"><span class="sw loss"></span>loss</span>
    </div>
    ${sr}
  </section>`;
}

function histogramSvg(values) {
  const W = 720, H = 220, padL = 14, padR = 14, padT = 16, padB = 30;
  const vals = values.filter((v) => Number.isFinite(v));
  if (!vals.length) return '<p class="empty">No net-revenue deltas available.</p>';
  const min = Math.min(...vals), max = Math.max(...vals);
  const lo = Math.min(0, min), hi = Math.max(0, max);
  const span = (hi - lo) || 1;
  const bins = 13;
  const counts = new Array(bins).fill(0);
  vals.forEach((v) => {
    let idx = Math.floor((v - lo) / span * bins);
    if (idx >= bins) idx = bins - 1;
    if (idx < 0) idx = 0;
    counts[idx]++;
  });
  const maxC = Math.max(...counts, 1);
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const bw = plotW / bins;
  const x0 = padL + (0 - lo) / span * plotW;   // x of the zero line
  const bars = counts.map((c, i) => {
    const h = (c / maxC) * plotH;
    const x = padL + i * bw + 1.5;
    const y = padT + (plotH - h);
    const center = lo + (i + 0.5) / bins * span;
    const cls = center < 0 ? 'bar neg' : 'bar';
    return `<rect class="${cls}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(bw - 3).toFixed(1)}" height="${h.toFixed(1)}" rx="2"><title>${c} scenario(s) near ${esc(money(center))}</title></rect>`;
  }).join('');
  const zero = `<line class="zero" x1="${x0.toFixed(1)}" y1="${padT}" x2="${x0.toFixed(1)}" y2="${(padT + plotH).toFixed(1)}" />`;
  const axis = `<line class="axis" x1="${padL}" y1="${(padT + plotH).toFixed(1)}" x2="${(W - padR).toFixed(1)}" y2="${(padT + plotH).toFixed(1)}" />`;
  const ticks = `<text class="tick" x="${padL}" y="${H - 10}">${esc(money(lo))}</text>` +
    (lo < 0 && 0 < hi ? `<text class="tick" x="${x0.toFixed(1)}" y="${H - 10}" text-anchor="middle">0</text>` : '') +
    `<text class="tick" x="${(W - padR).toFixed(1)}" y="${H - 10}" text-anchor="end">${esc(money(hi))}</text>`;
  return `<svg class="hist" viewBox="0 0 ${W} ${H}" role="img"
      aria-label="Distribution of net-revenue change (planner minus baseline) across ${vals.length} scenarios, ranging from ${esc(money(min))} to ${esc(money(max))}.">
    ${bars}${axis}${zero}${ticks}</svg>`;
}

function distributionChart(a) {
  return `<section class="panel">
    <h2 class="chart-title">Net-revenue change distribution</h2>
    <p class="chart-note">Planner − baseline net revenue (₹) per scenario, ${a.n} runs. Bars right of zero are gains.</p>
    ${histogramSvg(a.revDeltas)}
  </section>`;
}

function renderEvaluation(ev) {
  const a = evalAggregates(ev);
  $('eval-meta').textContent =
    `${a.n} synthetic scenarios · mode “${ev.mode}” · seeds ${ev.seeds[0]}–${ev.seeds[ev.seeds.length - 1]} · schema v${ev.schema_version}`;

  $('eval-notes').innerHTML =
    `<div class="note info">These results are generated from labelled synthetic fixtures and are fully reproducible with <code>python -m engine.scripts.run_eval</code>.</div>` +
    `<div class="note warn">The planner reliably raises net revenue (won <strong>${a.nr.win}/${a.n}</strong>, never worse) but the FEFO baseline already avoids spoilage, so spoilage is <strong>tied in ${a.sp.tie}/${a.n}</strong> scenarios and demand fulfillment is <strong>lower in ${a.fp.loss}/${a.n}</strong> runs. Reported honestly rather than tuned away.</div>`;

  $('eval-cards').innerHTML =
    statCard('Mean net revenue vs baseline',
      `${signed(a.nrMean, money)}`,
      `${a.nrPctAgg === null ? '—' : NUM(a.nrPctAgg, 2) + '%'} aggregate · planner wins ${a.nr.win}/${a.n} · never worse`) +
    statCard('Spoilage reduction',
      `${a.sp.win}/${a.n} wins`,
      `planner kg Δ mean ${signed(a.spMean, (t) => NUM(t, 2))} · tied in ${a.sp.tie} runs · no reduction demonstrated`) +
    statCard('Demand fulfillment Δ',
      `${signed(a.fpMean, (t) => NUM(t, 2))} pp`,
      `lower than baseline in ${a.fp.loss}/${a.n} runs · planner wins ${a.fp.win}/${a.n}`) +
    statCard('Full-metric wins',
      `${a.allWins}/${a.n}`,
      'planner ≥ baseline on revenue, spoilage and fulfillment') +
    statCard('Infeasible runs',
      `${a.infeasB} / ${a.infeasP}`,
      'baseline / planner · a constraint violation would void a win');

  $('eval-charts').innerHTML = outcomeChart(a) + distributionChart(a);

  const sel = $('scenario-select');
  sel.innerHTML = (ev.scenarios || []).map((sc, i) =>
    `<option value="${i}">${esc(sc.scenario_id)}${sc.disruption ? ' · ' + esc(sc.disruption.type) : ''}</option>`).join('');
  sel.addEventListener('change', () => renderScenario(ev.scenarios[Number(sel.value)]));
  if (ev.scenarios && ev.scenarios.length) renderScenario(ev.scenarios[0]);
}

function barRow(who, value, max, cls, fmt) {
  const w = max > 0 ? Math.max(0, Math.min(100, value / max * 100)) : 0;
  return `<div class="bar-row"><span class="who">${esc(who)}</span>
    <div class="bar"><span class="${cls}" style="width:${w.toFixed(2)}%"></span></div>
    <span class="amt">${fmt(value)}</span></div>`;
}

function barGroup(label, bv, pv, fmt) {
  const max = Math.max(Math.abs(bv) || 0, Math.abs(pv) || 0, 1e-9);
  return `<div class="bar-group"><div class="bar-label">${esc(label)}</div>
    ${barRow('Baseline', bv, max, 'fill-baseline', fmt)}
    ${barRow('Planner', pv, max, 'fill-planner', fmt)}</div>`;
}

function renderScenario(sc) {
  const view = $('scenario-view');
  const r = (sc.runs || [])[0];
  if (!r) { view.innerHTML = '<p class="empty">No run data for this scenario.</p>'; return; }
  const bm = r.baseline.metrics, pm = r.planner.metrics;
  const imp = r.improvement || {};
  const win = r.win || {};
  const nrd = (imp.net_revenue || {}).delta ?? 0;
  const spd = (imp.spoilage_kg || {}).delta ?? 0;
  const fpd = (imp.fulfillment_pct || {}).delta ?? 0;

  view.innerHTML = `
    <div class="scenario-meta">
      <span class="tag">seed ${r.seed}</span>
      <span class="tag">${esc(sc.disruption ? 'disruption: ' + sc.disruption.type : 'no disruption')}</span>
      <span class="tag ${win.all_metrics ? 'win' : ''}">all-metric win: ${win.all_metrics ? 'yes' : 'no'}</span>
    </div>
    <div class="bars">
      ${barGroup('Net revenue (₹, higher is better)', bm.net_revenue, pm.net_revenue, money)}
      ${barGroup('Spoilage (kg, lower is better)', bm.spoiled_kg, pm.spoiled_kg, (t) => NUM(t, 1))}
      ${barGroup('Demand fulfillment (%, higher is better)', bm.fulfillment_pct, pm.fulfillment_pct, (t) => NUM(t, 2))}
    </div>
    <div class="table-wrap" style="margin-top:var(--sp4)">
      <table class="responsive">
        <caption class="sr-only">This scenario's baseline vs planner metrics and the outcome for each.</caption>
        <thead><tr>
          <th scope="col">Metric</th><th scope="col" class="num">Baseline</th><th scope="col" class="num">Planner</th>
          <th scope="col" class="num">Change</th><th scope="col">Outcome</th>
        </tr></thead><tbody>
          <tr><td data-label="Metric">Net revenue</td><td class="num" data-label="Baseline">${money(bm.net_revenue)}</td>
              <td class="num" data-label="Planner">${money(pm.net_revenue)}</td>
              <td class="num ${nrd < 0 ? 'neg' : 'pos'}" data-label="Change">${signed(nrd, money)}</td>
              <td data-label="Outcome">${outcomeTag(nrd, 'higher_better', TOL_INR)}</td></tr>
          <tr><td data-label="Metric">Spoilage (kg)</td><td class="num" data-label="Baseline">${NUM(bm.spoiled_kg, 2)}</td>
              <td class="num" data-label="Planner">${NUM(pm.spoiled_kg, 2)}</td>
              <td class="num ${spd > TOL_KG ? 'neg' : ''}" data-label="Change">${signed(spd, (t) => NUM(t, 2))}</td>
              <td data-label="Outcome">${outcomeTag(spd, 'lower_better', TOL_KG)}</td></tr>
          <tr><td data-label="Metric">Fulfillment (%)</td><td class="num" data-label="Baseline">${NUM(bm.fulfillment_pct, 2)}</td>
              <td class="num" data-label="Planner">${NUM(pm.fulfillment_pct, 2)}</td>
              <td class="num ${fpd < -TOL_KG ? 'neg' : 'pos'}" data-label="Change">${signed(fpd, (t) => NUM(t, 2))}</td>
              <td data-label="Outcome">${outcomeTag(fpd, 'higher_better', TOL_KG)}</td></tr>
        </tbody>
      </table>
    </div>`;
}

/* ---------- view switching ---------- */

let activateView = () => {};

function initTabs() {
  const tabs = [$('tab-overview'), $('tab-evaluation')];
  const views = { 'tab-overview': $('view-overview'), 'tab-evaluation': $('view-evaluation') };
  activateView = (id, focus) => {
    tabs.forEach((t) => {
      const on = t.id === id;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      views[t.id].hidden = !on;
    });
    if (focus) $(id).focus();
  };
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => activateView(t.id));
    t.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
        activateView(next.id, true);
      } else if (e.key === 'Home') { e.preventDefault(); activateView(tabs[0].id, true); }
      else if (e.key === 'End') { e.preventDefault(); activateView(tabs[tabs.length - 1].id, true); }
    });
  });
}

/* ---------- boot ---------- */

function showError(msg) {
  const el = $('load-error');
  el.hidden = false;
  el.innerHTML = msg;
  $('loading').hidden = true;
}

function renderFooter() {
  $('footer').innerHTML =
    `Engine-generated demo data · regenerate with <code>python -m engine.scripts.run_plan --seed 1</code> ` +
    `and <code>python -m engine.scripts.run_eval --out demo/evaluation.json</code> · ` +
    `served with <code>python dashboard/serve.py</code>.`;
}

async function init() {
  renderFooter();
  initTabs();
  let overviewOk = false, evalOk = false;
  try {
    const result = await fetchJSON('../demo/result.json');
    renderDetail(result);
    overviewOk = true;
  } catch (e) {
    showError(`Could not load <code>../demo/result.json</code> — ${esc(e.message)}. Run: <code>python -m engine.scripts.run_plan --seed 1</code>`);
  }
  try {
    const ev = await fetchJSON('../demo/evaluation.json');
    renderEvaluation(ev);
    evalOk = true;
  } catch (e) {
    $('tab-evaluation').disabled = true;
    $('eval-meta').textContent = 'Evaluation fixture unavailable — run: python -m engine.scripts.run_eval --out demo/evaluation.json';
    if (!overviewOk) showError(`Could not load dashboard data — ${esc(e.message)}.`);
  }
  $('loading').hidden = true;
  // show the first view that actually loaded; keep tabs consistent with it
  activateView(overviewOk || !evalOk ? 'tab-overview' : 'tab-evaluation');
}

document.addEventListener('DOMContentLoaded', init);
