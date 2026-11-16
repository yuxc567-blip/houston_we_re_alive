'use strict';
const $ = selector => document.querySelector(selector);
let state = null;
let savingSleep = false;
const trial = {mode:null,phase:'idle',samples:[],early:0,timeouts:0,timer:null,frame:null,started:null,day:null,payload:null};
const fmt = (n, digits=1, signed=false) => n == null ? '—' : `${signed && n>0 ? '+' : ''}${Number(n).toFixed(digits)}`;
function notice(text,error=false){$('#notice').textContent=text;$('#notice').classList.toggle('error',error);}
async function request(path, body){
  const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||'The request could not be completed.');
  return result;
}
function drawChart(element, records, xKey, yKey, reference, unit){
  if(!records.length){element.classList.add('empty');element.textContent='Your next observation starts the chart.';return;}
  element.classList.remove('empty');
  const W=560,H=170,L=42,R=20,T=18,B=30;
  const xs=records.map(r=>r[xKey]),ys=records.map(r=>r[yKey]);
  const minX=Math.min(...xs),maxX=Math.max(...xs),values=[...ys,reference];
  const lo=Math.min(...values),hi=Math.max(...values),padding=Math.max((hi-lo)*.2,unit==='h'?.5:10),minY=lo-padding,maxY=hi+padding;
  const x=v=>L+(maxX===minX?(W-L-R)/2:(v-minX)/(maxX-minX)*(W-L-R));
  const y=v=>T+(maxY-v)/(maxY-minY)*(H-T-B);
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${unit==='h'?'Sleep hours':'Reaction time in milliseconds'} by actual mission day"><line x1="${L}" x2="${W-R}" y1="${y(reference)}" y2="${y(reference)}" stroke="#9aaea0" stroke-dasharray="4 4"/><text x="${W-R}" y="${y(reference)-5}" text-anchor="end" fill="#687e70" font-size="9">reference ${fmt(reference)} ${unit}</text>`;
  for(const v of [lo,hi])svg+=`<text x="${L-7}" y="${y(v)+3}" text-anchor="end" fill="#687e70" font-size="10">${fmt(v)}</text>`;
  svg+=`<polyline points="${records.map(r=>`${x(r[xKey])},${y(r[yKey])}`).join(' ')}" fill="none" stroke="#136a5c" stroke-width="2.3"/>`;
  for(const r of records)svg+=`<circle cx="${x(r[xKey])}" cy="${y(r[yKey])}" r="3.5" fill="#136a5c"><title>Day ${r[xKey]}: ${fmt(r[yKey])} ${unit}</title></circle>`;
  const labels=xs.length<=10?xs:[minX,maxX];
  for(const d of labels)svg+=`<text x="${x(d)}" y="${H-7}" text-anchor="middle" fill="#687e70" font-size="10">FD ${d}</text>`;
  element.innerHTML=svg+'</svg>';
}
function render(){
  $('#sleep-form button[type=submit]').disabled=savingSleep;
  $('#export').disabled=false;
  const data=state.data,sleep=state.sleep_analysis?.records||[],reaction=state.reaction_analysis;
  const latest=sleep.at(-1),last=reaction.at(-1),baseline=data.reaction_baseline;
  $('#reference-latest').innerHTML=`${fmt(data.baseline_hours,1)} <small>h</small>`;
  $('#sleep-latest').innerHTML=latest?`${fmt(latest.sleep_hours)} <small>h</small>`:'—';
  $('#sleep-context').textContent=latest?`FD ${latest.mission_day} · ${fmt(latest.deviation_hours,1,true)} h from reference`:'Add your first observation';
  $('#reaction-latest').innerHTML=last?`${fmt(last.reaction_time_ms,0)} <small>ms</small>`:'—';
  $('#reaction-context').textContent=last?`FD ${last.mission_day} · ${fmt(last.deviation_percent,1,true)}% from baseline`:baseline?'Baseline ready. Take your first daily test.':'Measure a personal baseline first';
  $('#sleep-reference').value=data.baseline_hours;
  $('#sleep-reference').disabled=!!sleep.length;
  $('#sleep-form').elements.day.value=latest?latest.mission_day+1:1;
  if(trial.mode===null)$('#reaction-day').value=last?last.mission_day+1:1;
  $('#baseline-summary').textContent=baseline?`Browser baseline: ${fmt(baseline.mean_ms)} ms mean · ${fmt(baseline.median_ms)} ms median · five valid trials. Keep the same device and input method.`:'Measure your browser baseline first. Native-app and browser baselines are kept separate because timing can differ.';
  $('#baseline-start').disabled=!!baseline||trial.mode!==null;
  $('#session-start').disabled=!baseline||trial.mode!==null;
  $('#reaction-day').disabled=trial.mode!==null;
  $('#sleep-rows').innerHTML=sleep.length?sleep.map(r=>`<tr><td>FD ${r.mission_day}</td><td>${fmt(r.sleep_hours)}</td><td>${fmt(r.deviation_hours,1,true)}</td><td>${fmt(r.deviation_percent,2,true)}</td><td>${fmt(r.error_rate_per_day==null?null:r.error_rate_per_day*100,2,true)}</td><td>${fmt(r.accumulated_relative_error_days,3,true)}</td></tr>`).join(''):'<tr><td colspan="6">No observations yet. Add your first sleep entry above.</td></tr>';
  $('#reaction-rows').innerHTML=reaction.length?reaction.map((r,i)=>`<tr><td>FD ${r.mission_day}</td><td>${fmt(r.reaction_time_ms)}</td><td>${fmt(r.deviation,1,true)}</td><td>${fmt(r.deviation_percent,2,true)}</td><td>${fmt(r.error_rate==null?null:r.error_rate*100,2,true)}</td><td>${fmt(r.accumulated_error,3,true)}</td><td>${data.reaction_sessions[i].early_clicks} / ${data.reaction_sessions[i].timeouts}</td></tr>`).join(''):'<tr><td colspan="7">No daily tests yet. Measure a baseline, then test a mission day.</td></tr>';
  drawChart($('#sleep-chart'),sleep,'mission_day','sleep_hours',data.baseline_hours,'h');
  drawChart($('#reaction-chart'),reaction,'mission_day','reaction_time_ms',baseline?.mean_ms||0,'ms');
}
$('#sleep-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!state)return;
  const form=event.currentTarget,button=form.querySelector('button[type=submit]');button.disabled=true;savingSleep=true;
  try{state=await request('/api/sleep',{day:Number(form.elements.day.value),hours:Number(form.elements.hours.value),baseline_hours:Number($('#sleep-reference').value)});form.elements.hours.value='';render();notice('Sleep observation saved. Your history and analysis are up to date.');}
  catch(error){notice(error.message,true);}finally{savingSleep=false;button.disabled=false;}
});
function target(text,sub,phase='idle'){
  const element=$('#target');element.className='target '+phase;
  element.replaceChildren(document.createTextNode(text));const caption=document.createElement('span');caption.textContent=sub;element.append(caption);
}
function clearTimers(){clearTimeout(trial.timer);cancelAnimationFrame(trial.frame);trial.timer=trial.frame=null;}
function progress(){
  $('#trial-progress').value=trial.samples.length;
  $('#trial-counter').textContent=`${trial.samples.length} / 5 valid`;
}
function begin(mode){
  if(!state||trial.mode!==null)return;
  const day=Number($('#reaction-day').value);
  if(mode==='session'&&(!Number.isInteger(day)||day<1||state.data.reaction_sessions.some(r=>r.day===day))){notice('Choose a positive mission day without an existing reaction test.',true);return;}
  if(mode==='baseline'&&state.data.reaction_baseline)return;
  Object.assign(trial,{mode,phase:'idle',samples:[],early:0,timeouts:0,started:null,day,payload:null});
  $('#cancel-test').disabled=false;$('#retry-save').hidden=true;progress();render();nextTrial();
}
function nextTrial(){
  if(trial.mode===null||!['idle','between'].includes(trial.phase))return;
  clearTimers();trial.phase='waiting';$('#next-trial').disabled=true;
  target('Wait for green…','DO NOT RESPOND YET','waiting');
  $('#trial-status').textContent=`Trial ${trial.samples.length+1} of 5 · Early clicks ${trial.early} · Timeouts ${trial.timeouts}`;
  const random=new Uint32Array(1);crypto.getRandomValues(random);
  trial.timer=setTimeout(()=>{
    trial.frame=requestAnimationFrame(()=>{
      if(trial.phase!=='waiting')return;
      target('Respond now','CLICK · TAP · SPACE','ready');
      trial.started=performance.now();trial.phase='ready';
      trial.timer=setTimeout(()=>{
        if(trial.phase!=='ready')return;
        trial.timeouts++;trial.phase='between';target('No response recorded','TIMEOUT — NOT COUNTED');
        $('#trial-status').textContent='The five-second response window expired. Choose Next trial. This timeout is not a clinical lapse threshold.';
        $('#next-trial').disabled=false;
      },5000);
    });
  },1500+(random[0]/4294967296)*2000);
  $('#target').focus({preventScroll:true});
}
function respond(){
  const now=performance.now();
  if(trial.phase==='waiting'){
    clearTimers();trial.early++;trial.phase='between';target('A little too early','THIS CLICK WAS NOT COUNTED','waiting');
    $('#trial-status').textContent='Wait until the button is green. Choose Next trial to try again.';$('#next-trial').disabled=false;return;
  }
  if(trial.phase!=='ready')return;
  const elapsed=now-trial.started;clearTimers();trial.phase='between';
  if(elapsed<=0||elapsed>5000){trial.timeouts++;target('Trial not counted','PLEASE TRY AGAIN');$('#next-trial').disabled=false;return;}
  trial.samples.push(elapsed);progress();target(`${fmt(elapsed)} ms`,'RESPONSE RECORDED');
  if(trial.samples.length===5){trial.payload={mode:trial.mode,day:trial.day,trials_ms:[...trial.samples],early_clicks:trial.early,timeouts:trial.timeouts};saveTest();}
  else{$('#trial-status').textContent=`${trial.samples.length} valid trials. Choose Next trial when ready.`;$('#next-trial').disabled=false;}
}
async function saveTest(){
  if(!trial.payload||trial.phase==='saving')return;
  trial.phase='saving';$('#retry-save').hidden=true;$('#cancel-test').disabled=true;
  $('#trial-status').textContent='Saving five valid trials to your local journal…';
  try{
    state=await request('/api/reaction',trial.payload);
    const record=trial.mode==='baseline'?state.data.reaction_baseline:state.data.reaction_sessions.find(r=>r.day===trial.day);
    $('#trial-status').textContent=`Saved · Mean ${fmt(record.mean_ms)} ms · Median ${fmt(record.median_ms)} ms · Early clicks ${record.early_clicks} · Timeouts ${record.timeouts}`;
    trial.mode=null;trial.phase='idle';trial.payload=null;render();notice('Reaction-time results saved locally.');
  }catch(error){trial.phase='save-error';$('#retry-save').hidden=false;$('#cancel-test').disabled=false;notice(`Results are not saved yet. ${error.message} Retry saving or cancel the test.`,true);}
}
function cancelTest(reason='Test cancelled. Partial trials were not saved.'){
  if(trial.mode===null||trial.phase==='saving')return;
  clearTimers();Object.assign(trial,{mode:null,phase:'idle',samples:[],payload:null});
  target('Choose a test above','WAIT FOR THE SIGNAL');progress();$('#trial-status').textContent=reason;
  $('#next-trial').disabled=true;$('#cancel-test').disabled=true;$('#retry-save').hidden=true;render();
}
$('#baseline-start').onclick=()=>begin('baseline');$('#session-start').onclick=()=>begin('session');
$('#next-trial').onclick=nextTrial;$('#cancel-test').onclick=()=>cancelTest();$('#retry-save').onclick=saveTest;
$('#target').addEventListener('pointerdown',event=>{if(event.isPrimary&&event.button===0){event.preventDefault();respond();}});
$('#target').addEventListener('keydown',event=>{if([' ','Enter'].includes(event.key)){event.preventDefault();if(!event.repeat)respond();}});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&['waiting','ready','between'].includes(trial.phase))cancelTest('Test cancelled because the page was hidden. Restart when you can stay on this page.');});
window.addEventListener('blur',()=>{if(['waiting','ready','between'].includes(trial.phase))cancelTest('Test cancelled because the window lost focus. Partial trials were not saved.');});
for(const type of ['sleep','reaction'])$('#'+type+'-tab').onclick=()=>{
  for(const other of ['sleep','reaction']){$('#'+other+'-tab').setAttribute('aria-selected',String(type===other));$('#'+other+'-history').hidden=type!==other;}
};
$('#export').onclick=async()=>{
  try{const data=await request('/api/export'),url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='rest-response-journal.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  catch(error){notice(error.message,true);}
};
request('/api/state').then(result=>{state=result;render();}).catch(error=>{
  notice('Cannot connect to the local Python server. Run python sleep/dashboard.py and open http://127.0.0.1:8010. '+error.message,true);
  for(const button of document.querySelectorAll('button'))button.disabled=true;
});
