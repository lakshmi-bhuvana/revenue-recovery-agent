const API_BASE = "";

function escapeHtml(value){
    const d=document.createElement("div");
    d.textContent=value==null?"":String(value);
    return d.innerHTML;
}
function formatCurrency(value){
    return new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:2}).format(Number(value||0));
}
function setText(id,value){const e=document.getElementById(id);if(e)e.textContent=value;}

function toggleSidebar(){
    const app=document.getElementById("app"); if(!app)return;
    const collapsed=app.classList.toggle("sidebar-collapsed");
    localStorage.setItem("sidebarCollapsed",collapsed?"true":"false");
    updateSidebarToggle();
}
function updateSidebarToggle(){
    const b=document.getElementById("sidebar-toggle"),app=document.getElementById("app");
    if(!b||!app)return;
    const c=app.classList.contains("sidebar-collapsed");
    const icon=b.querySelector(".toggle-icon"); if(icon)icon.textContent=c?"›":"‹";
    b.setAttribute("aria-label",c?"Expand sidebar":"Collapse sidebar");
    b.title=c?"Expand sidebar":"Collapse sidebar";
}
function setupSidebar(){
    const app=document.getElementById("app"),b=document.getElementById("sidebar-toggle");
    if(!app||!b)return;
    if(localStorage.getItem("sidebarCollapsed")==="true")app.classList.add("sidebar-collapsed");
    b.addEventListener("click",toggleSidebar); updateSidebarToggle();
}

async function loadDashboard(){
    const live=document.getElementById("live-text");
    try{
        if(live)live.textContent="Updating...";
        const r=await fetch(`${API_BASE}/dashboard-summary`,{cache:"no-store"});
        if(!r.ok)throw new Error(`Dashboard API returned ${r.status}`);
        const summary=await r.json();
        updateMetrics(summary); updatePriority(summary); updateStrategies(summary);
        try{
            const or=await fetch(`${API_BASE}/top-opportunities?limit=10`,{cache:"no-store"});
            if(or.ok)updateOpportunities(await or.json());
        }catch(e){console.warn("Top opportunities:",e);}
        if(live)live.textContent="Live";
        await loadOverallMetrics();
    }catch(e){console.error("Dashboard error:",e);if(live)live.textContent="API Error";}
}
function updateMetrics(m){
    setText("total-risk",formatCurrency(m.total_transaction_value));
    setText("expected-recovery",formatCurrency(m.expected_recovery_value));
    setText("recovery-rate", `${Number(m.recovery_rate||0).toFixed(2)}%`);
    const high=(m.priority_distribution||[]).find(x=>String(x.priority).toUpperCase()==="HIGH");
    setText("high-priority",Number(high?.cases||0).toLocaleString("en-IN"));
}
function updatePriority(data){
    let high=0,medium=0,low=0;
    (data.priority_distribution||[]).forEach(x=>{
        const p=String(x.priority||"").toUpperCase(),n=Number(x.cases||0);
        if(p==="HIGH")high=n; else if(p==="MEDIUM")medium=n; else if(p==="LOW")low=n;
    });
    updateLegend(".legend-dot.high",`High Priority (${high.toLocaleString("en-IN")})`);
    updateLegend(".legend-dot.medium",`Medium Priority (${medium.toLocaleString("en-IN")})`);
    updateLegend(".legend-dot.low",`Low Priority (${low.toLocaleString("en-IN")})`);
    updatePriorityChart(high,medium,low);
}
function updatePriorityChart(high,medium,low){
    const c=document.getElementById("priority-chart"); if(!c)return;
    const total=high+medium+low; setText("priority-total",total.toLocaleString("en-IN"));
    if(total<=0){c.style.background="#e2e8f0";return;}
    const hp=high/total*100,mp=medium/total*100;
    c.style.background=`conic-gradient(#2563eb 0% ${hp}%,#f59e0b ${hp}% ${hp+mp}%,#d1d5db ${hp+mp}% 100%)`;
}
function updateLegend(selector,text){
    const dot=document.querySelector(selector);if(!dot)return;const p=dot.parentElement;if(!p)return;
    p.innerHTML=`<span class="${escapeHtml(dot.className)}"></span><span>${escapeHtml(text)}</span>`;
}
function updateStrategies(data){
    const map={aggressive_recovery:0,assisted_recovery:0,standard_recovery:0,low_cost_recovery:0};
    (data.strategy_distribution||[]).forEach(x=>{const k=String(x.strategy||"").toLowerCase();if(k in map)map[k]=Number(x.cases||0);});
    setText("aggressive-count",map.aggressive_recovery.toLocaleString("en-IN"));
    setText("assisted-count",map.assisted_recovery.toLocaleString("en-IN"));
    setText("standard-count",map.standard_recovery.toLocaleString("en-IN"));
    setText("low-cost-count",map.low_cost_recovery.toLocaleString("en-IN"));
}
function updateOpportunities(payload){
    const arr=Array.isArray(payload)?payload:(payload?.value||[]),table=document.getElementById("opportunity-table");if(!table)return;
    if(!arr.length){table.innerHTML='<tr><td colspan="7" class="loading">No recovery opportunities found.</td></tr>';return;}
    table.innerHTML=arr.map(i=>{
        const p=String(i.priority||"LOW").toUpperCase(),pc=p.toLowerCase();
        return `<tr><td><a class="case-link" href="/recovery-case.html?transaction_id=${encodeURIComponent(i.transaction_id||"")}">${escapeHtml(i.transaction_id)}</a></td><td class="amount">${formatCurrency(i.transaction_amount)}</td><td class="probability">${(Number(i.recovery_probability||0)*100).toFixed(1)}%</td><td><span class="badge badge-${pc}">${escapeHtml(p)}</span></td><td>${escapeHtml(formatStrategy(i.strategy))}</td><td>${escapeHtml(i.recommended_channel||"—")}</td><td class="amount">${formatCurrency(i.expected_recovery_value)}</td></tr>`;
    }).join("");
}
function formatStrategy(s){return s?String(s).replaceAll("_"," ").replace(/\b\w/g,m=>m.toUpperCase()):"—";}

async function loadOverallMetrics(){
    try{
        const r=await fetch("/overall-metrics",{cache:"no-store"});if(!r.ok)return;const d=await r.json();
        setText("overall-total-cases",Number(d.total_cases||0).toLocaleString("en-IN"));
        setText("overall-total-value",formatCurrency(d.total_transaction_value));
        setText("overall-recovered-cases",Number(d.recovered_cases||0).toLocaleString("en-IN"));
        setText("overall-money-recovered",formatCurrency(d.money_recovered));
        setText("overall-recovery-rate",Number(d.overall_recovery_rate||0).toFixed(2)+"%");
        setText("overall-unrecovered-cases",Number(d.unrecovered_cases||0).toLocaleString("en-IN"));
        setText("overall-value-rate",Number(d.recovery_value_rate||0).toFixed(2)+"%");
        setText("overall-customers",Number(d.total_customers||0).toLocaleString("en-IN"));
    }catch(e){console.warn("Overall metrics:",e);}
}

let conversation=[];
function addChatMessage(role,text){
    const box=document.getElementById("conversation");if(!box)return;
    const row=document.createElement("div");row.className=`chat-message ${role}`;
    row.innerHTML=`<div><div class="chat-label">${role==="user"?"You":"Recovery AI"}</div><div class="chat-bubble">${escapeHtml(text)}</div></div>`;
    box.appendChild(row);box.scrollTop=box.scrollHeight;
}
function useAIQuestion(q){const i=document.getElementById("ai-question");if(!i)return;i.value=q;i.focus();}
async function askRecoveryAI(event){
    if(event)event.preventDefault();
    const i=document.getElementById("ai-question"),b=document.getElementById("ai-ask-button"),r=document.getElementById("ai-response"),s=document.getElementById("ai-bar-status");
    if(!i)return;const q=i.value.trim();if(!q)return;
    r.classList.add("visible");addChatMessage("user",q);b.disabled=true;b.textContent="Thinking…";s.textContent="Analyzing current recovery data…";
    try{
        const res=await fetch("/ai/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:q,context:{conversation_history:conversation,revenue_at_risk:document.getElementById("total-risk")?.textContent,expected_recovery:document.getElementById("expected-recovery")?.textContent,recovery_rate:document.getElementById("recovery-rate")?.textContent,high_priority_cases:document.getElementById("high-priority")?.textContent}})});
        const d=await res.json().catch(()=>({}));if(!res.ok)throw new Error(d.detail||`AI request failed (${res.status})`);
        const answer=d.answer||d.response||d.message||d.analysis||"I couldn't generate an answer.";conversation.push({role:"user",content:q},{role:"assistant",content:answer});addChatMessage("ai",answer);s.textContent="Grounded in current recovery data";
    }catch(e){addChatMessage("ai","Unable to generate the AI analysis right now. "+e.message);s.textContent="AI analysis unavailable";}
    finally{b.disabled=false;b.textContent="Ask AI";i.value="";}
}

function filterTable(){const q=(document.getElementById("search")?.value||"").toLowerCase().trim();document.querySelectorAll("#opportunity-table tr").forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?"":"none");}

document.addEventListener("DOMContentLoaded",()=>{
    setupSidebar();
    const form=document.getElementById("ai-bar-form");if(form)form.addEventListener("submit",askRecoveryAI);
    const search=document.getElementById("search");if(search)search.addEventListener("input",filterTable);
    loadDashboard(); setInterval(loadDashboard,30000);
});
