/* حصن السعودي — the money-manager layer: accounts, transactions, budgets, bills, savings goals,
   debts, reports, backup, app lock and navigation. Loaded before app.js; talks to the core via window.HISN. */
(()=>{
"use strict";
const H=()=>window.HISN;
const S=()=>H().S;
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const N=v=>{const n=Number(v);return isFinite(n)?n:0};
const fmt=(n,d=0)=>N(n).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const uid=()=>Math.random().toString(36).slice(2,9);
const KEY="hisn:";
const ls={get(k){try{return JSON.parse(localStorage.getItem(KEY+k))}catch(e){return null}},set(k,v){try{localStorage.setItem(KEY+k,JSON.stringify(v));return true}catch(e){return false}}};

/* ── categories ─────────────────────────────── */
const CAT_E=[["food","🍽️","أكل وشرب","#E2A541"],["groc","🛒","بقالة وسوبرماركت","#62C597"],["transport","🚕","مواصلات","#6E8BD6"],["car","⛽","عربية وبنزين","#9AA0B4"],
 ["bills","💡","فواتير البيت","#E2A541"],["tel","📱","موبايل وإنترنت","#6E8BD6"],["rent","🏠","سكن وإيجار","#C9A24E"],["health","💊","صحة وعلاج","#E06A5F"],
 ["edu","📚","تعليم وكورسات","#7FA0E8"],["fun","🎬","خروج وترفيه","#B07CC6"],["cloth","👕","لبس","#D6B26A"],["gift","🎁","هدايا ومناسبات","#E07F9A"],
 ["charity","🤲","صدقات وزكاة","#2F8F63"],["family","👨‍👩‍👧","أهل وعيلة","#B07CC6"],["care","💈","عناية شخصية","#9AA0B4"],["sav","🏦","ادخار واستثمار","#2F8F63"],
 ["debt","💳","سداد ديون وأقساط","#E06A5F"],["other","📦","أخرى","#5E6680"]];
const CAT_I=[["sal","💼","مرتب","#5CBF8D"],["bonus","🎉","مكافأة وأرباح","#C9A24E"],["cert","🏛️","عائد شهادة","#6E8BD6"],["side","🧰","دخل جانبي","#62C597"],
 ["gifti","🎁","هدية","#E07F9A"],["refund","↩️","استرداد وتحصيل","#9AA0B4"],["oi","📥","دخل آخر","#5E6680"]];
const toCat=t=>([id,i,n,c])=>({id,i,n,c,t});
function cats(t){const base=(t==="i"?CAT_I:CAT_E).map(toCat(t));const custom=(S().cats||[]).filter(c=>c.t===t);return base.concat(custom)}
function catOf(id){return cats("e").concat(cats("i")).find(c=>c.id===id)||{id,i:"❔",n:"غير مصنّف",c:"#5E6680"}}
const ATYPE={cash:["💵","كاش"],bank:["🏦","حساب بنكي"],wallet:["📱","محفظة إلكترونية"],savings:["🐖","مدخرات"]};
const accts=()=>S().cash||[];
const acctOf=id=>accts().find(a=>a.id===id);
const acctName=id=>{const a=acctOf(id);return a?a.label:"حساب محذوف"};
const acctIcon=a=>(ATYPE[a&&a.type]||ATYPE.bank)[0];

/* ── dates ──────────────────────────────────── */
const today=()=>H().today();
const mkOf=d=>String(d||"").slice(0,7);
function addM(mk,n){let [y,m]=mk.split("-").map(Number);m+=n;while(m>12){m-=12;y++}while(m<1){m+=12;y--}return `${y}-${String(m).padStart(2,"0")}`}
const mLabel=mk=>{const [y,m]=mk.split("-").map(Number);return new Date(Date.UTC(y,m-1,1)).toLocaleDateString("ar-EG-u-nu-latn",{month:"long",year:"numeric",timeZone:"UTC"})};
const dayLabel=d=>{const [y,m,dd]=d.split("-").map(Number);return new Date(Date.UTC(y,m-1,dd)).toLocaleDateString("ar-EG-u-nu-latn",{weekday:"long",day:"numeric",month:"long",timeZone:"UTC"})};
const daysIn=mk=>{const [y,m]=mk.split("-").map(Number);return new Date(Date.UTC(y,m,0)).getUTCDate()};
const dayOf=(mk,day)=>`${mk}-${String(Math.min(daysIn(mk),Math.max(1,N(day)||1))).padStart(2,"0")}`;

/* ── input helpers: Arabic digits + a tiny calculator (50+30×2) ── */
function normNum(s){return String(s??"").replace(/[٠-٩]/g,d=>"٠١٢٣٤٥٦٧٨٩".indexOf(d)).replace(/[۰-۹]/g,d=>"۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/[٫,]/g,".").replace(/[×xX]/g,"*").replace(/[÷]/g,"/").replace(/[−–]/g,"-").replace(/\s+/g,"")}
function calcExpr(s){s=normNum(s);if(!s)return null;if(!/^[\d.+\-*/]+$/.test(s))return null;
  const t=s.match(/(\d+\.?\d*|\.\d+|[+\-*/])/g);if(!t||t.join("")!==s)return null;
  const terms=[];let sign=1,cur=null,op=null;
  for(const x of t){if("+-".includes(x)){if(cur==null&&op==null&&!terms.length&&x==="-"){sign=-sign;continue}if(cur==null)return null;terms.push(sign*cur);sign=x==="-"?-1:1;cur=null;op=null}
    else if("*/".includes(x)){if(cur==null)return null;op=x}
    else{const v=Number(x);if(!isFinite(v))return null;if(op==="*")cur*=v;else if(op==="/")cur=v?cur/v:NaN;else if(cur==null)cur=v;else return null;op=null}}
  if(cur==null||op)return null;terms.push(sign*cur);const r=terms.reduce((a,b)=>a+b,0);return isFinite(r)?Math.round(r*100)/100:null}

/* ── ledger ─────────────────────────────────── */
function applyTx(x,sg){const a=N(x.a)*sg;const f=acctOf(x.ac);
  if(x.t==="e"){if(f)f.amount=N(f.amount)-a}
  else if(x.t==="i"){if(f)f.amount=N(f.amount)+a}
  else if(x.t==="x"){if(f)f.amount=N(f.amount)-a;const to=acctOf(x.to);if(to)to.amount=N(to.amount)+a}
  [f,acctOf(x.to)].forEach(z=>{if(z)z.amount=Math.round(N(z.amount)*100)/100})}
function saveTx(x,old){const L=S().tx;if(old){applyTx(old,-1);const i=L.findIndex(y=>y.id===old.id);if(i>=0)L[i]=x;else L.push(x)}else L.push(x);applyTx(x,1)}
function delTx(id){const L=S().tx;const i=L.findIndex(y=>y.id===id);if(i<0)return;applyTx(L[i],-1);L.splice(i,1)}
const txIn=mk=>S().tx.filter(x=>mkOf(x.d)===mk);
function sums(mk){let e=0,i=0;for(const x of txIn(mk)){if(x.t==="e")e+=N(x.a);else if(x.t==="i")i+=N(x.a)}return {e,i,n:i-e}}
function byCat(mk,t="e"){const m={};for(const x of txIn(mk))if(x.t===t)m[x.c]=(m[x.c]||0)+N(x.a);return Object.entries(m).map(([c,v])=>({c,v,cat:catOf(c)})).sort((a,b)=>b.v-a.v)}
/* average monthly spend over the last complete months that were actually tracked (at least 8 hand-entered
   expenses; auto-posted bills alone don't count) — savings/investing excluded since it is not consumption */
const TRACKED=8;
function avgExp(){if(!window.HISN)return 0;const cur=mkOf(today());const tx=S().tx||[];if(!tx.length)return 0;let tot=0,n=0;
  for(let k=1;k<=3;k++){const mk=addM(cur,-k);const L=tx.filter(x=>x.t==="e"&&mkOf(x.d)===mk);if(L.filter(x=>!x.rec).length<TRACKED)continue;
    tot+=L.filter(x=>x.c!=="sav").reduce((s,x)=>s+N(x.a),0);n++}
  return n?Math.round(tot/n):0}

/* ── budgets ────────────────────────────────── */
function budgetRows(mk){const B=S().budgets||{};const spent={};byCat(mk).forEach(r=>spent[r.c]=r.v);
  return Object.entries(B).filter(([k,v])=>k!=="_total"&&N(v)>0).map(([c,lim])=>({c,cat:catOf(c),lim:N(lim),sp:spent[c]||0})).sort((a,b)=>b.sp/b.lim-a.sp/a.lim)}
/* with an overall cap, all spending counts; without one, only the categories that carry a limit */
function budgetTotal(mk){const B=S().budgets||{};const rows=budgetRows(mk);
  if(N(B._total))return {lim:N(B._total),sp:sums(mk).e};return {lim:rows.reduce((s,r)=>s+r.lim,0),sp:rows.reduce((s,r)=>s+r.sp,0)}}
const lvl=r=>r>=1?"over":r>=0.8?"near":"ok";

/* ── recurring bills & income ──────────────── */
function nextDue(r){const day=N(r.day)||1;let mk=r.last?addM(mkOf(r.last),1):mkOf(r.start||today());let d=dayOf(mk,day);
  if(!r.last&&r.start&&d<r.start){mk=addM(mk,1);d=dayOf(mk,day)}return d}
function postRec(r,d){const x={id:uid(),d,t:r.t,a:N(r.a),c:r.c,ac:r.ac,n:r.n,rec:r.id};if(acctOf(r.ac)||!r.ac)saveTx(x);r.last=d;return x}
/* auto-post every due occurrence of the automatic ones; reminders stay pending until the user confirms */
function runRecurring(){const t=today();let n=0;for(const r of S().rec||[]){if(!r.auto)continue;let guard=0;while(nextDue(r)<=t&&guard++<36){postRec(r,nextDue(r));n++}}
  if(n){H().commit();H().toast(`اتسجّل تلقائيًا ${n} معاملة متكررة`)}}
const pendingRec=()=>(S().rec||[]).filter(r=>!r.auto&&nextDue(r)<=today());
function upcoming(days=10){const t=today();const lim=new Date(H().dParse(t).getTime()+days*864e5).toISOString().slice(0,10);
  return (S().rec||[]).map(r=>({r,d:nextDue(r)})).filter(x=>x.d<=lim).sort((a,b)=>a.d.localeCompare(b.d))}

/* ── charts ─────────────────────────────────── */
function ring(parts,total,label,sub){const R=78,r=52,cx=85,cy=85;let a0=-Math.PI/2,out="";
  if(!total)return `<svg viewBox="0 0 170 170" class="ring"><circle cx="85" cy="85" r="65" fill="none" stroke="#1B2442" stroke-width="26"/><text x="85" y="90" text-anchor="middle">لا بيانات</text></svg>`;
  const P=(rad,ang)=>`${(cx+rad*Math.cos(ang)).toFixed(2)} ${(cy+rad*Math.sin(ang)).toFixed(2)}`;
  parts.forEach(p=>{if(p.v<=0)return;let a=p.v/total*Math.PI*2;if(a>=Math.PI*2)a=Math.PI*2-1e-4;const a1=a0+a,lg=a>Math.PI?1:0;
    out+=`<path d="M${P(R,a0)}A${R} ${R} 0 ${lg} 1 ${P(R,a1)}L${P(r,a1)}A${r} ${r} 0 ${lg} 0 ${P(r,a0)}Z" fill="${p.c}" stroke="#0B1124" stroke-width="1.5"/>`;a0=a1});
  return `<svg viewBox="0 0 170 170" class="ring" role="img" aria-label="${esc(label)}">${out}<text x="85" y="80" text-anchor="middle" style="font-size:10px">${esc(label)}</text><text x="85" y="102" text-anchor="middle" style="font-family:'Cormorant Garamond',serif;font-size:22px;font-weight:600;fill:#F6E7BE">${esc(sub)}</text></svg>`}
function bars(months){const W=360,H2=170,pl=6,pr=42,pt=10,pb=26;const mx=Math.max(1,...months.flatMap(m=>[m.i,m.e]));const bw=(W-pl-pr)/months.length;
  const Y=v=>pt+(1-v/mx)*(H2-pt-pb);let g="";
  for(let i=0;i<=2;i++){const v=mx*i/2;g+=`<line x1="${pl}" x2="${W-pr}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1B2442"/><text x="${W-pr+4}" y="${Y(v)+3}">${v>=1000?fmt(v/1000)+"k":fmt(v)}</text>`}
  months.forEach((m,k)=>{const x=pl+k*bw+bw*.18,w=bw*.3;
    g+=`<rect x="${x}" y="${Y(m.i)}" width="${w}" height="${H2-pb-Y(m.i)}" rx="2" fill="#5CBF8D"/><rect x="${x+w+2}" y="${Y(m.e)}" width="${w}" height="${H2-pb-Y(m.e)}" rx="2" fill="#E06A5F"/>
    <text x="${x+w+1}" y="${H2-8}" text-anchor="middle" style="font-family:var(--f-body);font-size:10px">${esc(m.l)}</text>`});
  return `<svg viewBox="0 0 ${W} ${H2}" style="width:100%;height:auto;direction:ltr" role="img" aria-label="الدخل والمصروف آخر ${months.length} شهور">${g}</svg>`}

/* ── state for the money views ─────────────── */
const V={mk:null,q:"",ft:"",fa:"",fc:"",view:"home"};

/* ── HOME ───────────────────────────────────── */
function homeAlerts(){const A=[];const mk=mkOf(today());
  const lb=ls.get("lastBackup");const age=lb?(Date.now()-new Date(lb).getTime())/864e5:Infinity;
  const hasData=(S().tx||[]).length+(S().gold||[]).length+(S().cash||[]).length>0;
  if(hasData&&age>14)A.push({lv:"warn",t:lb?`آخر نسخة احتياطية من ${Math.round(age)} يوم`:"لسه ما عملتش نسخة احتياطية",b:"بياناتك على الموبايل ده بس. لو اتمسح التطبيق أو ضاع الموبايل، النسخة هي اللي بترجّعها.",btn:["backup","اعمل نسخة الآن"]});
  pendingRec().forEach(r=>A.push({lv:"warn",t:`مستحق: ${r.n} — ${fmt(r.a)} ج`,b:`ميعاده ${H().dLabel(nextDue(r))}.`,btn:["post:"+r.id,"سجّله"]}));
  budgetRows(mk).filter(r=>r.sp>=r.lim*0.8).slice(0,3).forEach(r=>A.push({lv:r.sp>r.lim?"critical":"warn",t:`${r.cat.i} ${r.cat.n}: ${Math.round(r.sp/r.lim*100)}% من الميزانية`,b:r.sp>r.lim?`عدّيت الحد بـ ${fmt(r.sp-r.lim)} ج.`:`فاضل ${fmt(r.lim-r.sp)} ج للشهر.`}));
  const crit=H().rules(H().C).filter(a=>a.lv==="critical"&&!a.mx).slice(0,2);crit.forEach(a=>A.push({lv:"critical",t:a.t,b:a.a||a.b}));
  return A}
function renderHome(){const el=$("#v-home");if(!el)return;const C=H().C;const mk=mkOf(today());const s=sums(mk);const bt=budgetTotal(mk);
  const keys=Object.keys(H().HIST.snaps||{}).sort();const prev=keys.filter(k=>k<C.t).pop();const dl=prev?C.nw-H().HIST.snaps[prev].nw:null;
  const A=homeAlerts();const recent=S().tx.slice().sort((a,b)=>(b.d+b.id).localeCompare(a.d+a.id)).slice(0,6);
  const up=upcoming(10);const nm=$("#nm")?.textContent||"",mean=$("#mean")?.textContent||"";
  const day=+today().slice(8,10),dim=daysIn(mk);const pace=day?s.e/day*dim:0;
  el.innerHTML=`
  <div class="nwcard" data-m="go:wealth" role="button" tabindex="0">
    <div class="eyebrow">NET WORTH · صافي الثروة</div>
    <div class="nwv">${fmt(C.nw)}<small>EGP</small></div>
    ${dl!=null?`<div class="small muted">منذ ${H().dLabel(prev)}: <span class="num ${dl>=0?"up":"down"}">${dl>=0?"+":"−"}${fmt(Math.abs(dl))}</span></div>`:""}
    <div class="nwpills"><span class="pill">ذهب <b>${fmt(C.goldT.grams24+C.goldT.grams21,1)} g</b></span><span class="pill">دخل سلبي <b>${fmt(C.passive)}</b></span><span class="pill">الحسابات <b>${fmt(C.cashT)}</b></span></div>
    <div class="nwgo">التفاصيل والأصول ←</div>
  </div>
  ${nm?`<div class="daily"><span class="dn">${esc(nm)}</span><span class="small muted">${esc(mean)}</span></div>`:""}
  ${A.length?`<div class="alerts" style="margin-top:12px">${A.map(a=>`<div class="alert ${a.lv}"><div class="stripe"></div><div><h4>${esc(a.t)}</h4><p>${esc(a.b)}</p>${a.btn?`<button class="btn sm gold" style="margin-top:8px" type="button" data-m="${esc(a.btn[0])}">${esc(a.btn[1])}</button>`:""}</div></div>`).join("")}</div>`:""}
  <div class="panel mcard"><div class="ph"><h3>${mLabel(mk)}</h3><button class="btn sm ghost" type="button" data-m="go:reports">التقرير ←</button></div>
    <div class="trio"><div><div class="k">دخل</div><div class="v up">${fmt(s.i)}</div></div><div><div class="k">مصروف</div><div class="v down">${fmt(s.e)}</div></div><div><div class="k">الصافي</div><div class="v ${s.n>=0?"up":"down"}">${s.n>=0?"+":"−"}${fmt(Math.abs(s.n))}</div></div></div>
    ${bt.lim?`<div class="bline"><div class="small muted">الميزانية: ${fmt(bt.sp)} من ${fmt(bt.lim)}</div><div class="pbar ${lvl(bt.sp/bt.lim)}"><i style="width:${Math.min(100,bt.sp/bt.lim*100)}%"></i><b style="right:${Math.min(100,day/dim*100)}%" title="النهارده"></b></div>
      <div class="small faint">${pace>bt.lim?`بالمعدل ده هتصرف ≈ ${fmt(pace)} آخر الشهر (فوق الحد بـ ${fmt(pace-bt.lim)})`:`بالمعدل ده هتقفل الشهر على ≈ ${fmt(pace)}`}</div></div>`
     :`<button class="btn sm" type="button" data-m="go:budget" style="margin-top:10px">حدّد ميزانية الشهر</button>`}
  </div>
  <div class="panel"><div class="ph"><h3>حساباتك</h3><div class="acts"><button class="btn sm" type="button" data-m="xfer">تحويل</button><button class="btn sm gold" type="button" data-add="cash">+ حساب</button></div></div>
    ${accts().length?`<div class="accts">${accts().map(a=>`<button type="button" class="acct" data-m="acct:${a.id}"><span class="ai">${acctIcon(a)}</span><span class="an">${esc(a.label)}</span><span class="av num ${N(a.amount)<0?"down":""}">${fmt(a.amount)}</span></button>`).join("")}</div>
      <div class="small muted" style="margin-top:8px">الإجمالي <b class="num">${fmt(C.cashT)}</b> ج · اضغط على حساب لعرض حركته</div>`
     :`<div class="empty">ضيف حساباتك (كاش، بنك، محفظة) برصيدها الحالي، وكل معاملة هتعدّل الرصيد لوحدها.</div>`}
  </div>
  ${up.length?`<div class="panel"><div class="ph"><h3>جاي قريب</h3><button class="btn sm ghost" type="button" data-m="go:budget">الكل ←</button></div>
    <div class="list">${up.map(({r,d})=>{const c=catOf(r.c);return `<div class="row"><span class="ic" style="background:${c.c}22;border-color:${c.c}55">${c.i}</span><div class="mid"><b>${esc(r.n)}</b><span class="small muted">${H().dLabel(d)} · ${r.auto?"تلقائي":"تذكير"}</span></div><span class="amt num ${r.t==="i"?"up":"down"}">${r.t==="i"?"+":"−"}${fmt(r.a)}</span></div>`}).join("")}</div></div>`:""}
  <div class="panel"><div class="ph"><h3>آخر المعاملات</h3><button class="btn sm ghost" type="button" data-m="go:tx">الكل ←</button></div>
    ${recent.length?`<div class="list">${recent.map(txRow).join("")}</div>`:`<div class="empty">سجّل أول مصروف من زرار <b>+</b> تحت. اكتب المبلغ، اختار التصنيف، وخلاص.</div>`}
  </div>`}

function txRow(x){const c=x.t==="x"?{i:"⇄",n:"تحويل",c:"#6E8BD6"}:catOf(x.c);const sign=x.t==="i"?"+":x.t==="e"?"−":"";
  const sub=x.t==="x"?`${esc(acctName(x.ac))} ← ${esc(acctName(x.to))}`:esc(x.ac?acctName(x.ac):"");
  return `<button type="button" class="row tx" data-m="tx:${x.id}"><span class="ic" style="background:${c.c}22;border-color:${c.c}55">${c.i}</span><div class="mid"><b>${esc(x.n||c.n)}</b><span class="small muted">${x.n?esc(c.n)+" · ":""}${sub}${x.rec?" · 🔁":""}</span></div><span class="amt num ${x.t==="i"?"up":x.t==="e"?"down":""}">${sign}${fmt(x.a,N(x.a)%1?2:0)}</span></button>`}

/* ── TRANSACTIONS ──────────────────────────── */
function monthNav(){return `<div class="mnav"><button type="button" class="btn sm" data-m="mk:-1" aria-label="الشهر اللي فات">‹</button><b>${mLabel(V.mk)}</b><button type="button" class="btn sm" data-m="mk:1" aria-label="الشهر الجاي" ${V.mk>=mkOf(today())?"disabled":""}>›</button></div>`}
function renderTx(){const el=$("#v-tx");if(!el)return;const s=sums(V.mk);
  let L=txIn(V.mk);const q=normNum(V.q).toLowerCase(),qt=V.q.trim().toLowerCase();
  if(V.ft)L=L.filter(x=>x.t===V.ft);if(V.fa)L=L.filter(x=>x.ac===V.fa||x.to===V.fa);if(V.fc)L=L.filter(x=>x.c===V.fc);
  if(qt)L=L.filter(x=>(x.n||"").toLowerCase().includes(qt)||catOf(x.c).n.includes(qt)||String(x.a).includes(q));
  L.sort((a,b)=>(b.d+b.id).localeCompare(a.d+a.id));
  const days={};L.forEach(x=>(days[x.d]=days[x.d]||[]).push(x));
  const opts=(arr,cur)=>arr.map(([v,n])=>`<option value="${esc(v)}" ${v===cur?"selected":""}>${esc(n)}</option>`).join("");
  const fa=V.fa?acctOf(V.fa):null;
  el.innerHTML=`${monthNav()}
  <div class="trio panel" style="padding:12px 14px"><div><div class="k">دخل</div><div class="v up">${fmt(s.i)}</div></div><div><div class="k">مصروف</div><div class="v down">${fmt(s.e)}</div></div><div><div class="k">الصافي</div><div class="v ${s.n>=0?"up":"down"}">${s.n>=0?"+":"−"}${fmt(Math.abs(s.n))}</div></div></div>
  ${fa?`<div class="chipbar"><span class="chip ok"><i></i><span>${acctIcon(fa)} ${esc(fa.label)} · الرصيد ${fmt(fa.amount)}</span></span><button class="btn sm ghost" type="button" data-m="clr:fa">إلغاء الفلتر ✕</button></div>`:""}
  <div class="filters"><input type="search" id="txq" placeholder="ابحث في الملاحظات أو التصنيف أو المبلغ" value="${esc(V.q)}" autocomplete="off">
    <select id="txft" aria-label="النوع"><option value="">الكل</option>${opts([["e","مصروف"],["i","دخل"],["x","تحويل"]],V.ft)}</select>
    <select id="txfc" aria-label="التصنيف"><option value="">كل التصنيفات</option>${opts(cats("e").concat(cats("i")).map(c=>[c.id,c.i+" "+c.n]),V.fc)}</select>
    <select id="txfa" aria-label="الحساب"><option value="">كل الحسابات</option>${opts(accts().map(a=>[a.id,a.label]),V.fa)}</select></div>
  ${L.length?Object.entries(days).map(([d,xs])=>{const net=xs.reduce((s,x)=>s+(x.t==="i"?N(x.a):x.t==="e"?-N(x.a):0),0);
    return `<div class="dayh"><span>${dayLabel(d)}</span><span class="num ${net>=0?"up":"down"}">${net>=0?"+":"−"}${fmt(Math.abs(net))}</span></div><div class="list panel">${xs.map(txRow).join("")}</div>`}).join("")
   :`<div class="empty" style="margin-top:12px">${S().tx.length?"مفيش معاملات بالفلتر ده في الشهر ده.":"لسه مفيش معاملات. اضغط + وسجّل أول واحدة."}</div>`}
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px"><button class="btn sm" type="button" data-m="csv">تصدير الشهر CSV</button><button class="btn sm ghost" type="button" data-m="csvall">تصدير كل المعاملات</button></div>`;
  const q1=$("#txq");q1.oninput=()=>{V.q=q1.value;const p=q1.selectionStart;renderTx();const n=$("#txq");n.focus();try{n.setSelectionRange(p,p)}catch(e){}};
  $("#txft").onchange=e=>{V.ft=e.target.value;renderTx()};$("#txfc").onchange=e=>{V.fc=e.target.value;renderTx()};$("#txfa").onchange=e=>{V.fa=e.target.value;renderTx()}}

/* ── BUDGET / BILLS / GOALS / DEBTS ────────── */
function renderBudget(){const el=$("#v-budget");if(!el)return;const mk=V.mk;const rows=budgetRows(mk);const bt=budgetTotal(mk);const B=S().budgets||{};
  const cur=mk===mkOf(today());const day=cur?+today().slice(8,10):daysIn(mk);const tf=day/daysIn(mk);
  const unb=byCat(mk).filter(r=>!N(B[r.c]));
  const bud=`<div class="panel"><div class="ph"><h3>الميزانية</h3><div class="acts"><button class="btn sm" type="button" data-m="bsuggest">اقتراح من مصروفك</button><button class="btn sm gold" type="button" data-m="badd">+ ميزانية</button></div></div>
    <div class="bline" style="margin-top:0"><div class="small muted">${N(B._total)?"الحد الكلي للشهر":"مجموع حدود التصنيفات"}: <b class="num">${fmt(bt.lim)}</b> · المصروف <b class="num">${fmt(bt.sp)}</b> <button class="btn sm ghost" type="button" data-m="btotal">تعديل الحد الكلي</button></div>
      ${bt.lim?`<div class="pbar ${lvl(bt.sp/bt.lim)}"><i style="width:${Math.min(100,bt.sp/bt.lim*100)}%"></i>${cur?`<b style="right:${tf*100}%"></b>`:""}</div><div class="small faint">${bt.sp<=bt.lim?`فاضل ${fmt(bt.lim-bt.sp)} ج${cur?` · ≈ ${fmt((bt.lim-bt.sp)/Math.max(1,daysIn(mk)-day+1))} ج في اليوم لحد آخر الشهر`:""}`:`عدّيت الحد بـ ${fmt(bt.sp-bt.lim)} ج`}</div>`:""}</div>
    ${rows.length?`<div class="list" style="margin-top:12px">${rows.map(r=>{const q=r.sp/r.lim;return `<button type="button" class="row brow" data-m="bedit:${r.c}"><span class="ic" style="background:${r.cat.c}22;border-color:${r.cat.c}55">${r.cat.i}</span><div class="mid"><b>${esc(r.cat.n)}</b>
      <div class="pbar ${lvl(q)}"><i style="width:${Math.min(100,q*100)}%"></i>${cur?`<b style="right:${tf*100}%"></b>`:""}</div><span class="small muted"><span class="num">${fmt(r.sp)}</span> من <span class="num">${fmt(r.lim)}</span> · ${q>1?`<span class="down">فوق الحد ${fmt(r.sp-r.lim)}</span>`:`فاضل ${fmt(r.lim-r.sp)}`}</span></div><span class="amt num ${q>1?"down":q>=.8?"warnc":"muted"}">${Math.round(q*100)}%</span></button>`}).join("")}</div>`
     :`<div class="empty" style="margin-top:12px">حدّد حد شهري لكل تصنيف مهم (أكل، خروج، مواصلات…). الخط الأبيض على الشريط = فين المفروض تكون النهارده.</div>`}
    ${unb.length?`<div class="small muted" style="margin-top:10px">مصروف من غير ميزانية: ${unb.map(r=>`${r.cat.i} ${esc(r.cat.n)} <b class="num">${fmt(r.v)}</b>`).join(" · ")}</div>`:""}</div>`;
  const R=(S().rec||[]).slice().sort((a,b)=>nextDue(a).localeCompare(nextDue(b)));
  const bills=`<div class="panel"><div class="ph"><h3>الفواتير والمتكرر</h3><div class="acts"><button class="btn sm gold" type="button" data-m="radd">+ متكرر</button></div></div>
    ${R.length?`<div class="list">${R.map(r=>{const c=catOf(r.c);const d=nextDue(r);const due=d<=today();return `<div class="row"><span class="ic" style="background:${c.c}22;border-color:${c.c}55">${c.i}</span><div class="mid"><b>${esc(r.n)}</b><span class="small muted">كل شهر يوم ${N(r.day)} · ${r.auto?"بيتسجّل تلقائي":"تذكير"} · ${esc(acctName(r.ac))}</span><span class="small ${due?"down":"faint"}">${due?"مستحق ":"الجاي "}${H().dLabel(d)}</span></div>
      <div class="rcol"><span class="amt num ${r.t==="i"?"up":"down"}">${r.t==="i"?"+":"−"}${fmt(r.a)}</span><div class="rowacts">${!r.auto&&due?`<button class="btn sm gold" type="button" data-m="post:${r.id}">سجّل</button>`:""}<button class="btn sm ghost" type="button" data-m="redit:${r.id}">تعديل</button></div></div></div>`}).join("")}</div>
      <div class="small muted" style="margin-top:8px">في الشهر: داخل <b class="num up">${fmt(R.filter(r=>r.t==="i").reduce((s,r)=>s+N(r.a),0))}</b> · خارج <b class="num down">${fmt(R.filter(r=>r.t==="e").reduce((s,r)=>s+N(r.a),0))}</b></div>`
     :`<div class="empty">ضيف المرتب، الإيجار، النت، الكهرباء، الأقساط… «تلقائي» بيتسجّل لوحده في ميعاده، و«تذكير» بيظهرلك في الرئيسية تأكده.</div>`}</div>`;
  const G=S().sg||[];
  const goals=`<div class="panel"><div class="ph"><h3>أهداف الادخار</h3><div class="acts"><button class="btn sm gold" type="button" data-m="gadd">+ هدف</button></div></div>
    ${G.length?`<div class="goals">${G.map(g=>{const p=Math.min(1,N(g.saved)/(N(g.target)||1));const left=Math.max(0,N(g.target)-N(g.saved));
      const ml=g.due?Math.max(1,Math.ceil(H().daysBetween(today(),g.due)/30.4)):null;const L2=2*Math.PI*30;
      return `<div class="goal"><svg viewBox="0 0 80 80" class="gring"><circle cx="40" cy="40" r="30" fill="none" stroke="#1B2442" stroke-width="7"/><circle cx="40" cy="40" r="30" fill="none" stroke="${p>=1?"#5CBF8D":"#C9A24E"}" stroke-width="7" stroke-linecap="round" stroke-dasharray="${L2*p} ${L2}" transform="rotate(-90 40 40)"/><text x="40" y="45" text-anchor="middle" style="font-size:15px;fill:#F6E7BE">${Math.round(p*100)}%</text></svg>
       <div class="mid"><b>${esc(g.n)}</b><span class="small muted"><span class="num">${fmt(g.saved)}</span> من <span class="num">${fmt(g.target)}</span>${g.due?` · لحد ${H().dLabel(g.due)}`:""}</span>
       <span class="small ${p>=1?"up":"faint"}">${p>=1?"اكتمل، الحمد لله":ml?`محتاج ${fmt(left/ml)} ج/شهر لمدة ${ml} شهر`:`فاضل ${fmt(left)} ج`}</span>
       <div class="rowacts"><button class="btn sm gold" type="button" data-m="gdep:${g.id}">+ إيداع</button><button class="btn sm" type="button" data-m="gwd:${g.id}">سحب</button><button class="btn sm ghost" type="button" data-m="gedit:${g.id}">تعديل</button></div></div></div>`}).join("")}</div>
      <p class="small faint" style="margin:8px 0 0">الهدف «تجنيب» لجزء من فلوسك، مش بيتخصم من الحسابات ولا من صافي الثروة. هدف الجواز الكبير في «الثروة ← الدخل والادخار».</p>`
     :`<div class="empty">هدف واضح بمبلغ وتاريخ: عربية، عمرة، شبكة، صندوق طوارئ… وهحسبلك المطلوب كل شهر.</div>`}</div>`;
  const D=S().debts||[];const dm=D.filter(d=>d.dir!=="owed"),dl=D.filter(d=>d.dir==="owed");
  const dRow=d=>{const due=d.due?H().daysBetween(today(),d.due):null;return `<div class="row"><span class="ic">${d.dir==="owed"?"📥":"📤"}</span><div class="mid"><b>${esc(d.label)}</b><span class="small muted">${N(d.limit)?`استخدام ${Math.round(N(d.amount)/N(d.limit)*100)}% من ${fmt(d.limit)} · `:""}${N(d.rate)?`<span class="down">فايدة ${N(d.rate)}%/شهر</span> · `:""}${d.due?(due<0?`<span class="down">متأخر ${-due} يوم</span>`:`ميعاده ${H().dLabel(d.due)}`):"بدون ميعاد"}${d.note?" · "+esc(d.note):""}</span></div>
    <div class="rcol"><span class="amt num ${d.dir==="owed"?"up":"down"}">${fmt(d.amount)}</span><div class="rowacts">${N(d.amount)>0?`<button class="btn sm gold" type="button" data-m="dpay:${d.id}">${d.dir==="owed"?"تحصيل":"سداد"}</button>`:""}<button class="btn sm ghost" type="button" data-edit="debt:${d.id}">تعديل</button><button class="btn sm ghost danger" type="button" data-del="debt:${d.id}">حذف</button></div></div></div>`};
  const debts=`<div class="panel"><div class="ph"><h3>الديون والسلف</h3><div class="acts"><button class="btn sm gold" type="button" data-add="debt">+ دين</button></div></div>
    ${D.length?`${dm.length?`<div class="small muted">عليك · <b class="num down">${fmt(dm.reduce((s,d)=>s+N(d.amount),0))}</b></div><div class="list">${dm.map(dRow).join("")}</div>`:""}
      ${dl.length?`<div class="small muted" style="margin-top:10px">ليك عند الناس · <b class="num up">${fmt(dl.reduce((s,d)=>s+N(d.amount),0))}</b></div><div class="list">${dl.map(dRow).join("")}</div>`:""}
      <p class="small faint" style="margin:8px 0 0">اللي عليك بيتخصم من صافي الثروة، واللي ليك بيتضاف. السداد من حساب بيسجّل معاملة ويعدّل الرصيد.</p>`
     :`<div class="empty">سجّل الكريدت كارد، الأقساط، أو أي سلفة ليك أو عليك.</div>`}</div>`;
  el.innerHTML=monthNav()+bud+bills+goals+debts}

/* ── REPORTS ───────────────────────────────── */
function renderReports(){const el=$("#v-reports");if(!el)return;const mk=V.mk;const s=sums(mk);const ec=byCat(mk,"e"),ic=byCat(mk,"i");const pv=sums(addM(mk,-1));const pc={};byCat(addM(mk,-1)).forEach(r=>pc[r.c]=r.v);
  const months=[];for(let k=5;k>=0;k--){const m=addM(mk,-k);const x=sums(m);const [y,mm]=m.split("-").map(Number);months.push({...x,l:new Date(Date.UTC(y,mm-1,1)).toLocaleDateString("ar-EG-u-nu-latn",{month:"short",timeZone:"UTC"})})}
  const cur=mk===mkOf(today());const days=cur?+today().slice(8,10):daysIn(mk);const avg=s.e/days;
  const top=txIn(mk).filter(x=>x.t==="e").sort((a,b)=>N(b.a)-N(a.a)).slice(0,5);
  const rate=s.i>0?(s.i-s.e)/s.i:null;const m6=months.filter(m=>m.i||m.e);const avgSave=m6.length?m6.reduce((a,m)=>a+m.n,0)/m6.length:0;
  const chg=(a,b)=>b?((a-b)/b*100):null;const dE=chg(s.e,pv.e);
  el.innerHTML=`${monthNav()}
  <div class="panel"><div class="ph"><h3>الملخص</h3><span class="code">MONTHLY REPORT</span></div>
   <div class="pstrip"><div class="pbox"><div class="k">الدخل</div><div class="v up">${fmt(s.i)}</div><div class="s">${pv.i?`الشهر اللي فات ${fmt(pv.i)}`:""}</div></div>
    <div class="pbox"><div class="k">المصروف</div><div class="v down">${fmt(s.e)}</div><div class="s">${dE!=null?`${dE>=0?"↑":"↓"} ${Math.abs(dE).toFixed(0)}% عن الشهر اللي فات`:""}</div></div>
    <div class="pbox"><div class="k">معدل الادخار</div><div class="v">${rate==null?"—":Math.round(rate*100)+"%"}</div><div class="s">${rate==null?"مفيش دخل مسجّل":rate>=0.2?"ممتاز، فوق 20%":"الهدف 20% أو أكتر"}</div></div>
    <div class="pbox"><div class="k">متوسط الصرف اليومي</div><div class="v">${fmt(avg)}</div><div class="s">${cur?`توقع آخر الشهر ≈ ${fmt(avg*daysIn(mk))}`:`على ${days} يوم`}</div></div></div></div>
  <div class="panel"><div class="ph"><h3>المصروف حسب التصنيف</h3></div>
   ${ec.length?`<div class="ov">${ring(ec.map(r=>({v:r.v,c:r.cat.c})),s.e,"المصروف",s.e>=1e6?(s.e/1e6).toFixed(2)+"M":s.e>=1000?(s.e/1000).toFixed(1)+"k":fmt(s.e))}
    <div class="list">${ec.map(r=>{const p=pc[r.c]||0;const d=chg(r.v,p);return `<button type="button" class="row" data-m="cat:${r.c}"><span class="ic" style="background:${r.cat.c}22;border-color:${r.cat.c}55">${r.cat.i}</span><div class="mid"><b>${esc(r.cat.n)}</b><div class="pbar"><i style="width:${r.v/ec[0].v*100}%;background:${r.cat.c}"></i></div><span class="small muted">${(r.v/s.e*100).toFixed(0)}%${d!=null?` · <span class="${d>10?"down":d<-10?"up":""}">${d>=0?"↑":"↓"}${Math.abs(d).toFixed(0)}%</span> عن اللي فات`:p===0&&pv.e?" · جديد الشهر ده":""}</span></div><span class="amt num">${fmt(r.v)}</span></button>`}).join("")}</div></div>`
    :`<div class="empty">مفيش مصروفات مسجّلة في ${mLabel(mk)}.</div>`}</div>
  <div class="panel"><div class="ph"><h3>آخر 6 شهور</h3><span class="legend"><span><span class="dot" style="background:#5CBF8D"></span>دخل</span><span><span class="dot" style="background:#E06A5F"></span>مصروف</span></span></div>${bars(months)}
   <div class="small muted" style="margin-top:6px">متوسط صافي الادخار الشهري: <b class="num ${avgSave>=0?"up":"down"}">${fmt(avgSave)}</b> ج${H().effExp()?` · المصروف الشهري المستخدم في حسابات الحصن: <b class="num">${fmt(H().effExp())}</b>${avgExp()&&S().settings.autoExp!==false?" (من معاملاتك)":" (يدوي)"}`:""}</div></div>
  ${ic.length?`<div class="panel"><div class="ph"><h3>مصادر الدخل</h3></div><div class="list">${ic.map(r=>`<div class="row"><span class="ic" style="background:${r.cat.c}22;border-color:${r.cat.c}55">${r.cat.i}</span><div class="mid"><b>${esc(r.cat.n)}</b><span class="small muted">${(r.v/s.i*100).toFixed(0)}%</span></div><span class="amt num up">${fmt(r.v)}</span></div>`).join("")}</div></div>`:""}
  ${top.length?`<div class="panel"><div class="ph"><h3>أكبر 5 مصروفات</h3></div><div class="list">${top.map(txRow).join("")}</div></div>`:""}
  <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="button" data-m="csv">تصدير الشهر CSV</button></div>`}

/* ── TRANSACTION SHEET ─────────────────────── */
let last={t:"e",ac:null};
function openTx(old,preset){
  if(!accts().length){H().toast("ضيف حساب الأول (كاش أو بنك) برصيده الحالي.");H().openForm("cash",{type:"cash"},o=>{if(!String(o.label||"").trim())return "اكتب اسم الحساب";S().cash.push({id:uid(),...o});H().commit();openTx(null,preset)});return}
  const st=old?{...old,a:String(old.a)}:{t:(preset&&preset.t)||last.t||"e",a:"",c:preset&&preset.c||null,ac:acctOf(last.ac)?last.ac:accts()[0].id,to:null,d:today(),n:""};
  if(st.t==="x"&&!st.to)st.to=(accts().find(a=>a.id!==st.ac)||{}).id||null;
  const draw=()=>{const isX=st.t==="x";const C2=isX?[]:cats(st.t);const v=calcExpr(st.a);
    $("#modalRoot").innerHTML=`<div class="scrim" id="scrim"><form class="modal sheet txs t-${st.t}" id="txf" autocomplete="off"><div class="grab"></div>
     <div class="seg seg3">${[["e","مصروف"],["i","دخل"],["x","تحويل"]].map(([k,n])=>`<button type="button" data-tt="${k}" class="${st.t===k?"on":""}">${n}</button>`).join("")}</div>
     <div class="amtbox"><input id="txa" inputmode="decimal" placeholder="0" value="${esc(st.a)}" aria-label="المبلغ"><span>ج.م</span></div>
     <div class="calcrow">${["+","−","×","÷"].map(o=>`<button type="button" data-op="${o}">${o}</button>`).join("")}<span id="txv" class="small muted">${v!=null&&/[+\-*/×÷−]/.test(st.a.slice(1))?"= "+fmt(v,2):""}</span></div>
     ${isX?"":`<div class="catgrid">${C2.map(c=>`<button type="button" data-cc="${c.id}" class="${st.c===c.id?"on":""}" style="--cc:${c.c}"><span>${c.i}</span><small>${esc(c.n)}</small></button>`).join("")}<button type="button" data-cc="+" class="addc"><span>＋</span><small>تصنيف جديد</small></button></div>`}
     <div class="fields">
      <label><span>${isX?"من حساب":"الحساب"}</span><select id="txac">${accts().map(a=>`<option value="${a.id}" ${a.id===st.ac?"selected":""}>${acctIcon(a)} ${esc(a.label)} (${fmt(a.amount)})</option>`).join("")}</select></label>
      ${isX?`<label><span>إلى حساب</span><select id="txto">${accts().map(a=>`<option value="${a.id}" ${a.id===st.to?"selected":""}>${acctIcon(a)} ${esc(a.label)}</option>`).join("")}</select></label>`:`<label><span>التاريخ</span><input type="date" id="txd" value="${esc(st.d)}"></label>`}
      ${isX?`<label><span>التاريخ</span><input type="date" id="txd" value="${esc(st.d)}"></label>`:""}
      <label class="${isX?"":"full"}"><span>ملاحظة</span><input type="text" id="txn" value="${esc(st.n)}" placeholder="${st.t==="e"?"غدا مع الشغل، فاتورة أكتوبر…":"اختياري"}"></label>
     </div>
     <div class="mfoot"><button class="btn gold" type="submit">حفظ</button>${old?`<button class="btn danger" type="button" id="txdel">حذف</button>`:`<button class="btn" type="button" id="txmore">حفظ وإضافة تاني</button>`}<button class="btn ghost" type="button" id="mcancel">إلغاء</button><span class="small down" id="merr"></span></div>
    </form></div>`;
    const a=$("#txa");a.oninput=()=>{st.a=a.value;const v2=calcExpr(st.a);$("#txv").textContent=v2!=null&&/[+\-*/×÷−]/.test(normNum(st.a).slice(1))?"= "+fmt(v2,2):""};
    const sync=()=>{st.ac=$("#txac").value;st.d=$("#txd").value;st.n=$("#txn").value;if($("#txto"))st.to=$("#txto").value};
    $$("#txf [data-tt]").forEach(b=>b.onclick=()=>{sync();st.t=b.dataset.tt;st.c=null;if(st.t==="x"&&(!st.to||st.to===st.ac))st.to=(accts().find(x=>x.id!==st.ac)||{}).id||null;draw()});
    $$("#txf [data-op]").forEach(b=>b.onclick=()=>{a.value+=b.dataset.op;a.oninput();a.focus()});
    $$("#txf [data-cc]").forEach(b=>b.onclick=()=>{sync();if(b.dataset.cc==="+"){newCat(st.t,id=>{st.c=id;draw()});return}st.c=b.dataset.cc;$$("#txf [data-cc]").forEach(x=>x.classList.toggle("on",x===b))});
    const close=()=>{$("#modalRoot").innerHTML=""};$("#mcancel").onclick=close;$("#scrim").onclick=e=>{if(e.target.id==="scrim")close()};
    const save=more=>{sync();const amt=calcExpr(st.a);const err=m=>{$("#merr").textContent=m;return false};
      if(!(amt>0))return err("اكتب مبلغ صحيح");if(st.t!=="x"&&!st.c)return err("اختار التصنيف");if(st.t==="x"&&st.to===st.ac)return err("اختار حسابين مختلفين");if(!st.d)return err("التاريخ مطلوب");
      const x={id:old?old.id:uid(),d:st.d,t:st.t,a:amt,c:st.t==="x"?null:st.c,ac:st.ac,to:st.t==="x"?st.to:null,n:st.n.trim()};if(old&&old.rec)x.rec=old.rec;
      saveTx(x,old);last={t:st.t,ac:st.ac};H().commit();if(st.t==="e")budgetToast(x);
      if(more){st.a="";st.n="";draw();setTimeout(()=>$("#txa")?.focus(),30);H().toast("اتسجّلت ✓")}else close();return true};
    $("#txf").onsubmit=e=>{e.preventDefault();save(false)};
    $("#txmore")&&($("#txmore").onclick=()=>save(true));
    $("#txdel")&&($("#txdel").onclick=e=>{if(!H().arm(e.target))return;delTx(old.id);H().commit();close();H().toast("اتحذفت")});
    if(!old)setTimeout(()=>a.focus(),40)};
  draw()}
function budgetToast(x){const mk=mkOf(x.d);const r=budgetRows(mk).find(r=>r.c===x.c);if(!r)return;const q=r.sp/r.lim;
  if(q>1)notify(`${r.cat.n}: عدّيت الميزانية`,`صرفت ${fmt(r.sp)} من ${fmt(r.lim)} ج.`);else if(q>=.8&&(r.sp-N(x.a))/r.lim<.8)notify(`${r.cat.n}: وصلت ${Math.round(q*100)}%`,`فاضل ${fmt(r.lim-r.sp)} ج للشهر.`)}
function notify(t,b){H().toast(t+" — "+b);try{if("Notification" in window&&Notification.permission==="granted"&&document.hidden)navigator.serviceWorker?.ready.then(r=>r.showNotification(t,{body:b,icon:"icons/icon-192.png",lang:"ar",dir:"rtl"}))}catch(e){}}
function newCat(t,done){const F=H().FORMS;F.cat={t:t==="i"?"تصنيف دخل جديد":"تصنيف مصروف جديد",f:[["n","الاسم","text",1],["i","إيموجي (اختياري)","text"]]};
  H().openForm("cat",{i:t==="i"?"💰":"🏷️"},o=>{const n=String(o.n||"").trim();if(!n)return "اكتب الاسم";const c={id:"c"+uid(),t,n,i:String(o.i||"").trim().slice(0,4)||"🏷️",c:["#C9A24E","#6E8BD6","#62C597","#B07CC6","#E2A541","#E07F9A"][S().cats.length%6]};S().cats.push(c);H().commit(false);setTimeout(()=>done&&done(c.id),0)})}

/* ── small forms (reuse the core modal) ────── */
function sel(arr){return arr.map(c=>[c.id,c.i+" "+c.n])}
function budgetForm(c){const F=H().FORMS;const B=S().budgets;const isNew=!c;
  F.blim={t:isNew?"ميزانية جديدة":"ميزانية: "+catOf(c).n,f:[...(isNew?[["c","التصنيف","select",1,sel(cats("e").filter(x=>!N(B[x.id])))]]:[]),["lim","الحد الشهري (ج) — صفر يلغيها","number"]]};
  H().openForm("blim",{c:"",lim:c?B[c]:""},o=>{const k=c||o.c;if(!k)return "اختار التصنيف";if(N(o.lim)>0)B[k]=N(o.lim);else delete B[k];H().commit()})}
function suggestBudgets(){const cur=mkOf(today());const tot={};let n=0;
  for(let k=1;k<=3;k++){const L=byCat(addM(cur,-k));if(L.length)n++;L.forEach(r=>tot[r.c]=(tot[r.c]||0)+r.v)}
  if(!n){const L=byCat(cur);if(!L.length){H().toast("محتاج معاملات مسجّلة الأول عشان أقترح.");return}const f=daysIn(cur)/Math.max(1,+today().slice(8,10));L.forEach(r=>tot[r.c]=r.v*f);n=1}
  const B=S().budgets;let k=0;Object.entries(tot).forEach(([c,v])=>{if(c==="sav"||N(B[c]))return;const x=Math.ceil(v/n*1.05/50)*50;if(x>0){B[c]=x;k++}});
  H().commit();H().toast(k?`اتضاف ${k} ميزانية = متوسط مصروفك + 5% (عدّلها براحتك)`:"كل التصنيفات ليها ميزانية بالفعل")}
function recForm(r){const F=H().FORMS;const isNew=!r;const v=r?{...r,auto:r.auto?"1":""}:{t:"e",day:+today().slice(8,10),start:today(),auto:"",ac:accts()[0]?.id||""};
  F.rec={t:isNew?"معاملة متكررة":"تعديل: "+r.n,f:[["n","الاسم (الإيجار، النت، المرتب…)","text",1],["t","النوع","select",0,[["e","مصروف"],["i","دخل"]]],["a","المبلغ","number"],["c","التصنيف","select",0,sel(cats("e")).concat(sel(cats("i")))],["ac","الحساب","select",0,accts().map(a=>[a.id,a.label])],["day","يوم الشهر","number"],["start","يبدأ من","date"],["auto","طريقة التسجيل","select",1,[["","تذكير: أأكده بنفسي"],["1","تلقائي في ميعاده"]]]]};
  H().openForm("rec",v,o=>{if(!String(o.n||"").trim())return "اكتب الاسم";if(!(N(o.a)>0))return "اكتب المبلغ";if(!(N(o.day)>=1&&N(o.day)<=31))return "اليوم من 1 لـ 31";
    const ci=cats(o.t).some(c=>c.id===o.c);if(!ci)return o.t==="i"?"اختار تصنيف دخل":"اختار تصنيف مصروف";
    const it=r||{id:uid()};Object.assign(it,{n:String(o.n).trim(),t:o.t,a:N(o.a),c:o.c,ac:o.ac,day:N(o.day),start:o.start||today(),auto:!!o.auto});if(isNew)S().rec.push(it);runRecurringSilent();H().commit()});
  if(r){setTimeout(()=>{const f=$(".mfoot");if(f){const b=document.createElement("button");b.type="button";b.className="btn danger";b.textContent="حذف";b.onclick=()=>{if(!H().arm(b))return;S().rec=S().rec.filter(x=>x.id!==r.id);$("#modalRoot").innerHTML="";H().commit()};f.insertBefore(b,f.children[1])}},0)}}
function runRecurringSilent(){const t=today();for(const r of S().rec||[]){if(!r.auto)continue;let g=0;while(nextDue(r)<=t&&g++<36)postRec(r,nextDue(r))}}
function goalForm(g){const F=H().FORMS;F.sg={t:g?"تعديل الهدف":"هدف ادخار جديد",f:[["n","الهدف","text",1],["target","المبلغ المطلوب","number"],["saved","المتجمّع لحد دلوقتي","number"],["due","التاريخ المستهدف","date"]]};
  H().openForm("sg",g||{saved:0},o=>{if(!String(o.n||"").trim())return "اكتب اسم الهدف";if(!(N(o.target)>0))return "اكتب المبلغ";const it=g||{id:uid(),log:[]};Object.assign(it,{n:String(o.n).trim(),target:N(o.target),saved:N(o.saved),due:o.due});if(!g)S().sg.push(it);H().commit()});
  if(g)setTimeout(()=>{const f=$(".mfoot");if(f){const b=document.createElement("button");b.type="button";b.className="btn danger";b.textContent="حذف";b.onclick=()=>{if(!H().arm(b))return;S().sg=S().sg.filter(x=>x.id!==g.id);$("#modalRoot").innerHTML="";H().commit()};f.insertBefore(b,f.children[1])}},0)}
function goalMove(g,sg){const F=H().FORMS;F.gmv={t:(sg>0?"إيداع في ":"سحب من ")+g.n,f:[["a","المبلغ","number"],["d","التاريخ","date"]]};
  H().openForm("gmv",{d:today()},o=>{if(!(N(o.a)>0))return "اكتب المبلغ";g.saved=Math.max(0,N(g.saved)+sg*N(o.a));(g.log=g.log||[]).push({d:o.d,a:sg*N(o.a)});H().commit();if(N(g.saved)>=N(g.target))H().toast("🎉 الهدف اكتمل، بارك الله لك")})}
function debtPay(d){const F=H().FORMS;const owed=d.dir==="owed";
  F.dpay={t:(owed?"تحصيل من ":"سداد: ")+d.label,f:[["a","المبلغ","number"],["ac",owed?"اتحصّل في حساب":"اتدفع من حساب","select",0,[["","بدون (تعديل الرصيد بس)"]].concat(accts().map(a=>[a.id,a.label]))],["d","التاريخ","date"]]};
  H().openForm("dpay",{a:N(d.amount),ac:accts()[0]?.id||"",d:today()},o=>{const a=N(o.a);if(!(a>0))return "اكتب المبلغ";if(a>N(d.amount)+0.01)return "أكبر من المتبقي ("+fmt(d.amount)+")";
    d.amount=Math.round((N(d.amount)-a)*100)/100;(d.log=d.log||[]).push({d:o.d,a});
    if(o.ac)saveTx({id:uid(),d:o.d,t:owed?"i":"e",a,c:owed?"refund":"debt",ac:o.ac,n:(owed?"تحصيل: ":"سداد: ")+d.label});H().commit();H().toast(N(d.amount)?`فاضل ${fmt(d.amount)} ج`:"اتقفل بالكامل ✓")})}

/* ── backup / CSV ──────────────────────────── */
async function deliver(name,blob){const file=new File([blob],name,{type:blob.type});
  try{if(navigator.canShare&&navigator.canShare({files:[file]})&&matchMedia("(pointer:coarse)").matches){await navigator.share({files:[file],title:name});return true}}catch(e){if(e&&e.name==="AbortError")return false}
  const u=URL.createObjectURL(blob);const a=document.createElement("a");a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),4000);return true}
async function backup(){const data={app:"hisn",v:2,exportedAt:new Date().toISOString(),S:H().S,HIST:H().HIST};
  const ok=await deliver(`hisn-backup-${today()}.json`,new Blob([JSON.stringify(data)],{type:"application/json"}));if(ok){ls.set("lastBackup",new Date().toISOString());H().toast("اتعملت النسخة. احفظها في Drive أو مكان آمن.");H().render()}}
function csv(list,name){const q=v=>{const s=String(v??"");return /[",\n]/.test(s)?`"${s.replace(/"/g,'""')}"`:s};const T={e:"مصروف",i:"دخل",x:"تحويل"};
  const rows=[["التاريخ","النوع","التصنيف","المبلغ","الحساب","إلى حساب","ملاحظة"]].concat(list.slice().sort((a,b)=>a.d.localeCompare(b.d)).map(x=>[x.d,T[x.t],x.t==="x"?"":catOf(x.c).n,x.a,acctName(x.ac),x.to?acctName(x.to):"",x.n||""]));
  deliver(name,new Blob(["﻿"+rows.map(r=>r.map(q).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"}))}
function importFile(){const inp=document.createElement("input");inp.type="file";inp.accept=".json,application/json";
  inp.onchange=async()=>{const f=inp.files[0];if(!f)return;let o;try{o=JSON.parse(await f.text())}catch(e){H().toast("الملف مش نسخة صالحة.");return}
    const st=o&&o.S&&typeof o.S==="object"?o.S:(o&&(o.gold||o.funds||o.tx)?o:null);if(!st){H().toast("الملف مش نسخة من الحصن.");return}
    const cnt=k=>Array.isArray(st[k])?st[k].length:0;
    $("#modalRoot").innerHTML=`<div class="scrim" id="scrim"><div class="modal sheet"><div class="grab"></div><h3>استرجاع نسخة</h3>
     <p class="muted small">النسخة بتاريخ ${esc(o.exportedAt?H().dLabel(o.exportedAt.slice(0,10)):o.at?H().dLabel(String(o.at).slice(0,10)):st.updatedAt?H().dLabel(String(st.updatedAt).slice(0,10)):"غير معروف")} وفيها: ${cnt("gold")} قطعة ذهب · ${cnt("funds")} صندوق · ${cnt("certs")} شهادة · ${cnt("cash")} حساب · ${cnt("tx")} معاملة.</p>
     <p class="small" style="color:var(--amber)">البيانات الحالية على الجهاز هتتبدّل بالنسخة دي (بنحتفظ بنسخة من الحالية تقدر ترجعلها من الإعدادات).</p>
     <div class="mfoot"><button class="btn gold" type="button" id="impok">استرجع</button><button class="btn ghost" type="button" id="mcancel">إلغاء</button></div></div></div>`;
    $("#mcancel").onclick=()=>$("#modalRoot").innerHTML="";
    $("#impok").onclick=()=>{ls.set("prevState",{S:H().S,HIST:H().HIST,at:new Date().toISOString()});H().setState(st,o.HIST);$("#modalRoot").innerHTML="";runRecurring();H().toast("اترجعت البيانات ✓")}};
  inp.click()}

/* ── app lock (PIN) ─────────────────────────── */
async function sha(s){const b=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s));return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,"0")).join("")}
const lockCfg=()=>ls.get("lock");
let hiddenAt=0;
function showLock(){const cfg=lockCfg();if(!cfg)return;document.documentElement.classList.add("locked");let pin="";const ov=$("#lock");
  const paint=(msg)=>{ov.innerHTML=`<div class="lockin"><svg viewBox="0 0 40 40" width="52" height="52" aria-hidden="true"><g fill="none" stroke="#C9A24E" stroke-width="1.4"><rect x="8" y="8" width="24" height="24"/><rect x="8" y="8" width="24" height="24" transform="rotate(45 20 20)"/><circle cx="20" cy="20" r="5" fill="#2F8F63" stroke="#62C597"/></g></svg>
    <b>حصن السعودي</b><span class="small muted">${esc(msg||"اكتب الرقم السري")}</span><div class="pdots">${[0,1,2,3,4,5].slice(0,Math.max(4,cfg.len||4)).map(i=>`<i class="${i<pin.length?"on":""}"></i>`).join("")}</div>
    <div class="keypad">${[1,2,3,4,5,6,7,8,9,"",0,"⌫"].map(k=>k===""?"<span></span>":`<button type="button" data-k="${k}">${k}</button>`).join("")}</div>
    <button type="button" class="btn sm ghost" data-k="forgot">نسيت الرقم؟</button></div>`};
  paint();ov.hidden=false;
  ov.onclick=async e=>{const b=e.target.closest("[data-k]");if(!b)return;const k=b.dataset.k;
    if(k==="forgot"){paint("مفيش طريقة تفتح بيها من غير الرقم. لو عندك نسخة احتياطية: امسح بيانات الموقع من إعدادات المتصفح ورجّعها.");return}
    if(k==="⌫"){pin=pin.slice(0,-1);paint();return}
    if(pin.length>=8)return;pin+=k;paint();
    if(pin.length>=(cfg.len||4)){const h=await sha(cfg.salt+pin);if(h===cfg.h){ov.hidden=true;ov.innerHTML="";document.documentElement.classList.remove("locked")}else{pin="";paint("رقم غلط، جرّب تاني");ov.querySelector(".pdots")?.classList.add("shake")}}}}
function setPin(){const F=H().FORMS;F.pin={t:lockCfg()?"تغيير الرقم السري":"قفل التطبيق برقم سري",f:[["p1","الرقم السري (4 لـ 8 أرقام)","password"],["p2","تأكيد الرقم","password"],["after","يقفل بعد ما تسيبه","select",1,[["0","فورًا"],["1","دقيقة"],["5","5 دقايق"]]]]};
  H().openForm("pin",{after:"1"},o=>{const p=normNum(o.p1);if(!/^\d{4,8}$/.test(p))return "من 4 لـ 8 أرقام";if(p!==normNum(o.p2))return "الرقمين مش زي بعض";if(!crypto.subtle)return "القفل محتاج التطبيق يتفتح من رابط https";
    const salt=uid()+uid();sha(salt+p).then(h=>{ls.set("lock",{h,salt,len:p.length,after:N(o.after)});H().toast("القفل اتفعّل ✓");openMenu()})});
  setTimeout(()=>$$("#mform input[type=password]").forEach(i=>i.setAttribute("inputmode","numeric")),20)}

/* ── settings menu ─────────────────────────── */
let installEvt=null;addEventListener("beforeinstallprompt",e=>{e.preventDefault();installEvt=e});
const standalone=()=>matchMedia("(display-mode: standalone)").matches||navigator.standalone===true;
function openMenu(){const lb=ls.get("lastBackup");const lc=lockCfg();const p=H().S.prices;const prev=ls.get("prevState");
  const ios=/iphone|ipad|ipod/i.test(navigator.userAgent);
  $("#modalRoot").innerHTML=`<div class="scrim" id="scrim"><div class="modal sheet menu"><div class="grab"></div><div class="ph"><h3>الإعدادات</h3><button class="btn sm ghost" type="button" id="mcancel">إغلاق</button></div>
   <section><h4>النسخ الاحتياطي</h4><p class="small muted">بياناتك متخزنة على الموبايل ده بس، مفيش سيرفر. ${lb?"آخر نسخة: "+H().dLabel(lb.slice(0,10)):"لسه ما عملتش نسخة."}</p>
    <div class="mrow"><button class="btn gold sm" data-m="backup" type="button">نسخة احتياطية</button><button class="btn sm" data-m="import" type="button">استرجاع نسخة</button><button class="btn sm" data-m="csvall" type="button">المعاملات CSV</button>${prev?`<button class="btn sm ghost" data-m="undoimport" type="button">رجوع للبيانات قبل آخر استرجاع</button>`:""}</div></section>
   <section><h4>الأمان</h4><p class="small muted">${lc?"التطبيق مقفول برقم سري.":"أي حد ماسك الموبايل يقدر يفتح التطبيق."} القفل بيمنع الفتح من الواجهة، والبيانات نفسها على الجهاز بدون تشفير.</p>
    <div class="mrow"><button class="btn sm ${lc?"":"gold"}" data-m="pin" type="button">${lc?"تغيير الرقم":"فعّل القفل"}</button>${lc?`<button class="btn sm ghost danger" data-m="nopin" type="button">إلغاء القفل</button>`:""}</div></section>
   <section><h4>سعر الذهب</h4><p class="small muted">آخر سعر: ع24 <b class="num">${H().fmt(p.k24.buy)}</b> · ${esc(p.src||"—")}${p.at?" · "+new Date(p.at).toLocaleString("ar-EG-u-nu-latn",{timeZone:H().TZ,dateStyle:"medium",timeStyle:"short"}):""}.<br>التحديث بيجيب السعر العالمي ويطبّق عليه فرق السوق المحلي من آخر سعر جلا كتبته يدوي. اكتب سعر الجلا يدوي كل فترة عشان التقدير يفضل دقيق.</p>
    <div class="mrow"><button class="btn gold sm" data-m="gold" type="button">تحديث من الإنترنت</button><button class="btn sm" data-m="goldman" type="button">إدخال سعر الجلا يدوي</button></div></section>
   <section><h4>الثروة والدخل</h4><p class="small muted">المرتب، المصروف الشهري، نسب التوزيع المستهدفة، التضخم، ومصدر المصروف (تلقائي من المعاملات أو يدوي).</p>
    <div class="mrow"><button class="btn sm" data-m="wset" type="button">إعدادات الثروة</button><button class="btn sm" data-m="cats" type="button">تصنيفاتي</button>${"Notification" in window&&Notification.permission==="default"?`<button class="btn sm" data-m="notif" type="button">فعّل الإشعارات</button>`:""}</div></section>
   ${standalone()?"":`<section><h4>تثبيت على الموبايل</h4><p class="small muted">${ios?"من Safari: زرار المشاركة ⬆︎ ← «إضافة إلى الشاشة الرئيسية».":"من Chrome: القائمة ⋮ ← «تثبيت التطبيق» أو «إضافة للشاشة الرئيسية»."} بعد كده يفتح كتطبيق مستقل ويشتغل من غير نت.</p>${installEvt?`<div class="mrow"><button class="btn gold sm" data-m="install" type="button">ثبّت الآن</button></div>`:""}</section>`}
   <section><h4>منطقة خطر</h4><div class="mrow"><button class="btn sm ghost danger" data-m="wipe" type="button">مسح كل البيانات من الجهاز</button></div></section>
   <p class="small faint" style="text-align:center;margin:10px 0 0">حصن السعودي · نسخة <span class="num">${esc(window.HISN_VERSION||"")}</span></p></div></div>`;
  $("#mcancel").onclick=()=>$("#modalRoot").innerHTML="";$("#scrim").onclick=e=>{if(e.target.id==="scrim")$("#modalRoot").innerHTML=""}}
function catsManager(){const C2=S().cats||[];$("#modalRoot").innerHTML=`<div class="scrim" id="scrim"><div class="modal sheet"><div class="grab"></div><div class="ph"><h3>تصنيفاتي</h3><button class="btn sm ghost" type="button" id="mcancel">إغلاق</button></div>
  ${C2.length?`<div class="list">${C2.map(c=>`<div class="row"><span class="ic">${esc(c.i)}</span><div class="mid"><b>${esc(c.n)}</b><span class="small muted">${c.t==="i"?"دخل":"مصروف"}</span></div><button class="btn sm ghost danger" type="button" data-m="delcat:${c.id}">حذف</button></div>`).join("")}</div>`:`<p class="small muted">مفيش تصنيفات مخصصة. التصنيفات الأساسية ثابتة.</p>`}
  <div class="mrow" style="margin-top:12px"><button class="btn sm gold" type="button" data-m="ncat:e">+ تصنيف مصروف</button><button class="btn sm" type="button" data-m="ncat:i">+ تصنيف دخل</button></div></div></div>`;$("#mcancel").onclick=()=>$("#modalRoot").innerHTML=""}

/* ── navigation ────────────────────────────── */
const VIEWS=["home","tx","reports","budget","wealth"];
function go(v,push=true){if(!VIEWS.includes(v))v="home";V.view=v;$$(".view").forEach(s=>s.classList.toggle("on",s.id==="v-"+v));$$(".bnav [data-vw]").forEach(b=>b.setAttribute("aria-current",b.dataset.vw===v?"page":"false"));
  document.body.dataset.view=v;try{sessionStorage.setItem("hisn:view",v)}catch(e){}
  if(push&&history.state?.v!==v)history.pushState({v},"");window.scrollTo(0,0);if(v==="wealth")dispatchEvent(new Event("resize"))}
addEventListener("popstate",e=>{if($("#modalRoot")?.innerHTML){$("#modalRoot").innerHTML="";history.pushState({v:V.view},"");return}go(e.state?.v||"home",false)});

document.addEventListener("click",e=>{const b=e.target.closest("[data-m],[data-vw]");if(!b)return;
  if(b.dataset.vw){go(b.dataset.vw);return}
  const [k,arg]=b.dataset.m.split(/:(.*)/s);
  switch(k){
   case "go":go(arg);break;
   case "fab":openTx(null,V.view==="tx"&&V.ft&&V.ft!=="x"?{t:V.ft}:null);break;
   case "tx":{const x=S().tx.find(y=>y.id===arg);if(x)openTx(x);break}
   case "xfer":if(accts().length<2){H().toast("محتاج حسابين على الأقل للتحويل.");break}openTx(null,{t:"x"});setTimeout(()=>{$('[data-tt="x"]')?.click()},0);break;
   case "acct":V.fa=arg;V.mk=mkOf(today());go("tx");renderTx();break;
   case "clr":V[arg]="";renderTx();break;
   case "cat":V.fc=arg;go("tx");renderTx();break;
   case "mk":V.mk=addM(V.mk,N(arg));if(V.mk>mkOf(today()))V.mk=mkOf(today());renderMoney();break;
   case "badd":budgetForm(null);break;
   case "bedit":budgetForm(arg);break;
   case "btotal":{const F=H().FORMS;F.btot={t:"الحد الكلي للمصروف الشهري",f:[["lim","الحد (صفر = مجموع حدود التصنيفات)","number"]]};H().openForm("btot",{lim:N(S().budgets._total)||""},o=>{if(N(o.lim)>0)S().budgets._total=N(o.lim);else delete S().budgets._total;H().commit()});break}
   case "bsuggest":suggestBudgets();break;
   case "radd":if(!accts().length){H().toast("ضيف حساب الأول.");break}recForm(null);break;
   case "redit":recForm((S().rec||[]).find(r=>r.id===arg));break;
   case "post":{const r=(S().rec||[]).find(x=>x.id===arg);if(r){postRec(r,nextDue(r));H().commit();H().toast(`اتسجّل: ${r.n}`)}break}
   case "gadd":goalForm(null);break;
   case "gedit":goalForm(S().sg.find(g=>g.id===arg));break;
   case "gdep":goalMove(S().sg.find(g=>g.id===arg),1);break;
   case "gwd":goalMove(S().sg.find(g=>g.id===arg),-1);break;
   case "dpay":debtPay(S().debts.find(d=>d.id===arg));break;
   case "csv":csv(txIn(V.mk),`hisn-${V.mk}.csv`);break;
   case "csvall":if(!S().tx.length){H().toast("مفيش معاملات.");break}csv(S().tx,`hisn-transactions-${today()}.csv`);break;
   case "backup":backup();break;
   case "import":importFile();break;
   case "undoimport":{const p=ls.get("prevState");if(p&&H().arm(b)){H().setState(p.S,p.HIST);localStorage.removeItem(KEY+"prevState");$("#modalRoot").innerHTML="";H().toast("رجعت البيانات اللي كانت قبل الاسترجاع")}break}
   case "pin":setPin();break;
   case "nopin":if(H().arm(b)){localStorage.removeItem(KEY+"lock");openMenu();H().toast("القفل اتلغى")}break;
   case "gold":$("#modalRoot").innerHTML="";H().fetchGalla(true);break;
   case "goldman":H().manualPrice();break;
   case "wset":H().openSettings();break;
   case "cats":catsManager();break;
   case "ncat":newCat(arg,()=>catsManager());break;
   case "delcat":if(H().arm(b)){S().cats=S().cats.filter(c=>c.id!==arg);H().commit();catsManager()}break;
   case "notif":Notification.requestPermission().then(()=>openMenu());break;
   case "install":installEvt&&installEvt.prompt();installEvt=null;break;
   case "wipe":if(H().arm(b)&&confirm("هيتمسح كل حاجة من الجهاز ده (ذهب، شهادات، معاملات…). متأكد؟ اعمل نسخة احتياطية الأول.")){Object.keys(localStorage).filter(x=>x.startsWith(KEY)).forEach(x=>localStorage.removeItem(x));location.reload()}break;
  }});
document.addEventListener("keydown",e=>{if((e.key==="Enter"||e.key===" ")&&e.target.matches?.(".nwcard")){e.preventDefault();go("wealth")}});

/* ── render glue ───────────────────────────── */
function renderMoney(){if(!V.mk)V.mk=mkOf(today());renderHome();renderTx();renderBudget();renderReports()}

/* budget, bills and debt signals inside the core "advisor" rules */
function rulesExtra(){const A=[];if(!window.HISN)return A;const mk=mkOf(today());
  budgetRows(mk).filter(r=>r.sp>r.lim).forEach(r=>A.push({mx:1,lv:"warn",t:`ميزانية ${r.cat.n} اتعدّت`,b:`صرفت ${fmt(r.sp)} من ${fmt(r.lim)} ج في ${mLabel(mk)}.`,a:"وقّف الصرف في التصنيف ده لآخر الشهر أو ارفع الحد بوعي."}));
  pendingRec().forEach(r=>A.push({mx:1,lv:"info",t:`مستحق: ${r.n} (${fmt(r.a)} ج)`,b:`ميعاده ${H().dLabel(nextDue(r))}.`,a:"سجّله من الرئيسية."}));
  (S().debts||[]).filter(d=>N(d.amount)>0&&d.due&&H().daysBetween(today(),d.due)<0).forEach(d=>A.push({mx:1,lv:d.dir==="owed"?"info":"critical",t:`${d.dir==="owed"?"فلوس ليك متأخرة":"دين متأخر"}: ${d.label}`,b:`${fmt(d.amount)} ج، ميعاده كان ${H().dLabel(d.due)}.`}));
  return A}
function briefHtml(){const mk=mkOf(today()),pm=addM(mk,-1);const s=sums(mk),p=sums(pm);if(!S().tx.length)return "";
  const top=byCat(mk).slice(0,3).map(r=>`${r.cat.n} ${fmt(r.v)}`).join("، ");const over=budgetRows(mk).filter(r=>r.sp>r.lim);
  return `<h4>المصروفات</h4><ul><li>${mLabel(mk)}: دخل ${fmt(s.i)}، مصروف ${fmt(s.e)}، صافي ${s.n>=0?"+":"−"}${fmt(Math.abs(s.n))}.</li>${p.e?`<li>الشهر اللي فات: مصروف ${fmt(p.e)}، صافي ${p.n>=0?"+":"−"}${fmt(Math.abs(p.n))}.</li>`:""}${top?`<li>أكبر بنود: ${esc(top)}.</li>`:""}${over.length?`<li><strong>ميزانيات متعدّية:</strong> ${esc(over.map(r=>r.cat.n).join("، "))}.</li>`:""}</ul>`}

function init(){if(!V.mk)V.mk=mkOf(today());runRecurringSilent();
  let v="home";try{v=sessionStorage.getItem("hisn:view")||"home"}catch(e){}
  const q=new URLSearchParams(location.search);history.replaceState({v},"",location.pathname);go(v,false);
  if(q.get("add"))setTimeout(()=>openTx(null,{t:q.get("add")==="i"?"i":"e"}),300);
  addEventListener("visibilitychange",()=>{if(document.hidden){hiddenAt=Date.now()}else{const c=lockCfg();if(c&&hiddenAt&&Date.now()-hiddenAt>=N(c.after)*60e3)showLock();if(V.mk&&H())runRecurring()}});
  addEventListener("online",()=>document.body.classList.remove("offline"));addEventListener("offline",()=>document.body.classList.add("offline"));if(!navigator.onLine)document.body.classList.add("offline")}

window.HISN_EXT={init,onRender:renderMoney,avgExp,rulesExtra,briefHtml,openMenu,go};
/* lock before the first paint when a PIN is set */
if(lockCfg())document.documentElement.classList.add("locked");
document.addEventListener("DOMContentLoaded",()=>{if(lockCfg())showLock()});
})();
