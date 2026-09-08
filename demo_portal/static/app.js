const state = {
  bootstrap: null,
  currentView: 'story',
  storyStep: 0,
  storyResults: {},
  agent: 'customer',
  chats: { customer: [], exception: [] },
  sessions: {
    customer: `portal-customer-${Date.now()}`,
    exception: `portal-exception-${Date.now()}`,
    storyCustomer: `story-customer-${Date.now()}`,
    storyException: `story-exception-${Date.now()}`,
  },
  mockSection: 'scenario',
  mockRaw: false,
};

const storySteps = [
  {
    title: 'Customer detects the risk',
    subtitle: 'Customer Experience Agent',
    source: 'ai',
    description: 'Start with the customer-facing question. The agent grounds its answer in shipment, order, customer, and SLA data.',
    prompt: 'Atlas Medical is calling about order ORD-ATL-1007. Where is it, what happened, and are we still meeting the promised delivery?',
    actionLabel: 'Ask Customer Experience',
    run: () => api('/api/agents/customer/chat', { method:'POST', body:{ message: storySteps[0].prompt, session_id: state.sessions.storyCustomer } }),
  },
  {
    title: 'See the network-wide impact',
    subtitle: 'Network Control Tower',
    source: 'ai',
    description: 'Move from one customer to the whole disruption. The Control Tower ranks exposure and recommends where recovery spend creates value.',
    prompt: 'Analyze DISR-GRU-0908 with the governed LLM and generate the leadership brief.',
    actionLabel: 'Run Control Tower analysis',
    run: () => api('/api/agents/control-tower/analyze', { method:'POST', body:{ disruption_id:'DISR-GRU-0908', use_llm:true } }),
  },
  {
    title: 'Evaluate recovery options',
    subtitle: 'Shipment Exception Manager',
    source: 'ai',
    description: 'The operations agent compares every option, cost, ETA, risk, and SLA impact—but it is explicitly told not to execute.',
    prompt: 'Investigate BRX-784512. Explain the exception, compare every available recovery option, and recommend what operations should do. Do not execute anything yet.',
    actionLabel: 'Ask Exception Manager',
    run: () => api('/api/agents/exception/chat', { method:'POST', body:{ message: storySteps[2].prompt, session_id: state.sessions.storyException } }),
  },
  {
    title: 'Human approves execution',
    subtitle: 'Human-in-the-loop control',
    source: 'human',
    description: 'Execution is gated. The UI makes the approval explicit and records an approver and reference before asking the agent to act.',
    prompt: 'Approved. Execute REC-ATL-VCP for BRX-784512. Approved by Ana Ribeiro, approval reference APPROVED-GRU-0908-01.',
    actionLabel: 'Review approval',
    requiresApproval: true,
    run: () => api('/api/agents/exception/chat', { method:'POST', body:{ message: storySteps[3].prompt, session_id: state.sessions.storyException } }),
  },
  {
    title: 'Customer sees shared-state change',
    subtitle: 'Customer Experience Agent',
    source: 'ai',
    description: 'Return to the original customer agent. It is not told what Operations did—it independently reads the same shared Logistics Core and sees the new ETA.',
    prompt: 'Give me the latest status for BRX-784512. Did anything change since we first checked it?',
    actionLabel: 'Refresh customer status',
    run: () => api('/api/agents/customer/chat', { method:'POST', body:{ message: storySteps[4].prompt, session_id: state.sessions.storyCustomer } }),
  },
  {
    title: 'Close the communication loop',
    subtitle: 'Customer Experience Agent',
    source: 'ai',
    description: 'Queue proactive communication with the revised recovery plan and ETA, completing the customer/operations loop.',
    prompt: 'Queue a proactive notification to Marina Costa explaining that recovery has been booked and the revised ETA is Sep 8 at 21:40 BRT.',
    actionLabel: 'Queue customer notification',
    run: () => api('/api/agents/customer/chat', { method:'POST', body:{ message: storySteps[5].prompt, session_id: state.sessions.storyCustomer } }),
  },
];

const mockSections = [
  ['scenario','Scenario','Fixed identifiers & demo clock'],
  ['customers','Customers','Customer tiers, contacts & SLA profiles'],
  ['orders','Orders','Contents, commitments & criticality'],
  ['shipments','Shipments','Current state and routing'],
  ['tracking_events','Tracking events','Deterministic shipment history'],
  ['disruptions','Disruptions','Network disruption definitions'],
  ['recovery_options','Recovery options','Cost / ETA alternatives'],
  ['incidents','Incidents','Operational exception records'],
  ['facilities','Facilities','Mock network locations'],
  ['mutable_state','Mutable state','Cases, notifications & executed recoveries'],
];

const agentConfig = {
  customer: {
    label:'Customer Experience',
    description:'Customer-facing shipment status, SLA context, cases and proactive notifications.',
    endpoint:'/api/agents/customer/chat',
    prompts:[
      'Atlas Medical is calling about order ORD-ATL-1007. Where is it, what happened, and are we still meeting the promised delivery?',
      "What does this customer's SLA profile require us to do now?",
      'What is the status of BRX-784566?',
    ],
  },
  exception: {
    label:'Shipment Exception Manager',
    description:'Operations investigation, recovery trade-offs, and approval-controlled execution.',
    endpoint:'/api/agents/exception/chat',
    prompts:[
      'Investigate BRX-784512. Compare every recovery option and recommend what operations should do. Do not execute anything yet.',
      'Why is spending BRL 1,850 justified for this shipment?',
      'What approval is required before executing REC-ATL-VCP?',
    ],
  },
};

async function api(path, options={}) {
  const init = { headers:{'Content-Type':'application/json'}, ...options };
  if (init.body && typeof init.body !== 'string') init.body = JSON.stringify(init.body);
  const response = await fetch(path, init);
  let data = null;
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
  return data;
}

function escapeHtml(text='') { return String(text).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

function markdown(text='') {
  let safe = escapeHtml(text).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  const lines = safe.split(/\n/);
  let html = '', inUl=false, inOl=false;
  const closeLists = () => { if(inUl){html+='</ul>';inUl=false;} if(inOl){html+='</ol>';inOl=false;} };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { closeLists(); continue; }
    if (/^###\s/.test(line)) { closeLists(); html += `<h3>${line.replace(/^###\s/,'')}</h3>`; }
    else if (/^##\s/.test(line)) { closeLists(); html += `<h2>${line.replace(/^##\s/,'')}</h2>`; }
    else if (/^#\s/.test(line)) { closeLists(); html += `<h1>${line.replace(/^#\s/,'')}</h1>`; }
    else if (/^[-*]\s+/.test(line)) { if(inOl){html+='</ol>';inOl=false;} if(!inUl){html+='<ul>';inUl=true;} html += `<li>${line.replace(/^[-*]\s+/,'')}</li>`; }
    else if (/^\d+\.\s+/.test(line)) { if(inUl){html+='</ul>';inUl=false;} if(!inOl){html+='<ol>';inOl=true;} html += `<li>${line.replace(/^\d+\.\s+/,'')}</li>`; }
    else { closeLists(); html += `<p>${line}</p>`; }
  }
  closeLists(); return html;
}

function fmtMoney(v) { return `BRL ${Number(v||0).toLocaleString('en-US',{maximumFractionDigits:0})}`; }
function fmtDate(v) { if(!v) return '—'; try { return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'America/Sao_Paulo'}).format(new Date(v)); } catch { return v; } }
function mins(v) { const h=Math.floor(v/60), m=v%60; return h ? `${h}h${m?String(m).padStart(2,'0'):''}` : `${m}m`; }
function getCatalog() { return state.bootstrap?.catalog?.data || state.bootstrap?.catalog || {}; }

function toast(message, type='') { const box=document.createElement('div'); box.className=`toast ${type}`; box.textContent=message; document.querySelector('#toast-container').append(box); setTimeout(()=>box.remove(),4200); }
function banner(message) { const el=document.querySelector('#global-banner'); if(!message){el.classList.add('hidden');el.textContent='';return;} el.textContent=message; el.classList.remove('hidden'); }

async function loadBootstrap(showToast=false) {
  try {
    banner('');
    const data = await api('/api/bootstrap');
    state.bootstrap = data;
    renderOverview(); renderTower(); renderAgentStatuses(); renderMock();
    if(showToast) toast('Live demo state refreshed');
  } catch (e) { banner(`Could not load the demo state: ${e.message}`); }
}

function renderAgentStatuses() {
  const health=state.bootstrap?.health||{};
  const defs=[['core','Logistics Core','Shared deterministic state'],['customer','Customer Experience','Chat Agent'],['exception','Exception Manager','Chat Agent'],['control_tower','Network Control Tower','Custom API Agent']];
  document.querySelector('#agent-status-list').innerHTML=defs.map(([key,name,sub])=>{
    const ok=health[key]?.ok; return `<div class="agent-status"><span class="status-dot ${ok?'ok':'warning'}"></span><div><strong>${name}</strong><small>${sub}</small></div><small>${ok?'Healthy':'Unavailable'}</small></div>`;
  }).join('');
}

function renderOverview() {
  const disruption=state.bootstrap?.disruption||{};
  const impact=state.bootstrap?.impact?.impacted_shipments||[];
  const scenario=state.bootstrap?.scenario||{};
  document.querySelector('#demo-clock').textContent=`Demo time ${fmtDate(scenario.demo_now)}`;
  document.querySelector('#disruption-description').textContent=disruption.description || 'Severe convective weather and ramp restrictions reduced cargo processing at GRU.';
  document.querySelector('#kpi-impacted').textContent=impact.length || '—';
  document.querySelector('#kpi-risk').textContent=impact.filter(x=>x.sla?.sla_at_risk).length || '0';
  document.querySelector('#kpi-spend').textContent=fmtMoney(impact.reduce((a,x)=>a+Number(x.recommended_recovery?.incremental_cost_brl||0),0));
  document.querySelector('#kpi-p1').textContent=impact.find(x=>x.priority==='P1')?.tracking_number || '—';
  renderStory();
}

function renderStory() {
  const rail=document.querySelector('#story-rail');
  rail.innerHTML=storySteps.map((s,i)=>`<button class="story-step ${i===state.storyStep?'active':''} ${state.storyResults[i]?'done':''}" data-story-step="${i}"><span class="step-no">${state.storyResults[i]?'✓':i+1}</span><span class="step-copy"><strong>${s.title}</strong><small>${s.subtitle}</small></span><span class="step-state"></span></button>`).join('');
  rail.querySelectorAll('[data-story-step]').forEach(b=>b.onclick=()=>{state.storyStep=Number(b.dataset.storyStep);renderStory();});
  const s=storySteps[state.storyStep], result=state.storyResults[state.storyStep];
  const sourceLabel=s.source==='human'?'<span class="source-badge human">HUMAN CONTROL</span>':'<span class="source-badge ai">AI AGENT</span>';
  document.querySelector('#story-stage').innerHTML=`
    <div class="stage-header"><div>${sourceLabel}<h2>Act ${state.storyStep+1} — ${s.title}</h2><p>${s.description}</p></div><button class="btn primary" id="run-story-step">${result?'Run again':s.actionLabel}</button></div>
    <div class="stage-body"><div class="prompt-card"><div class="prompt-label">REQUEST</div><div class="prompt-text">${escapeHtml(s.prompt)}</div></div>
      <div class="output-card"><div class="output-head"><span>${escapeHtml(s.subtitle)}</span>${s.source==='human'?'<span class="source-badge human">APPROVAL GATE</span>':'<span class="source-badge ai">LIVE AGENT RESPONSE</span>'}</div><div class="output-body rich-output" id="story-output">${result?renderResult(result):'<div class="empty-state">Run this act to see the live response.</div>'}</div></div>
    </div>`;
  document.querySelector('#run-story-step').onclick=()=>runStoryStep(state.storyStep);
}

function renderResult(result) {
  if(result.response) return markdown(result.response);
  if(result.summary) return markdown(result.summary);
  return `<pre class="json-view" style="min-height:0;border-radius:8px">${escapeHtml(JSON.stringify(result,null,2))}</pre>`;
}

async function runStoryStep(index, approved=false) {
  const s=storySteps[index];
  if(s.requiresApproval && !approved) { document.querySelector('#approval-modal').classList.remove('hidden'); return; }
  const out=document.querySelector('#story-output'); out.innerHTML='<div class="loading">Calling deployed agent…</div>';
  try {
    const result=await s.run(); state.storyResults[index]=result; renderStory(); await loadBootstrap(false);
    if(index<storySteps.length-1){ state.storyStep=index+1; renderStory(); }
    toast(`Act ${index+1} completed`);
  } catch(e) { out.innerHTML=`<div class="global-banner">${escapeHtml(e.message)}</div>`; toast(e.message,'error'); }
}

function renderTower() {
  const impact=state.bootstrap?.impact?.impacted_shipments||[];
  document.querySelector('#impact-table').innerHTML=impact.map(row=>`<tr><td><span class="priority ${row.priority}">${row.priority}</span><div class="muted" style="margin-top:5px;font-size:10px">Score ${row.priority_score}</div></td><td><strong class="mono" style="font-size:12px">${row.tracking_number}</strong><div class="muted" style="font-size:10px;margin-top:4px">${row.service_level}</div></td><td><strong>${row.customer}</strong><div class="muted" style="font-size:10px;margin-top:4px">${row.order_id}</div></td><td>${row.sla?.sla_at_risk?`<strong style="color:#a6222d">${mins(row.sla.projected_delay_minutes)} late</strong>`:`<strong style="color:#18794e">${mins(row.sla.delivery_buffer_minutes)} buffer</strong>`}<div class="muted" style="font-size:10px;margin-top:4px">ETA ${fmtDate(row.sla?.estimated_delivery)}</div></td><td><strong>${row.recommended_recovery?.option_id||'—'}</strong><div class="muted" style="font-size:10px;margin-top:4px;max-width:280px">${row.recommended_recovery?.description||''}</div></td><td><strong>${fmtMoney(row.recommended_recovery?.incremental_cost_brl)}</strong></td></tr>`).join('') || '<tr><td colspan="6">No impact data available.</td></tr>';
}

async function analyzeTower() {
  const el=document.querySelector('#tower-summary'); el.innerHTML='<div class="loading">Generating leadership brief…</div>';
  try { const result=await api('/api/agents/control-tower/analyze',{method:'POST',body:{disruption_id:'DISR-GRU-0908',use_llm:true}}); el.innerHTML=markdown(result.summary||JSON.stringify(result)); toast('Control Tower analysis complete'); }
  catch(e){ el.innerHTML=`<div class="global-banner">${escapeHtml(e.message)}</div>`; }
}

function renderAgentWorkbench() {
  const cfg=agentConfig[state.agent];
  document.querySelector('#chat-context').innerHTML=`<strong>${cfg.label}</strong> · ${cfg.description}`;
  document.querySelectorAll('.agent-tab').forEach(b=>b.classList.toggle('active',b.dataset.agent===state.agent));
  const messages=state.chats[state.agent];
  document.querySelector('#chat-messages').innerHTML=messages.length?messages.map(m=>`<div class="chat-message ${m.role}"><div class="chat-bubble ${m.role==='agent'?'rich-output':''}">${m.role==='agent'?markdown(m.text):escapeHtml(m.text)}</div></div>`).join(''):'<div class="empty-state">Choose a suggested prompt or start a conversation.</div>';
  document.querySelector('#prompt-chips').innerHTML=cfg.prompts.map(p=>`<button class="chip" data-prompt="${encodeURIComponent(p)}">${escapeHtml(p.length>65?p.slice(0,62)+'…':p)}</button>`).join('');
  document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>sendChat(decodeURIComponent(b.dataset.prompt)));
  const box=document.querySelector('#chat-messages'); box.scrollTop=box.scrollHeight;
}

async function sendChat(message) {
  if(!message.trim()) return;
  const cfg=agentConfig[state.agent], agent=state.agent;
  state.chats[agent].push({role:'user',text:message}); renderAgentWorkbench();
  state.chats[agent].push({role:'agent',text:'__loading__'}); renderAgentWorkbench();
  const bubbles=document.querySelectorAll('#chat-messages .chat-message.agent .chat-bubble'); bubbles[bubbles.length-1].innerHTML='<div class="loading">Agent is reasoning…</div>';
  try { const result=await api(cfg.endpoint,{method:'POST',body:{message,session_id:state.sessions[agent]}}); state.chats[agent][state.chats[agent].length-1]={role:'agent',text:result.response||JSON.stringify(result)}; }
  catch(e){ state.chats[agent][state.chats[agent].length-1]={role:'agent',text:`Error: ${e.message}`}; }
  renderAgentWorkbench(); document.querySelector('#chat-input').value='';
}

function renderMock() {
  const nav=document.querySelector('#mock-nav');
  nav.innerHTML=mockSections.map(([key,title])=>`<button class="mock-nav-item ${state.mockSection===key?'active':''}" data-mock="${key}">${title}</button>`).join('');
  nav.querySelectorAll('[data-mock]').forEach(b=>b.onclick=()=>{state.mockSection=b.dataset.mock;state.mockRaw=false;renderMock();});
  const meta=mockSections.find(x=>x[0]===state.mockSection); document.querySelector('#mock-title').textContent=meta?.[1]||state.mockSection; document.querySelector('#mock-subtitle').textContent=meta?.[2]||'';
  document.querySelector('#raw-toggle').textContent=state.mockRaw?'Readable view':'Raw JSON';
  const data=mockDataForSection(state.mockSection); const query=(document.querySelector('#mock-search')?.value||'').toLowerCase();
  const json=JSON.stringify(data,null,2); document.querySelector('#mock-json').textContent=json; document.querySelector('#mock-json').classList.toggle('hidden',!state.mockRaw); document.querySelector('#mock-readable').classList.toggle('hidden',state.mockRaw);
  document.querySelector('#mock-readable').innerHTML=renderReadable(data,query);
}

function mockDataForSection(section) {
  const catalog=getCatalog();
  if(section==='scenario') return catalog.scenario || state.bootstrap?.scenario || {};
  if(section==='mutable_state') return state.bootstrap?.mutable_state || catalog.mutable_state || {};
  return catalog[section] || {};
}

function renderReadable(data,query='') {
  const values=Array.isArray(data)?data:(data && typeof data==='object'?Object.entries(data).map(([key,value])=>typeof value==='object'&&value!==null?{__key:key,...value}:{__key:key,value}):[data]);
  return values.filter(v=>!query||JSON.stringify(v).toLowerCase().includes(query)).map((v,i)=>{
    if(typeof v!=='object'||v===null) return `<div class="data-card"><strong>${escapeHtml(String(v))}</strong></div>`;
    const title=v.name||v.customer_id||v.order_id||v.tracking_number||v.disruption_id||v.option_id||v.incident_id||v.__key||`Record ${i+1}`;
    const desc=v.description||v.exception_description||v.contents||v.notes||v.scenario||v.type||'';
    const fields=Object.entries(v).filter(([k,val])=>k!=='__key'&&typeof val!=='object').slice(0,9);
    return `<div class="data-card"><div class="data-card-head"><div><h4>${escapeHtml(title)}</h4><p>${escapeHtml(desc)}</p></div><span class="source-badge mock">MOCK</span></div><div class="data-grid">${fields.map(([k,val])=>`<div class="data-field"><span>${escapeHtml(k.replaceAll('_',' '))}</span><strong>${escapeHtml(String(val??'—'))}</strong></div>`).join('')}</div></div>`;
  }).join('') || '<div class="empty-state">No matching records.</div>';
}

async function resetDemo() {
  if(!confirm('Reset all mutable demo state? Cases, notifications and executed recoveries will be cleared.')) return;
  try { await api('/api/story/reset',{method:'POST'}); state.storyResults={}; state.storyStep=0; state.chats={customer:[],exception:[]}; state.sessions={customer:`portal-customer-${Date.now()}`,exception:`portal-exception-${Date.now()}`,storyCustomer:`story-customer-${Date.now()}`,storyException:`story-exception-${Date.now()}`}; await loadBootstrap(false); toast('Demo state reset'); }
  catch(e){ toast(e.message,'error'); }
}

function switchView(view) {
  state.currentView=view; document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===view)); document.querySelectorAll('.view').forEach(v=>v.classList.remove('active')); document.querySelector(`#view-${view}`).classList.add('active');
  const titles={story:['Guided disruption story','GRU Weather Disruption'],tower:['Network intelligence','Control Tower'],agents:['Agent workbench','Deployed AI Agents'],mock:['Deterministic source of truth','Mock Data Explorer']}; document.querySelector('#page-title').textContent=titles[view][0]; document.querySelector('#header-title').textContent=titles[view][1];
  if(view==='agents') renderAgentWorkbench(); if(view==='mock') renderMock();
}

function bind() {
  document.querySelectorAll('.nav-item').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
  document.querySelectorAll('[data-view-jump]').forEach(b=>b.onclick=()=>switchView(b.dataset.viewJump));
  document.querySelector('#refresh-btn').onclick=()=>loadBootstrap(true); document.querySelector('#reset-btn').onclick=resetDemo; document.querySelector('#analyze-btn').onclick=analyzeTower;
  document.querySelectorAll('.agent-tab').forEach(b=>b.onclick=()=>{state.agent=b.dataset.agent;renderAgentWorkbench();});
  document.querySelector('#chat-form').onsubmit=e=>{e.preventDefault();sendChat(document.querySelector('#chat-input').value);};
  document.querySelector('#raw-toggle').onclick=()=>{state.mockRaw=!state.mockRaw;renderMock();}; document.querySelector('#mock-search').oninput=()=>renderMock();
  document.querySelector('#approval-cancel').onclick=()=>document.querySelector('#approval-modal').classList.add('hidden'); document.querySelector('#approval-confirm').onclick=()=>{document.querySelector('#approval-modal').classList.add('hidden');runStoryStep(3,true);};
}

bind(); loadBootstrap(); renderAgentWorkbench();
