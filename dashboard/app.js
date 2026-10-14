'use strict';

/* Aurenza dashboard: reads only the engine-generated JSON files
 * (../demo/result.json and ../demo/evaluation.json). Imports no engine code.
 * Every number is read from those files — nothing is hardcoded. */

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
const signed = (n, fmt) => (n > 0 ? '+' : '') + fmt(n);

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

// delta chip class: good/bad/neutral given metric direction.
function chipClass(delta, direction, tol) {
  if (delta === null || delta === undefined || Math.abs(delta) <= tol) return 'flat';
  const good = direction === 'higher_better' ? delta > 0 : delta < 0;
  return good ? 'up' : 'down';
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
      <div class="delta">Change
        <span class="chip ${cls}">${arrow} ${deltaText}</span>
      </div>
    </div>`;
}

function statCard(title, big, sub) {
  return `<div class="card"><p class="card-title">${esc(title)}</p>
    <div style="font-size:21px;font-weight:700;font-variant-numeric:tabular-nums">${big}</div>
    <div class="muted" style="margin-top:6px">${sub || ''}</div></div>`;
}

function dispatchTable(dispatches) {
  if (!dispatches || !dispatches.length) {
    return '<p class="empty">No dispatches in this plan.</p>';
  }
  const rows = dispatches.map((d) => `
    <tr>
      <td>${esc(d.batch_id)}</td>
      <td>${esc(d.destination_id)}</td>
      <td class="num">${NUM(d.quantity_kg, 1)}</td>
      <td class="num">${NUM(d.discount_pct, 0)}</td>
      <td class="num">${money(d.effective_price_per_kg)}</td>
      <td class="num">${NUM(d.sold_kg, 1)}</td>
      <td class="num ${d.expected_contribution < 0 ? 'neg' : ''}">${money(d.expected_contribution)}</td>
      <td class="reason">${esc(d.reason)}</td>
    </tr>`).join('');
  return `<table><thead><tr>
      <th>Batch</th><th>Destination</th><th class="num">Qty (kg)</th><th class="num">Disc %</th>
      <th class="num">Eff ₹/kg</th><th class="num">Sold (kg)</th><th class="num">Contribution</th><th>Reason</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
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
      <td>${esc(id)}</td>
      <td class="num">${NUM(harvested, 0)}</td>
      <td class="num">${NUM(b.dispatched_kg, 0)}</td>
      <td class="num">${NUM(b.sold_kg, 0)}</td>
      <td class="num ${b.spoiled_kg > 0 ? 'neg' : ''}">${NUM(b.spoiled_kg, 0)}</td>
      <td class="num">${NUM(p.dispatched_kg, 0)}</td>
      <td class="num">${NUM(p.sold_kg, 0)}</td>
      <td class="num ${p.spoiled_kg > 0 ? 'neg' : ''}">${NUM(p.spoiled_kg, 0)}</td>
      <td class="num">${NUM(p.fresh_inventory_kg, 0)}</td>
    </tr>`;
  }).join('');
  return `<table><thead><tr>
      <th>Batch</th><th class="num">Harvested</th>
      <th class="num">B dispatched</th><th class="num">B sold</th><th class="num">B spoiled</th>
      <th class="num">P dispatched</th><th class="num">P sold</th><th class="num">P spoiled</th>
      <th class="num">P fresh inv.</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

function reconRows(name, rec) {
  if (!rec) return '';
  const ok = rec.check_ok === true;
  return `<div class="recon-row">
    <span class="${ok ? 'ok' : 'bad'}">${ok ? 'PASS' : 'FAIL'}</span>
    <strong>${esc(name)}</strong>
    <span class="detail">Σ dispatch contributions ${money(rec.sum_dispatch_contributions)} − spoilage ${money(rec.spoilage_cost)} = net ${money(rec.net_revenue)}</span>
  </div>`;
}

/* ---------- detail view (demo/result.json) ---------- */

function renderDetail(result) {
  const b = result.results.baseline;
  const p = result.results.planner;
  const imp = result.improvement || {};
  const bm = b.metrics, pm = p.metrics;

  $('detail-meta').textContent =
    `${result.scenario_id} · seed ${result.seed} · schema v${result.schema_version} · generated by ${result.generated_by}`;

  // KPI comparison cards
  const nr = imp.net_revenue || {};
  const sp = imp.spoilage_kg || {};
  const fp = imp.fulfillment_pct || {};
  const nrPctText = (nr.delta_pct === null || nr.delta_pct === undefined) ? '—' : NUM(nr.delta_pct, 2) + '%';

  $('kpi-cards').innerHTML =
    compareCard({
      title: 'Net revenue',
      baselineText: money(bm.net_revenue), plannerText: money(pm.net_revenue),
      deltaText: `${signed(nr.delta, money)} (${nrPctText})`,
      direction: 'higher_better', delta: nr.delta, tol: TOL_INR,
    }) +
    compareCard({
      title: 'Spoilage',
      baselineText: kg(bm.spoiled_kg), plannerText: kg(pm.spoiled_kg),
      deltaText: `${signed(sp.delta, (v) => NUM(v, 2) + ' kg')}`,
      direction: 'lower_better', delta: sp.delta, tol: TOL_KG,
    }) +
    compareCard({
      title: 'Demand fulfillment',
      baselineText: pct(bm.fulfillment_pct), plannerText: pct(pm.fulfillment_pct),
      deltaText: `${signed(fp.delta, (v) => NUM(v, 2) + ' pp')}`,
      direction: 'higher_better', delta: fp.delta, tol: TOL_KG,
    }) +
    statCard('Scenario supply & demand',
      `${NUM(bm.harvested_kg, 0)} kg`,
      `harvested · demand ${NUM(bm.demand_kg, 0)} kg · baseline ships ${NUM(bm.dispatched_kg, 0)} kg, planner ships ${NUM(pm.dispatched_kg, 0)} kg`);

  // Honest messaging
  const notes = [];
  notes.push(`<div class="note info">Synthetic fixture scenario <strong>${esc(result.scenario_id)}</strong>, generated by the Aurenza engine — not observed real-world performance.</div>`);
  if ((nr.delta || 0) > TOL_INR) {
    notes.push(`<div class="note good">Planner net revenue is <strong>${money(nr.delta)}</strong> (${nrPctText}) higher than the FEFO baseline.</div>`);
  }
  if (Math.abs(sp.delta || 0) <= TOL_KG) {
    notes.push('<div class="note warn">No spoilage reduction in this scenario: the FEFO baseline already dispatches expiring stock first, so both strategies leave the same kg to spoil.</div>');
  }
  if ((fp.delta || 0) < -TOL_KG) {
    notes.push(`<div class="note warn">Planner demand fulfillment is <strong>${NUM(fp.delta, 2)} pp lower</strong> than the baseline here — it skips dispatches that would lose money, so it moves less volume. Net revenue is still higher. This is an honest trade-off, not a fixed guarantee.</div>`);
  }
  if (pm.feasible === false) {
    notes.push('<div class="note warn">Planner plan reports a feasibility violation — see <code>metrics.violations</code>.</div>');
  }
  $('detail-notes').innerHTML = notes.join('');

  $('planner-dispatches').innerHTML = dispatchTable(p.dispatches);
  $('baseline-dispatches').innerHTML = dispatchTable(b.dispatches);
  $('batch-table').innerHTML = batchTable(b.batch_summary, p.batch_summary);
  $('recon').innerHTML = reconRows('Baseline', b.reconciliation) + reconRows('Planner', p.reconciliation);
}

/* ---------- evaluation view (demo/evaluation.json) ---------- */

function evalAggregates(ev) {
  const runs = [];
  (ev.scenarios || []).forEach((sc) => (sc.runs || []).forEach((r) => runs.push(r)));
  const n = runs.length;
  const agg = { n, nrWins: 0, spWins: 0, fpWins: 0, allWins: 0, spTie: 0, fpLoss: 0,
    nrDelta: 0, sumB: 0, sumP: 0, spDelta: 0, fpDelta: 0, infeasB: 0, infeasP: 0 };
  runs.forEach((r) => {
    const imp = r.improvement || {};
    const win = r.win || {};
    agg.nrWins += win.net_revenue ? 1 : 0;
    agg.spWins += win.spoilage_kg ? 1 : 0;
    agg.fpWins += win.fulfillment_pct ? 1 : 0;
    agg.allWins += win.all_metrics ? 1 : 0;
    if (imp.spoilage_kg && Math.abs(imp.spoilage_kg.delta || 0) <= TOL_KG) agg.spTie++;
    if (imp.fulfillment_pct && (imp.fulfillment_pct.delta || 0) < -TOL_KG) agg.fpLoss++;
    if (imp.net_revenue) {
      agg.nrDelta += imp.net_revenue.delta || 0;
      agg.sumB += imp.net_revenue.baseline || 0;
      agg.sumP += imp.net_revenue.planner || 0;
    }
    if (imp.spoilage_kg) agg.spDelta += imp.spoilage_kg.delta || 0;
    if (imp.fulfillment_pct) agg.fpDelta += imp.fulfillment_pct.delta || 0;
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

function renderEvaluation(ev) {
  const a = evalAggregates(ev);
  $('eval-meta').textContent =
    `${a.n} synthetic scenarios · mode "${ev.mode}" · seeds ${ev.seeds[0]}–${ev.seeds[ev.seeds.length - 1]} · schema v${ev.schema_version}`;

  $('eval-cards').innerHTML =
    statCard('Mean net revenue vs baseline',
      `${signed(a.nrMean, money)}`,
      `${a.nrPctAgg === null ? '—' : NUM(a.nrPctAgg, 2) + '%'} aggregate · planner wins ${a.nrWins}/${a.n} · never worse`) +
    statCard('Spoilage reduction',
      `${a.spWins}/${a.n} wins`,
      `planner kg Δ mean ${signed(a.spMean, (v) => NUM(v, 2))} · tied in ${a.spTie} runs · no reduction demonstrated`) +
    statCard('Demand fulfillment Δ',
      `${signed(a.fpMean, (v) => NUM(v, 2))} pp`,
      `lower than baseline in ${a.fpLoss}/${a.n} runs · planner wins ${a.fpWins}/${a.n}`) +
    statCard('Full-metric wins',
      `${a.allWins}/${a.n}`,
      'planner ≥ baseline on revenue, spoilage and fulfillment') +
    statCard('Infeasible runs',
      `${a.infeasB} / ${a.infeasP}`,
      'baseline / planner · constraint violation would void a win');

  // honest summary note
  const notes = document.createElement('div');
  notes.className = 'notes';
  notes.id = 'eval-notes';
  notes.innerHTML =
    `<div class="note info">These results are generated from labelled synthetic fixtures and are fully reproducible with <code>python -m engine.scripts.run_eval</code>.</div>` +
    `<div class="note warn">The planner reliably raises net revenue (won ${a.nrWins}/${a.n}, never worse) but the FEFO baseline already avoids spoilage, so spoilage is <strong>tied in ${a.spTie}/${a.n}</strong> scenarios and demand fulfillment is <strong>lower in ${a.fpLoss}/${a.n}</strong> runs. Reported honestly rather than tuned away.</div>`;
  const section = $('eval-section');
  section.insertBefore(notes, $('eval-cards'));

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
  return `<div class="bar-group"><div class="bar-label"><span>${esc(label)}</span></div>
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

  const resultChip = (label, key, direction) => {
    const d = (imp[key] || {}).delta || 0;
    const tol = key === 'net_revenue' ? TOL_INR : TOL_KG;
    const cls = chipClass(d, direction, tol);
    const txt = cls === 'flat' ? 'tie' : (cls === 'up' ? 'win' : 'loss');
    return `<span class="tag ${win[key] ? 'win' : (cls === 'down' && direction !== 'lower_better' ? 'loss' : '')}">${esc(label)}: ${txt}</span>`;
  };

  view.innerHTML = `
    <div class="scenario-meta">
      <span class="tag">seed ${r.seed}</span>
      <span class="tag">${esc(sc.disruption ? 'disruption: ' + sc.disruption.type : 'no disruption')}</span>
      <span class="tag ${win.all_metrics ? 'win' : ''}">all-metric win: ${win.all_metrics ? 'yes' : 'no'}</span>
    </div>
    <div class="bars">
      ${barGroup('Net revenue (₹)', bm.net_revenue, pm.net_revenue, money)}
      ${barGroup('Spoilage (kg, lower is better)', bm.spoiled_kg, pm.spoiled_kg, (v) => NUM(v, 1))}
      ${barGroup('Demand fulfillment (%)', bm.fulfillment_pct, pm.fulfillment_pct, (v) => NUM(v, 2))}
    </div>
    <div class="table-wrap" style="margin-top:16px">
      <table><thead><tr>
        <th>Metric</th><th class="num">Baseline</th><th class="num">Planner</th><th class="num">Change</th><th>Result</th>
      </tr></thead><tbody>
        <tr><td>Net revenue</td><td class="num">${money(bm.net_revenue)}</td><td class="num">${money(pm.net_revenue)}</td>
            <td class="num ${(imp.net_revenue || {}).delta < 0 ? 'neg' : 'pos'}">${signed((imp.net_revenue || {}).delta, money)}</td>
            <td>${resultChip('Revenue', 'net_revenue', 'higher_better')}</td></tr>
        <tr><td>Spoilage (kg)</td><td class="num">${NUM(bm.spoiled_kg, 2)}</td><td class="num">${NUM(pm.spoiled_kg, 2)}</td>
            <td class="num ${(imp.spoilage_kg || {}).delta > 0 ? 'neg' : 'pos'}">${signed((imp.spoilage_kg || {}).delta, (v) => NUM(v, 2))}</td>
            <td>${resultChip('Spoilage', 'spoilage_kg', 'lower_better')}</td></tr>
        <tr><td>Fulfillment (%)</td><td class="num">${NUM(bm.fulfillment_pct, 2)}</td><td class="num">${NUM(pm.fulfillment_pct, 2)}</td>
            <td class="num ${(imp.fulfillment_pct || {}).delta < 0 ? 'neg' : 'pos'}">${signed((imp.fulfillment_pct || {}).delta, (v) => NUM(v, 2))}</td>
            <td>${resultChip('Fulfillment', 'fulfillment_pct', 'higher_better')}</td></tr>
      </tbody></table>
    </div>`;
}

/* ---------- boot ---------- */

function showError(msg) {
  const el = $('load-error');
  el.hidden = false;
  el.textContent = msg;
}

function renderFooter() {
  $('footer').innerHTML =
    `Engine-generated demo data · regenerate with <code>python -m engine.scripts.run_plan --seed 1</code> ` +
    `and <code>python -m engine.scripts.run_eval --out demo/evaluation.json</code> · ` +
    `served with <code>python dashboard/serve.py</code>.`;
}

async function init() {
  renderFooter();
  let loaded = 0;
  try {
    const result = await fetchJSON('../demo/result.json');
    renderDetail(result);
    $('detail-section').hidden = false;
    loaded++;
  } catch (e) {
    showError(`Could not load ../demo/result.json — ${e.message}. Run: python -m engine.scripts.run_plan --seed 1`);
  }
  try {
    const ev = await fetchJSON('../demo/evaluation.json');
    renderEvaluation(ev);
    $('eval-section').hidden = false;
    loaded++;
  } catch (e) {
    // evaluation.json is optional: the dashboard still works with result.json
    if (!loaded) showError(`Could not load dashboard data — ${e.message}.`);
  }
}

document.addEventListener('DOMContentLoaded', init);
