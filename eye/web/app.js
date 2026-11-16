let state, eye = 'R', demo = !!window.SANS_STATIC;
const $ = s => document.querySelector(s);
const fmt = (v, digits = 2, signed = false) => v == null ? '—' : `${signed && v > 0 ? '+' : ''}${Number(v).toFixed(digits)}`;
const status = r => !r || r.delta_trt_um == null ? ['Baseline needed', 'neutral'] : r.threshold_status === 'EARLY_ODE_RESEARCH_THRESHOLD_EXCEEDED' ? ['Research threshold exceeded', 'warn'] : ['Research threshold not exceeded', ''];
let noticeTimer;
function notice(message, error = false) { $('#notice').textContent = message; $('#notice').className = error ? 'error' : ''; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => $('#notice').textContent = '', 6000); }
const STATIC = window.SANS_STATIC || null;
const READ_ONLY = 'This is a read-only showcase. Run sans_web.py locally to enter measurements.';
function staticDownload(name, text) {
  const blob = new Blob(['\ufeff' + text], {type: 'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
async function request(path, body) {
  if (STATIC) {
    if (body === undefined) {
      if (path === '/api/demo') return JSON.parse(JSON.stringify(STATIC.demo));
      if (path === '/api/data') return JSON.parse(JSON.stringify(STATIC.data));
      if (path === '/api/export-linked') return JSON.parse(JSON.stringify(STATIC.exportLinked));
      if (path === '/api/export') { staticDownload('sans_export.csv', STATIC.exportCsv); return {}; }
    }
    throw new Error(READ_ONLY);
  }
  const res = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed. Please try again.');
  return data;
}
async function load() { state = await request(demo ? '/api/demo' : '/api/data'); render(); }
const eyeName = e => e === 'R' ? 'Right eye' : 'Left eye';
const isExceeded = r => r?.threshold_status === 'EARLY_ODE_RESEARCH_THRESHOLD_EXCEEDED';
const needsRateReview = r => r?.change_review_status === 'CHANGE_REVIEW_SUGGESTED_EXPERIMENTAL';
function eyeSummary(e) {
  const item = state.eyes[e], r = item.results.at(-1);
  const exceeded = isExceeded(r), unknown = !r || r.delta_trt_um == null;
  const tone = exceeded ? 'attention' : unknown ? 'unknown' : 'within';
  const title = !r ? 'No measurement yet' : r.delta_trt_um == null ? 'Baseline needed' : exceeded ? 'Early ODE signal · review needed' : 'Research threshold not exceeded';
  let trend = 'First reading · trend not available';
  if (r?.change_since_previous_um != null) {
    const change = r.change_since_previous_um;
    trend = `${change > 0 ? '↑ Increased' : change < 0 ? '↓ Decreased' : '→ Unchanged'} ${fmt(Math.abs(change))} μm over ${r.interval_days} days`;
    if (change < 0 && exceeded) trend += ' · Still above threshold';
  }
  return `<article class="eye-result ${tone}" aria-label="${eyeName(e)}: ${title}"><div class="eye-result-heading"><h2>${eyeName(e)} <small>${e === 'R' ? 'OD' : 'OS'}</small></h2><span>${r ? `Latest: FD ${r.flight_day}` : 'No scan recorded'}</span></div><div class="eye-result-status"><span aria-hidden="true">${exceeded ? '▲' : unknown ? '○' : '✓'}</span> ${title}</div><div class="eye-delta">${fmt(r?.delta_trt_um,2,true)} <small>μm</small></div><div class="delta-caption">Change from preflight baseline${r?.relative_change_percent != null ? ` · ${fmt(r.relative_change_percent,2,true)}%` : ''}</div><div class="eye-facts"><span>Current TRT <strong>${fmt(r?.current_trt_um)} μm</strong></span><span>Baseline <strong>${fmt(item.baseline)} μm</strong></span></div><p class="eye-trend">${r ? trend : 'Enter a reviewed OCT result to begin.'}</p>${needsRateReview(r) ? '<p class="rate-review">◆ Experimental rate flag · Verify the measurement</p>' : ''}<div class="eye-result-foot">${unknown ? 'Not assessed — missing data is not a normal result.' : exceeded ? 'Above the +19.4 μm research threshold.' : 'At or below the +19.4 μm research threshold.'}</div></article>`;
}
function renderEyeOverview() {
  const latest = ['R','L'].map(e => ({eye:e, record:state.eyes[e].results.at(-1)}));
  const flags = latest.filter(x=>isExceeded(x.record));
  const unknown = latest.filter(x=>!x.record || x.record.delta_trt_um == null);
  const rateFlags = latest.filter(x=>needsRateReview(x.record));
  const any = latest.some(x=>x.record);
  const names = values => values.map(x=>eyeName(x.eye)).join(' and ');
  const banner = $('#mission-status');
  banner.className = `mission-status ${flags.length ? 'attention' : rateFlags.length ? 'review' : unknown.length ? 'unknown' : 'within'}`;
  const title = flags.length ? `${names(flags)}: threshold exceeded` : rateFlags.length ? 'Measurement review suggested' : unknown.length ? 'Assessment incomplete' : 'Neither eye exceeds the research threshold';
  let subtitle = flags.length ? 'Early optic disc swelling signal. Check the scan and track the next measurement.' : rateFlags.length ? 'The optional rate rule was triggered. Check measurement quality; this is not a medical urgency grade.' : unknown.length ? 'Add the missing measurement or preflight baseline to assess each eye.' : 'Continue your monitoring schedule and log any countermeasures used.';
  if (unknown.length && (flags.length || rateFlags.length)) subtitle += ` ${names(unknown)}: assessment incomplete.`;
  const dates = latest.filter(x=>x.record).map(x=>x.record.flight_day);
  if (dates.length===2 && dates[0]!==dates[1]) subtitle += ' The eyes were last measured on different flight days.';
  banner.innerHTML = `<div class="mission-icon" aria-hidden="true">${flags.length ? '▲' : rateFlags.length ? '◆' : unknown.length ? '○' : '✓'}</div><div><h2>${title}</h2><p>${subtitle}</p></div>`;
  $('#eye-overview').innerHTML = ['R','L'].map(eyeSummary).join('');
  const actionTitle = flags.length ? 'Check the change. Track your response.' : rateFlags.length ? 'Check the unexpected change.' : !any ? 'Start with a reviewed OCT result.' : unknown.length ? 'Complete the missing reference.' : 'Keep to your assigned scan schedule.';
  const steps = flags.length ? ['Confirm the eye, BMO–250 μm region and preflight baseline.', 'Have scan alignment and tissue boundaries checked; repeat imaging if advised.', 'Log any countermeasures used; compare your next OCT result.'] : rateFlags.length ? ['Confirm the entered value, scan day and measurement method.', 'Ask the scan reviewer to check alignment and segmentation.', 'Log your next scan to follow the change.'] : unknown.length ? ['Use the same eye and region for the baseline and in-flight scan.', 'Complete the preflight reference using the Baseline button.', 'You can save TRT now; baseline-based assessment stays unavailable.'] : ['Record the next reviewed scan on its actual flight day.', 'Keep acquisition and analysis methods consistent.', 'Report visual changes through your mission medical procedure.'];
  $('#next-action').innerHTML = `<h2>${actionTitle}</h2><ol class="next-step-list">${steps.map(x=>`<li>${x}</li>`).join('')}</ol>`;
}

function render() {
  const item = state.eyes[eye], rows = item.results, last = rows.at(-1), [label, tone] = status(last);
  $('#demo-banner').hidden = !demo; $('#demo').textContent = demo ? 'Viewing demo' : 'Explore demo ↗';
  for (const form of [$('#record-form'), $('#baseline-form')]) for (const input of form.elements) input.disabled = demo;

  for (const e of ['R','L']) { const input = $('#baseline-form').elements[e]; input.disabled = demo || state.eyes[e].baseline != null; input.value = demo ? '' : state.eyes[e].baseline ?? ''; }
  $('#export').hidden = demo || !['R','L'].some(e => state.eyes[e].results.length);
  syncBaseline();
  renderCountermeasures();
  renderEyeOverview();
  const cards = [ ['Change from baseline',fmt(last?.delta_trt_um,2,true),'μm',last?.relative_change_percent != null ? `${fmt(last.relative_change_percent,2,true)}% relative change` : 'Requires a preflight baseline'], ['Interval change rate',fmt(last?.rate_um_per_day,3,true),'μm/day',last?.interval_days != null ? `Across the last ${last.interval_days} days · Δ ${fmt(last.change_since_previous_um,2,true)} μm` : 'Requires two measurements'], ['Accumulated deviation',fmt(last?.accumulated_deviation_um_days,1),'μm·days',last?.integral_start_flight_day != null ? `FD ${last.integral_start_flight_day}–${last.flight_day} · Signed integral` : 'Requires a baseline and measurement'], [state.settings.prediction_days ? `Estimated ΔTRT in ${state.settings.prediction_days} days` : 'Linear extrapolation',fmt(last?.forecast_delta_trt_um,2,true),'μm Δ',state.settings.prediction_days ? `${state.settings.prediction_days}-day horizon · Latest rate continues` : 'Optional · Enable in analysis settings'] ];
  $('#metrics').innerHTML = cards.map(([title,value,unit,note])=>`<div class="metric ${title === 'Change from baseline' && isExceeded(last) ? 'metric-flagged' : title === 'Interval change rate' && needsRateReview(last) ? 'metric-review' : ''}"><div class="metric-title">${title}</div><div class="metric-value">${value} <small>${unit}</small></div><div class="metric-note">${note}</div></div>`).join('');
  drawChart(rows);
  let copy = !last ? 'Start with a preflight baseline and your first measurement. Each eye is analyzed independently.' : last.delta_trt_um == null ? 'Without a preflight baseline, interval changes can still be tracked, but baseline deviation and threshold status cannot be assessed.' : tone === 'warn' ? 'The current change exceeds the +19.4 μm research threshold.' : 'The current change does not exceed the +19.4 μm research threshold used in this model. This does not rule out SANS.';
  if(last?.change_since_previous_um < 0 && last?.delta_trt_um > 0) copy += ' Thickness has decreased since the previous measurement but remains above baseline.';
  if(last?.change_review_status === 'CHANGE_REVIEW_SUGGESTED_EXPERIMENTAL') copy += ' Experimental rate review triggered: check the input and measurement quality, and consider a repeat measurement.';
  copy += ' Rates are interval averages. The integral assumes linear change between recorded observations; negative deviations offset positive ones. It is not cumulative damage.';
  $('#interpretation').textContent = copy;
  $('#analysis-countermeasure-reminder').hidden = last?.delta_trt_um == null || !isExceeded(last);
  const all = ['R','L'].flatMap(e => state.eyes[e].results.map(r => ({...r,eye:e}))).sort((a,b)=>b.flight_day-a.flight_day || a.eye.localeCompare(b.eye));
  $('#history-body').innerHTML = all.length ? all.map(r=>`<tr><td>FD ${r.flight_day}</td><td>${r.eye==='R'?'Right':'Left'}</td><td>${fmt(r.current_trt_um)}</td><td class="${status(r)[1] === 'warn' ? 'flagged-value' : ''}">${fmt(r.delta_trt_um,2,true)}</td><td>${fmt(r.change_since_previous_um,2,true)}</td><td>${fmt(r.rate_um_per_day,3,true)}</td><td>${fmt(r.accumulated_deviation_um_days,1)}</td><td><span class="status-pill ${status(r)[1]}">${r.delta_trt_um == null ? 'Not assessed' : status(r)[1] === 'warn' ? 'Exceeded' : 'Not exceeded'}</span></td><td>${demo ? '' : `<button data-delete="${r.eye}:${r.flight_day}" aria-label="Delete ${r.eye} eye flight day ${r.flight_day}">Delete</button>`}</td></tr>`).join('') : '<tr><td colspan="9" class="empty">No measurements yet. Save your first daily check-in to begin.</td></tr>';
  for(const key of Object.keys(state.settings)) $('#settings-form').elements[key].value = state.settings[key] ?? '';
}
function drawChart(rows) {
  const valid = rows.filter(r=>r.delta_trt_um != null);
  if(!valid.length) { $('#chart').innerHTML = '<div class="empty">Your trend starts here.<br>Add a baseline and at least one measurement to see your ΔTRT curve.</div>'; return; }
  const W=940,H=300,L=55,R=20,T=35,B=45;
  let xmin=Math.min(...valid.map(r=>r.flight_day)),xmax=Math.max(...valid.map(r=>r.flight_day)); if(xmin===xmax){xmin=Math.max(0,xmin-5);xmax+=5;}
  const values=valid.map(r=>r.delta_trt_um),lo=Math.min(0,...values),hi=Math.max(19.4,...values),pad=Math.max(5,(hi-lo)*.16),ymin=lo-pad,ymax=hi+pad;
  const x=d=>L+(d-xmin)/(xmax-xmin)*(W-L-R),y=v=>H-B-(v-ymin)/(ymax-ymin)*(H-T-B);
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${eye==='R'?'Right':'Left'} eye change from baseline in micrometres by flight day"><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#197b73" stop-opacity=".12"/><stop offset="100%" stop-color="#197b73" stop-opacity="0"/></linearGradient></defs>`;
  for(let i=0;i<=4;i++){const v=ymin+(ymax-ymin)*i/4,d=xmin+(xmax-xmin)*i/4;svg+=`<line x1="${L}" y1="${y(v)}" x2="${W-R}" y2="${y(v)}" stroke="#edf1ed"/><text x="${L-12}" y="${y(v)+4}" text-anchor="end">${v.toFixed(1)}</text><text x="${x(d)}" y="${H-18}" text-anchor="middle">${+d.toFixed(1)}</text>`;}
  svg+=`<line x1="${L}" x2="${W-R}" y1="${y(0)}" y2="${y(0)}" stroke="#adbfb7" stroke-dasharray="3 5"/><line x1="${L}" x2="${W-R}" y1="${y(19.4)}" y2="${y(19.4)}" stroke="#c99b62" stroke-dasharray="5 5"/><text x="${W-R}" y="${y(19.4)-9}" text-anchor="end" style="fill:#ad7d42">+19.4 μm</text>`;
  const points=valid.map(r=>`${x(r.flight_day)},${y(r.delta_trt_um)}`).join(' ');
  svg+=`<polygon points="${x(valid[0].flight_day)},${y(0)} ${points} ${x(valid.at(-1).flight_day)},${y(0)}" fill="url(#fill)"/><polyline points="${points}" fill="none" stroke="#197b73" stroke-width="2.5" stroke-linejoin="round"/>`;
  for(const r of valid) svg+=`<circle cx="${x(r.flight_day)}" cy="${y(r.delta_trt_um)}" r="4" fill="${r.threshold_status === 'EARLY_ODE_RESEARCH_THRESHOLD_EXCEEDED' ? '#b53f2d' : 'white'}" stroke="${r.threshold_status === 'EARLY_ODE_RESEARCH_THRESHOLD_EXCEEDED' ? '#b53f2d' : '#197b73'}" stroke-width="2"><title>Flight day ${r.flight_day}: ${fmt(r.delta_trt_um,2,true)} μm</title></circle>`;
  $('#chart').innerHTML=svg+'</svg>';
}
for(const button of document.querySelectorAll('[data-view]')) button.onclick=()=>{for(const view of document.querySelectorAll('.view')) view.hidden=view.id!==button.dataset.view;for(const nav of document.querySelectorAll('.nav'))nav.classList.toggle('active',nav.dataset.view===button.dataset.view);$('#page-title').textContent={overview:'Eye health check',history:'Your measurement history',settings:'Make sense of the change',countermeasures:'Countermeasures & response'}[button.dataset.view];};
for(const button of document.querySelectorAll('[data-eye]'))button.onclick=()=>{eye=button.dataset.eye;for(const b of document.querySelectorAll('[data-eye]')){b.classList.toggle('selected',b.dataset.eye===eye);b.setAttribute('aria-pressed',String(b.dataset.eye===eye));}render();};
for(const [id,path] of [['record-form','record'],['baseline-form','baseline'],['settings-form','settings']]) $( '#'+id).onsubmit=async event=>{event.preventDefault();const form=event.target,body=Object.fromEntries(new FormData(form));if(id==='baseline-form' && !body.R && !body.L)return notice('Enter a baseline for at least one eye.',true);body.quality=form.elements.quality?.checked === true;const submit=form.querySelector('button[type=submit],button');submit.disabled=true;try{state=await request('/api/'+path,body);if(id!=='settings-form')form.reset();if(id==='baseline-form'){closeBaseline();$('#baseline-feedback').textContent='';}if(id==='record-form'){const savedDay=Number(body.day);const newest=Math.max(...['R','L'].flatMap(e=>state.eyes[e].results.map(r=>r.flight_day)));$('#entry-feedback').textContent=savedDay<newest ? `Saved FD ${savedDay}. Overview continues to show the latest observation for each eye.` : `Saved FD ${savedDay}. Both eye statuses have been updated.`;}if(demo)state=await request('/api/demo');render();notice(id==='settings-form'?'Analysis settings updated.':'Saved. Your analysis is up to date.');}catch(error){if(id==='baseline-form')$('#baseline-feedback').textContent=error.message;notice(error.message,true);}finally{submit.disabled=demo&&id!=='settings-form';}};
$('#demo').onclick=async()=>{try{demo=true;await load();}catch(e){demo=false;notice(e.message,true);}};
$('#history-body').onclick=async event=>{const button=event.target.closest('[data-delete]');if(!button)return;const [e,day]=button.dataset.delete.split(':');if(!confirm(`Delete the ${e==='R'?'right':'left'} eye measurement for flight day ${day}? All derived values will be recalculated.`))return;try{state=await request('/api/delete',{eye:e,day:Number(day)});render();notice('Measurement deleted. Analysis recalculated.');}catch(error){notice(error.message,true);}};
$('#print').onclick=()=>window.print();
let baselinePrompted = false;
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
function openBaseline() { if (!$('#baseline-dialog').open) $('#baseline-dialog').showModal(); }
function closeBaseline() { baselinePrompted = true; $('#baseline-dialog').close(); }
function syncBaseline() {
  const missing = ['R','L'].filter(e=>state.eyes[e].baseline == null);
  $('#baseline-summary').textContent = `Preflight reference · R ${fmt(state.eyes.R.baseline)} μm / L ${fmt(state.eyes.L.baseline)} μm`;
  $('#baseline-open').textContent = missing.length ? 'Complete baseline →' : 'View baseline';
  $('#baseline-save').hidden = !missing.length || demo;
  $('#baseline-quality').hidden = !missing.length || demo;
  $('#baseline-later').hidden = !missing.length || demo;
  $('#baseline-demo').hidden = demo;
  $('#baseline-title').textContent = missing.length ? 'First, your preflight baseline.' : 'Your fixed preflight reference.';
  if (demo && $('#baseline-dialog').open) $('#baseline-dialog').close();
  if (!demo && missing.length && !baselinePrompted) { baselinePrompted = true; openBaseline(); }
}
function cmName(r) { return r.name ? `${r.kind} · ${r.name}` : r.kind; }
function responseCard(record,e) {
  const r=record.responses[e], pre=r.before, post=r.after;
  if(record.status==='Skipped')return `<div class="response-eye"><h3>${eyeName(e)}</h3><p class="muted">Session skipped · no comparison</p></div>`;
  const delta = r.change_um;
  const direction = delta == null ? 'pending' : delta < 0 ? 'decreased' : delta > 0 ? 'increased' : 'unchanged';
  const headline = delta == null ? (!pre ? 'Before scan needed' : 'Awaiting follow-up scan') : `${direction === 'decreased' ? '↓' : direction === 'increased' ? '↑' : '→'} ${fmt(Math.abs(delta))} μm ${direction}`;
  function scan(label,scan) { return `<div><span>${label}${scan ? ` · FD ${scan.flight_day}` : ''}</span><strong>${fmt(scan?.current_trt_um)} <small>μm TRT</small></strong><span>Δ baseline ${fmt(scan?.delta_trt_um,2,true)} μm</span></div>`; }
  const others=r.other_intervention_ids.map(id=>state.interventions.find(x=>x.id===id)).filter(Boolean);
  return `<div class="response-eye ${direction}"><h3>${eyeName(e)}</h3><div class="response-headline">${headline}</div><div class="scan-pair">${scan('Before',pre)}<span class="pair-arrow">→</span>${scan('After',post)}</div>${pre&&post ? `<p class="response-interval">${post.flight_day-pre.flight_day} days between scans · ${post.flight_day-record.end_day} days after session end</p>` : ''}${post ? `<span class="status-pill ${isExceeded(post)?'warn':post.delta_trt_um==null?'neutral':''}">${post.delta_trt_um==null?'No baseline comparison':isExceeded(post)?'Still above +19.4 μm':'At or below +19.4 μm'}</span>`:''}${others.length?`<p class="cointerventions">Also in this scan interval: ${others.map(x=>escapeHTML(cmName(x))).join(', ')}</p>`:''}</div>`;
}
// Static demo: countermeasures are entered into memory only. The pairing rule
// mirrors interventions.comparisons() - latest scan strictly before the start
// day, first scan strictly after the end day, same-day scans excluded.
function pairInterventions(records){
  const results = records.map(record => {
    const entry = Object.assign({}, record, {responses:{}});
    for(const eye of ['R','L']){
      const rows = state.eyes[eye].results;
      const before = rows.filter(r => r.flight_day < record.start_day);
      const after  = rows.filter(r => r.flight_day > record.end_day);
      let pre  = before.length ? before[before.length-1] : null;
      let post = after.length ? after[0] : null;
      if(record.status === 'Skipped'){ pre = post = null; }
      const change = pre && post ? post.current_trt_um - pre.current_trt_um : null;
      const others = records.filter(r => r.id !== record.id && r.status !== 'Skipped'
        && pre && post && r.start_day < post.flight_day && r.end_day > pre.flight_day).map(r => r.id);
      entry.responses[eye] = {before:pre, after:post, change_um:change, other_intervention_ids:others};
    }
    return entry;
  });
  results.sort((a,b) => b.start_day - a.start_day);
  return results;
}
function setInterventions(records){
  state.interventions = pairInterventions(records);
}
function newInterventionId(){ return 'local-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,7); }
function renderCountermeasures() {
  const records=state.interventions || [];
  $('#export-linked').hidden=demo;
  $('#cm-overview-summary').textContent=records.length ? `${records.length} logged ${records.length===1?'session':'sessions'} · ${records.filter(r=>r.status!=='Skipped'&&Object.values(r.responses).some(x=>x.change_um!=null)).length} with paired OCT results` : 'Log a session. Your next OCT scan completes the before-and-after comparison.';
  $('#cm-records').innerHTML=records.length ? records.map(r=>`<article class="card cm-record"><div class="cm-record-heading"><div><span class="section-kicker">FD ${r.start_day}${r.end_day!==r.start_day?'–'+r.end_day:''}</span><h2>${escapeHTML(cmName(r))}</h2></div><span class="status-pill ${r.status==='Stopped early'?'warn':r.status==='Skipped'?'neutral':''}">${escapeHTML(r.status)}</span></div><p class="cm-record-details">${r.duration_minutes!=null?`${r.duration_minutes} min · `:''}${escapeHTML(r.details || 'No parameters recorded')}</p>${r.notes?`<p class="cm-note">${escapeHTML(r.notes)}</p>`:''}<div class="response-grid">${responseCard(r,'R')}${responseCard(r,'L')}</div>${true?`<div class="cm-record-actions"><button class="text-button" data-cm-edit="${escapeHTML(r.id)}">Edit record</button><button class="text-button delete-button" data-cm-delete="${escapeHTML(r.id)}">Delete</button></div>`:''}</article>`).join('') : '<div class="card empty"><h2>Your first session starts the log.</h2><p>Record what you used and when.<br>Before-and-after TRT values appear here as scans become available.</p></div>';
}
function configureCountermeasure() {
  const kind=$('#cm-kind').value, named=['Medication','Supplement','Other'].includes(kind);
  $('#cm-name-label').hidden=!named;
  $('#cm-form').elements.name.required=named;
  $('#cm-duration-label').hidden=['Medication','Supplement'].includes(kind);
  $('#cm-detail-title').textContent=['Medication','Supplement'].includes(kind)?'Actual dose & frequency':'Actual device settings';
  $('#cm-form').elements.details.placeholder=['Medication','Supplement'].includes(kind)?'Amount, unit and frequency used':'Parameter and unit, if recorded';
}
$('#cm-kind').onchange=configureCountermeasure;
$('#cm-form').onsubmit=async event=>{
  event.preventDefault();
  const form=event.target,body=Object.fromEntries(new FormData(form)),button=form.querySelector('[type=submit]');
  if(body.end_day==='')body.end_day=body.start_day;
  if(['Medication','Supplement'].includes(body.kind))body.duration_minutes='';
  button.disabled=true;
  try{
    if(demo){
      const record={id: body.id || newInterventionId(), kind:body.kind,
        name: body.name || '', start_day:Number(body.start_day), end_day:Number(body.end_day),
        duration_minutes: body.duration_minutes==='' || body.duration_minutes==null ? null : Number(body.duration_minutes),
        details: body.details || '', status: body.status, notes: body.notes || ''};
      const list=(state.interventions || []).filter(r => r.id !== record.id);
      list.push(record);
      setInterventions(list);
      form.reset();$('#cm-form-title').textContent='Record a countermeasure';$('#cm-cancel').hidden=true;
      configureCountermeasure();render();
      $('#cm-feedback').textContent='Added to this session. Reloading clears it.';
    } else {
      state=await request('/api/intervention',body);
      form.reset();$('#cm-form-title').textContent='Record a countermeasure';$('#cm-cancel').hidden=true;
      configureCountermeasure();render();
      $('#cm-feedback').textContent='Saved. Scan comparisons updated.';
    }
  }
  catch(error){$('#cm-feedback').textContent=error.message;notice(error.message,true);}
  finally{button.disabled=false;}
};
$('#cm-cancel').onclick=()=>{$('#cm-form').reset();$('#cm-cancel').hidden=true;$('#cm-form-title').textContent='Record a countermeasure';$('#cm-feedback').textContent='';configureCountermeasure();};
$('#cm-records').onclick=async event=>{
  const edit=event.target.closest('[data-cm-edit]'),del=event.target.closest('[data-cm-delete]');
  if(edit){const r=state.interventions.find(x=>x.id===edit.dataset.cmEdit);if(!r)return;for(const key of ['id','kind','name','start_day','end_day','duration_minutes','details','status','notes'])$('#cm-form').elements[key].value=r[key]??'';configureCountermeasure();$('#cm-cancel').hidden=false;$('#cm-form-title').textContent='Edit countermeasure';$('#cm-feedback').textContent='';$('#cm-form').elements.kind.focus();$('#cm-form').scrollIntoView({behavior:'smooth',block:'start'});}
  if(del&&confirm('Delete this countermeasure record?')){
    try{
      if(demo){
        setInterventions((state.interventions || []).filter(r => r.id !== del.dataset.cmDelete));
        if($('#cm-form').elements.id.value===del.dataset.cmDelete)$('#cm-cancel').click();
        render();notice('Removed from this session.');
      } else {
        state=await request('/api/intervention-delete',{id:del.dataset.cmDelete});
        if($('#cm-form').elements.id.value===del.dataset.cmDelete)$('#cm-cancel').click();
        render();notice('Countermeasure deleted.');
      }
    }catch(error){notice(error.message,true);}
  }
};
$('#baseline-open').onclick=openBaseline;
$('#baseline-close').onclick=closeBaseline;
$('#baseline-later').onclick=closeBaseline;
$('#baseline-dialog').addEventListener('cancel',()=>{baselinePrompted=true;});
$('#baseline-demo').onclick=()=>{$('#baseline-dialog').close();$('#demo').click();};
configureCountermeasure();

load().catch(e=>{notice('Could not load your data. '+e.message,true);$('#mission-status').className='mission-status unknown';$('#mission-status').innerHTML='<div><h2>Eye status unavailable</h2><p>Could not load saved measurements. Check the local server and reload this page.</p></div>';});
