/* Custody analytics dashboard — no build step. Renders the server's report model (the same one behind the PDF and
   Excel downloads), so what is on screen is exactly what is exported. Filters are applied on the server. */
(function () {
  "use strict";
  const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
  const SEQ = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
  const UP = "#d03b3b", DOWN = "#256abf";
  const $ = (s) => document.querySelector(s);
  const store = { get: (k) => { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
                  set: (k, v) => { try { sessionStorage.setItem(k, v); } catch (e) { /* storage may be blocked */ } } };

  const UI = {
    ar: { title: "منصة التحليل الإداري", dataset: "الملف المحلل", upload: "رفع ملف Excel", year: "السنة (إن لم تكن في الملف)", drop: "أو اسحب الملف هنا",
      apply: "تطبيق", clear: "مسح", period: "الفترة", branch: "الفرع", category: "البند", all: "الكل", none: "لا شيء", search: "بحث…",
      selected: "محدد", emptyTitle: "ارفع ملف Excel لبدء التحليل",
      emptyText: "يدعم النظام ثلاثة أنواع: قيود تسوية العهد المؤقتة، تحليل مصروفات الفروع، وتحليل مصروفات المركز الرئيسي. كل نوع يُحلل منفصلًا.",
      token: "رمز الدخول", tokenHint: "يلزم عند تفعيل المصادقة على الخادم (Bearer token).", save: "حفظ", showAll: "عرض الكل", rows: "سطر",
      uploaded: "تم رفع الملف وتحليله", layout: "نوع الملف", issues: "ملاحظات جودة", duplicate: "هذا الملف مرفوع من قبل — تم فتحه.",
      failed: "تعذر التنفيذ", unauthorized: "غير مصرح — أدخل رمز الدخول", filtered: "عرض مفلتر", noDatasets: "لا توجد ملفات بعد",
      layouts: { advance_register: "سجل السلف المؤقتة", gl_settlement_lines: "قيود تسوية العهد المؤقتة", monthly_branch_expense: "مصروفات الفروع", monthly_custodian_expense: "مصروفات المركز الرئيسي" },
      month: "الشهر (إن لم يكن في الملف)", processing: "جاري معالجة الملف…", files: "ملفات", roles: { statement: "الكشف (أساسي)", invoice: "الفاتورة (أساسي)", statement_word: "ملف Word (مساند)", evidence: "صور الطابعات (أدلة فقط)", invoice_pdf: "فاتورة Aramex PDF (أساسي)", shipments_xlsx: "كشف الشحنات Excel (أساسي)", contract_reference: "ملحق العقد (مرجع فقط)", paper_distribution: "كشف توزيع الورق" },
      clickHint: "اضغط على عنصر لتصفية التحليل عليه" },
    en: { title: "Management Analytics", dataset: "Analysed file", upload: "Upload Excel", year: "Year (if not in the file)", drop: "or drop the file here",
      apply: "Apply", clear: "Clear", period: "Period", branch: "Branch", category: "Category", all: "All", none: "None", search: "Search…",
      selected: "selected", emptyTitle: "Upload an Excel file to start",
      emptyText: "Three file types are supported: temporary-custody settlement journal, branch expense analysis and Head Office expense analysis. Each is analysed separately.",
      token: "Access token", tokenHint: "Needed when the server has authentication enabled (Bearer token).", save: "Save", showAll: "Show all", rows: "rows",
      uploaded: "File uploaded and analysed", layout: "File type", issues: "data-quality observations", duplicate: "This file was already uploaded — opened it.",
      failed: "Request failed", unauthorized: "Not authorised — enter the access token", filtered: "Filtered view", noDatasets: "No files yet",
      layouts: { advance_register: "Temporary-advance register", gl_settlement_lines: "Temporary-custody settlement journal", monthly_branch_expense: "Branch expenses", monthly_custodian_expense: "Head Office expenses" },
      month: "Month (if not in the file)", processing: "Processing the file…", files: "files", roles: { statement: "Statement (authoritative)", invoice: "Invoice (authoritative)", statement_word: "Word (supporting)", evidence: "Status pages (evidence only)", invoice_pdf: "Aramex invoice PDF (authoritative)", shipments_xlsx: "Shipment sheet Excel (authoritative)", contract_reference: "Contract appendix (reference only)", paper_distribution: "Paper distribution statement" },
      clickHint: "Click an item to filter the analysis to it" },
  };

  const state = { lang: store.get("lang") || "ar", token: store.get("token") || "", datasets: [], dsId: store.get("ds") || null,
                  report: null, filters: {}, tab: "summary", charts: [], modules: [], module: store.get("module") || "custody", poll: null };
  const mod = () => state.modules.find((m) => m.key === state.module) || { key: state.module, label: {}, accepts: [".xlsx"], upload_hint: {}, filters: {} };
  const base = () => `/api/analysis/${state.module}/datasets`;
  const resetFilters = () => { state.filters = {}; };
  const T = () => UI[state.lang];

  // ------------------------------------------------------------------ helpers
  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") n.className = v; else if (k === "html") n.innerHTML = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat()) if (k != null) n.append(k.nodeType ? k : document.createTextNode(String(k)));
    return n;
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function fmt(v, kind) {
    if (v === null || v === undefined || v === "") return kind === "text" ? "" : "—";
    const n = Number(v);
    const loc = (x, d = 0) => x.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });
    if (kind === "money") return loc(Math.round(n));
    if (kind === "smoney") return (n > 0 ? "+" : "") + loc(Math.round(n));
    if (kind === "money3") return loc(n, 3);
    if (kind === "num") return loc(n, 2);
    if (kind === "snum") return (n > 0 ? "+" : "") + loc(n, 2);
    if (kind === "pct") return loc(n, 1) + "%";
    if (kind === "spct") return (n > 0 ? "+" : "") + loc(n, 1) + "%";
    if (kind === "int") return loc(n);
    return String(v);
  }
  const compact = (v) => { const a = Math.abs(v); return a >= 1e6 ? (v / 1e6).toFixed(1) + "M" : a >= 1e4 ? Math.round(v / 1e3) + "k" : Math.round(v).toLocaleString("en-US"); };
  function notice(text, kind) { const n = $("#notice"); if (!text) { n.hidden = true; return; } n.textContent = text; n.className = "notice " + (kind || ""); n.hidden = false; }
  function busy(on) { $("#busy").hidden = !on; }

  async function api(path, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    if (state.token) headers.Authorization = "Bearer " + state.token;
    const res = await fetch(path, Object.assign({}, opts, { headers }));
    if (res.status === 401) { $("#tokenDlg").showModal(); throw new Error(T().unauthorized); }
    if (!res.ok) {
      let msg = res.statusText;
      try { const j = await res.json(); const d = j.detail; msg = typeof d === "string" ? d : (d && d.message) || JSON.stringify(d); res.detailObj = d; } catch (e) { /* not json */ }
      const err = new Error(msg); err.status = res.status; err.detail = res.detailObj; throw err;
    }
    return opts.blob ? res : res.json();
  }

  // ------------------------------------------------------------------ static texts / language
  function applyLang() {
    const t = T(), d = document.documentElement;
    d.lang = state.lang; d.dir = state.lang === "ar" ? "rtl" : "ltr";
    $("#langBtn").textContent = state.lang === "ar" ? "EN" : "ع";
    $("#appTitle").textContent = t.title; document.title = t.title;
    $("#lblDataset").textContent = t.dataset; $("#lblUpload").textContent = t.upload; $("#lblYear").textContent = t.year; $("#lblDrop").textContent = t.drop;
    $("#applyBtn").textContent = t.apply; $("#clearBtn").textContent = t.clear;
    $("#emptyTitle") && ($("#emptyTitle").textContent = t.emptyTitle); $("#emptyText") && ($("#emptyText").textContent = t.emptyText);
    renderModules();
    const mo = $("#monthInput"); if (mo) { mo.parentElement.querySelector("span").textContent = t.month; mo.parentElement.hidden = state.module !== "copiers"; }
    $("#fileInput").setAttribute("accept", (mod().accepts || [".xlsx"]).join(",")); state.module !== "custody" ? $("#fileInput").setAttribute("multiple", "") : $("#fileInput").removeAttribute("multiple");
    const hint = (mod().upload_hint || {})[state.lang]; $("#lblDrop").textContent = hint || t.drop;
    $("#tokenTitle").textContent = t.token; $("#tokenHint").textContent = t.tokenHint; $("#tokenSave").textContent = t.save;
  }

  function renderModules() {
    const bar = $("#moduleTabs"); if (!bar) return; bar.innerHTML = "";
    state.modules.forEach((m) => bar.append(el("button", { class: "mtab" + (m.key === state.module ? " on" : ""), onclick: () => switchModule(m.key) }, m.label[state.lang] || m.key)));
  }
  async function switchModule(key) {
    state.module = key; store.set("module", key); state.dsId = null; store.set("ds", ""); resetFilters(); state.tab = "summary"; notice(""); applyLang(); await init();
  }

  // ------------------------------------------------------------------ datasets
  async function loadDatasets(select) {
    state.datasets = await api(base());
    const sel = $("#datasetSelect");
    sel.innerHTML = "";
    if (!state.datasets.length) sel.append(el("option", { value: "" }, T().noDatasets));
    for (const d of state.datasets) {
      sel.append(el("option", { value: d.id }, d.label || `#${d.id} · ${d.file_name} · ${T().layouts[d.layout] || d.layout}`));
    }
    if (select !== undefined && select !== null) state.dsId = String(select);
    if (!state.datasets.find((d) => String(d.id) === String(state.dsId))) state.dsId = state.datasets.length ? String(state.datasets[0].id) : null;
    sel.value = state.dsId || "";
  }

  async function upload(files) {
    files = [...(files || [])]; if (!files.length) return;
    // authoritative files first (statement, invoice), supporting ones after, so the evidence has its period
    const rank = (f) => (/\.(xlsx|xlsm)$/i.test(f.name) ? 0 : /\.(docx?)$/i.test(f.name) ? 2 : 1);
    files.sort((a, b) => rank(a) - rank(b));
    busy(true); notice("");
    let last = null, msgs = [];
    for (const file of files) {
      const fd = new FormData(); fd.append("file", file);
      const y = $("#yearInput").value; if (y) fd.append("year", y);
      const mo = $("#monthInput") && $("#monthInput").value; if (mo && state.module === "copiers") fd.append("month", mo);
      try {
        const meta = await api(base(), { method: "POST", body: fd });
        last = meta.id; resetFilters();
        const role = meta.uploaded ? (T().roles[meta.uploaded.role] || meta.uploaded.role) : (T().layouts[meta.layout] || meta.layout);
        msgs.push(`✔ ${file.name} → ${role}${meta.issues ? " · " + meta.issues.length + " " + T().issues : ""}`);
      } catch (e) {
        if (e.status === 409 && e.detail && e.detail.dataset_id) { last = e.detail.dataset_id; msgs.push(`↺ ${file.name}: ${e.detail.message || T().duplicate}`); }
        else msgs.push(`✖ ${file.name}: ${e.message}`);
      }
    }
    try {
      if (last !== null) { await loadDatasets(last); store.set("ds", state.dsId); await loadReport(); }
      notice(msgs.join("   |   "), msgs.some((m) => m.startsWith("✖")) ? "err" : "ok");
    } finally { busy(false); $("#fileInput").value = ""; }
  }

  // ------------------------------------------------------------------ report
  const dims = () => (state.report && state.report.meta.filters.dimensions) || [];
  function query() {
    const p = new URLSearchParams({ lang: state.lang });
    dims().forEach((d) => (state.filters[d.key] || []).forEach((x) => p.append(d.param, x)));
    return p.toString();
  }
  async function loadReport() {
    if (!state.dsId) { state.report = null; render(); return; }
    busy(true);
    try {
      const j = await api(`${base()}/${state.dsId}/report?${query()}`);
      state.report = j.report;
      render();
      watchProcessing();
    } catch (e) { notice(`${T().failed}: ${e.message}`, "err"); } finally { busy(false); }
  }

  async function download(kind) {
    busy(true);
    try {
      const res = await api(`${base()}/${state.dsId}/report.${kind}?${query()}`, { blob: true });
      const blob = await res.blob(); const a = el("a", { href: URL.createObjectURL(blob), download: `${state.module}_analysis_${state.dsId}_${state.lang}.${kind}` });
      document.body.append(a); a.click(); a.remove();
    } catch (e) { notice(`${T().failed}: ${e.message}`, "err"); } finally { busy(false); }
  }

  // ------------------------------------------------------------------ render
  function watchProcessing() {  // background OCR of the evidence pages: poll until the item is ready, then reload
    clearTimeout(state.poll);
    if (state.module !== "copiers" || state.dsId === "all") return;
    api(`${base()}/${state.dsId}`).then((m) => { if (m.status === "processing") { state.pollNotice = true; notice(T().processing, "warn"); state.poll = setTimeout(loadReport, 4000); } else if (state.pollNotice) { state.pollNotice = false; notice(""); } }).catch(() => {});
  }

  function render() {
    state.charts.forEach((c) => c.destroy()); state.charts = [];
    const r = state.report, content = $("#content");
    $("#pdfBtn").disabled = $("#xlsxBtn").disabled = !r;
    if (!r) { content.innerHTML = ""; content.append(el("div", { class: "empty", id: "emptyState" }, el("h2", { id: "emptyTitle" }, T().emptyTitle), el("p", { id: "emptyText" }, T().emptyText))); $("#filters").hidden = $("#tabs").hidden = true; return; }
    renderFilters(); renderTabs();
    const sec = r.sections.find((s) => s.key === state.tab) || r.sections[0];
    content.innerHTML = "";
    const body = el("div", { class: "panel-body" });
    if (sec.key === "summary") {
      body.append(el("div", { class: "hint", style: "margin-bottom:10px" }, `${r.title} — ${r.subtitle || ""} · ${r.period_label}`));
    }
    if (sec.kpis.length) body.append(el("div", { class: "kpis" }, sec.kpis.map(kpiCard)));
    if (sec.insights.length) body.append(el("ul", { class: "insights" }, sec.insights.map((i) => el("li", { class: i.severity }, i.text))));
    if (sec.charts.length) {
      const g = el("div", { class: "grid2" });
      sec.charts.forEach((c) => g.append(chartCard(c)));
      body.append(g);
      if (sec.charts.some((c) => c.drill || c.drill_rows || c.drill_cols)) body.append(el("div", { class: "hint", style: "margin:-8px 0 14px" }, T().clickHint));
    }
    sec.tables.filter((t) => t.rows && t.rows.length).forEach((t) => body.append(tableBlock(t)));
    content.append(body);
    if (sec.key === "summary") {
      // the other sections' charts are on their own tabs; nothing else to add here
    }
  }

  function kpiCard(k) {
    const long = String(k.value).length > 14;
    return el("div", { class: "kpi" }, el("div", { class: "l" }, k.label), el("div", { class: "v" + (long ? " sm" : "") }, k.value),
              el("div", { class: "s " + (k.tone || "") }, k.sub || ""));
  }

  // ------------------------------------------------------------------ tabs & filters
  function renderTabs() {
    const tabs = $("#tabs"); tabs.hidden = false; tabs.innerHTML = "";
    state.report.sections.forEach((s) => {
      if (s.key !== "summary" && !s.kpis.length && !s.charts.length && !s.insights.length && !s.tables.some((t) => t.rows && t.rows.length)) return;
      tabs.append(el("button", { class: "tab" + (s.key === state.tab ? " on" : ""), role: "tab", onclick: () => { state.tab = s.key; render(); } }, s.title));
    });
  }

  function dropdown(root, label, items, selected, searchable) {
    root.innerHTML = "";
    const count = selected.size ? ` (${selected.size})` : "";
    const btn = el("button", { class: "btn", type: "button" }, label + count + " ▾");
    const panel = el("div", { class: "panel", hidden: true });
    const list = el("div");
    const draw = (q) => {
      list.innerHTML = "";
      items.filter((i) => !q || i.label.toLowerCase().includes(q.toLowerCase())).slice(0, 400).forEach((i) => {
        const cb = el("input", { type: "checkbox" }); cb.checked = selected.has(i.id);
        cb.addEventListener("change", () => { cb.checked ? selected.add(i.id) : selected.delete(i.id); btn.textContent = label + (selected.size ? ` (${selected.size})` : "") + " ▾"; });
        list.append(el("label", {}, cb, i.label));
      });
    };
    if (searchable) { const s = el("input", { type: "search", placeholder: T().search }); s.addEventListener("input", () => draw(s.value)); panel.append(s); }
    panel.append(el("div", { class: "tools" }, el("a", { onclick: () => { items.forEach((i) => selected.add(i.id)); draw(""); btn.textContent = label + ` (${selected.size}) ▾`; } }, T().all),
                                              el("a", { onclick: () => { selected.clear(); draw(""); btn.textContent = label + " ▾"; } }, T().none)), list);
    draw("");
    btn.addEventListener("click", (e) => { e.stopPropagation(); document.querySelectorAll(".dd .panel").forEach((p) => { if (p !== panel) p.hidden = true; }); panel.hidden = !panel.hidden; });
    panel.addEventListener("click", (e) => e.stopPropagation());
    root.append(btn, panel);
  }
  document.addEventListener("click", () => document.querySelectorAll(".dd .panel").forEach((p) => (p.hidden = true)));

  let pending = {};
  function renderFilters() {
    const ds = dims();
    const f = $("#filters"); f.hidden = !ds.length;
    pending = {};
    ["#ddPeriod", "#ddBranch", "#ddCategory"].forEach((id) => { $(id).innerHTML = ""; });
    const slots = ["#ddPeriod", "#ddBranch", "#ddCategory"];
    ds.forEach((d, i) => {
      pending[d.key] = new Set(state.filters[d.key] || []);
      const root = $(slots[i]); if (!root) return;
      dropdown(root, d.label, d.items, pending[d.key], d.searchable);
    });
    const chips = $("#chips"); chips.innerHTML = "";
    ds.forEach((d) => (state.filters[d.key] || []).forEach((id) => chips.append(el("span", { class: "chip" }, `${d.label}: ${((d.items.find((x) => x.id === id)) || {}).label || id}`,
      el("b", { onclick: () => { state.filters[d.key] = state.filters[d.key].filter((x) => x !== id); loadReport(); } }, "×")))));
  }
  function applyFilters() {
    const next = {}; dims().forEach((d) => { next[d.key] = [...(pending[d.key] || [])]; });
    state.filters = next; loadReport();
  }
  function drill(kind, id) {  // click-through from a chart or heatmap (only for dimensions this module has)
    if (!id || !dims().some((d) => d.key === kind)) return;
    const list = (state.filters[kind] = state.filters[kind] || []); if (!list.includes(id)) list.push(id);
    loadReport();
  }
  function branchKeyByLabel(label) {
    const d = dims().find((x) => x.key === "branches"); if (!d) return null;
    const m = d.items.filter((b) => b.label === label);
    return m.length === 1 ? m[0].id : null;
  }

  // ------------------------------------------------------------------ tables
  function tableBlock(t) {
    const wrap = el("div", { class: "tblwrap" });
    const search = el("input", { type: "search", placeholder: T().search });
    wrap.append(el("h3", {}, t.title, el("span", { class: "hint" }, `${t.rows.length} ${T().rows}`), t.rows.length > 8 ? search : null));
    const scroll = el("div", { class: "scroll" }); wrap.append(scroll);
    let sortKey = null, sortDir = 1, limit = 60, q = "";
    const draw = () => {
      let rows = t.rows.filter((r) => !q || t.columns.some((c) => String(r[c.key] ?? "").toLowerCase().includes(q)));
      if (sortKey) rows = rows.slice().sort((a, b) => { const x = a[sortKey], y = b[sortKey]; return (typeof x === "number" && typeof y === "number" ? x - y : String(x ?? "").localeCompare(String(y ?? ""))) * sortDir; });
      const shown = rows.slice(0, limit);
      const table = el("table");
      table.append(el("thead", {}, el("tr", {}, t.columns.map((c) => el("th", { onclick: () => { sortDir = sortKey === c.key ? -sortDir : 1; sortKey = c.key; draw(); } }, c.label, sortKey === c.key ? (sortDir > 0 ? " ▲" : " ▼") : "")))));
      table.append(el("tbody", {}, shown.map((r) => el("tr", {}, t.columns.map((c) => {
        const v = r[c.key]; const numeric = c.fmt !== "text";
        const cls = (numeric ? "n " : "") + ((c.fmt === "smoney" || c.fmt === "spct") && Number(v) ? (Number(v) > 0 ? "pos" : "neg") : "");
        const td = el("td", { class: cls.trim() }, fmt(v, c.fmt));
        if (!numeric && /^(ok|matches|مطابق)$/i.test(String(v))) td.innerHTML = `<span class="tag ok">${esc(v)}</span>`;
        else if (!numeric && /^(differs|فرق|no total in file|لا يوجد إجمالي في الملف)$/i.test(String(v))) td.innerHTML = `<span class="tag bad">${esc(v)}</span>`;
        return td;
      })))));
      scroll.innerHTML = ""; scroll.append(table);
      wrap.querySelector(".more")?.remove();
      if (rows.length > limit) wrap.append(el("button", { class: "btn more", onclick: () => { limit = 1e9; draw(); } }, `${T().showAll} (${rows.length})`));
    };
    search.addEventListener("input", () => { q = search.value.toLowerCase(); draw(); });
    draw();
    return wrap;
  }

  // ------------------------------------------------------------------ charts
  function cssv(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function baseOpts(extra) {
    const ink2 = cssv("--ink2"), grid = cssv("--grid");
    return Object.assign({ responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
      plugins: { legend: { display: false, labels: { color: ink2, boxWidth: 12 } }, tooltip: { callbacks: {} } },
      scales: { x: { ticks: { color: ink2, maxRotation: 50 }, grid: { display: false }, border: { color: cssv("--axis") } },
                y: { ticks: { color: ink2, callback: (v) => compact(v) }, grid: { color: grid }, border: { display: false } } } }, extra || {});
  }
  function chartCard(spec) {
    const tall = spec.type === "heatmap" || (spec.horizontal && spec.x.length > 8);
    const card = el("div", { class: "chart" + (spec.type === "heatmap" ? " wide" : "") }, el("h3", {}, spec.title));
    if (spec.type === "heatmap") { card.append(heatmap(spec)); return card; }
    const cv = el("canvas"); card.append(el("div", { class: "cv" + (tall ? " tall" : "") }, cv));
    queueMicrotask(() => state.charts.push(makeChart(cv, spec)));
    return card;
  }
  function makeChart(cv, spec) {
    const ctx = cv.getContext("2d");
    if (spec.type === "bar") {
      const horizontal = !!spec.horizontal;
      const o = baseOpts({ indexAxis: horizontal ? "y" : "x" });
      if (horizontal) { o.scales.x = { ticks: { color: cssv("--ink2"), callback: (v) => compact(v) }, grid: { color: cssv("--grid") }, border: { display: false } };
                        o.scales.y = { ticks: { color: cssv("--ink2") }, grid: { display: false }, border: { color: cssv("--axis") } }; }
      if (spec.stacked) { o.scales.x.stacked = true; o.scales.y.stacked = true; }
      if (spec.series.length > 1) o.plugins.legend.display = true;
      o.plugins.tooltip.callbacks.label = (c) => `${c.dataset.label}: ${fmt(c.parsed[horizontal ? "x" : "y"], "money")}`;
      if (spec.drill === "branch") o.onClick = (e, els, ch) => { if (els.length) drill("branches", branchKeyByLabel(ch.data.labels[els[0].index])); };
      return new Chart(ctx, { type: "bar", data: { labels: spec.x, datasets: spec.series.map((s, i) => ({ label: s.name, data: s.values, backgroundColor: SERIES[i], borderRadius: 4, maxBarThickness: 46, borderSkipped: false })) }, options: o });
    }
    if (spec.type === "pareto") {
      const o = baseOpts();
      o.scales.y1 = { position: "right", min: 0, max: 100, ticks: { color: cssv("--ink2"), callback: (v) => v + "%" }, grid: { display: false }, border: { display: false } };
      o.plugins.tooltip.callbacks.label = (c) => c.dataset.type === "line" ? `${fmt(c.parsed.y, "pct")}` : fmt(c.parsed.y, "money");
      o.onClick = (e, els, ch) => { if (els.length) drill("categories", ch.data.labels[els[0].index]); };
      return new Chart(ctx, { data: { labels: spec.x, datasets: [
        { type: "bar", data: spec.values, backgroundColor: SERIES[0], borderRadius: 4, maxBarThickness: 40, yAxisID: "y" },
        { type: "line", data: spec.cum, borderColor: cssv("--ink2"), pointRadius: 3, borderWidth: 2, yAxisID: "y1" }] }, options: o });
    }
    if (spec.type === "waterfall") {
      const labels = [spec.start[0], ...spec.x, spec.other_label || "…", spec.end[0]];
      const base = [0], up = [null], down = [null], tot = [spec.start[1]]; let level = spec.start[1];
      [...spec.values, spec.other].forEach((d) => { base.push(Math.min(level, level + d)); up.push(d > 0 ? d : null); down.push(d < 0 ? -d : null); tot.push(null); level += d; });
      base.push(0); up.push(null); down.push(null); tot.push(spec.end[1]);
      const o = baseOpts(); o.scales.x.stacked = o.scales.y.stacked = true;
      o.plugins.tooltip.filter = (c) => c.datasetIndex !== 0;
      o.plugins.tooltip.callbacks.label = (c) => `${c.dataset.label}: ${fmt(c.dataset.sign * c.parsed.y, "smoney")}`.replace("+", c.dataset.sign > 0 ? "+" : "");
      return new Chart(ctx, { type: "bar", data: { labels, datasets: [
        { label: "", data: base, backgroundColor: "transparent", sign: 1 }, { label: "↑", data: up, backgroundColor: UP, sign: 1, borderRadius: 3 },
        { label: "↓", data: down, backgroundColor: DOWN, sign: -1, borderRadius: 3 }, { label: "Σ", data: tot, backgroundColor: SERIES[0], sign: 1, borderRadius: 3 }] }, options: o });
    }
    return new Chart(ctx, { type: "line", data: { labels: spec.x, datasets: spec.series.map((s, i) => ({ label: s.name, data: s.values, borderColor: SERIES[i], tension: .2 })) }, options: baseOpts() });
  }

  function heatmap(spec) {
    const vals = spec.values.flat().filter((v) => v !== null && v !== undefined);
    const max = Math.max(1, ...vals.map(Math.abs)), min = Math.min(0, ...vals);
    const wrap = el("div", { class: "heat", style: `grid-template-columns:minmax(130px,1.3fr) repeat(${spec.cols.length},minmax(54px,1fr))` });
    wrap.append(el("div", {}));
    spec.cols.forEach((c) => { const h = el("div", { class: "ch", title: c }, c); if (spec.drill_cols) { h.style.cursor = "pointer"; h.onclick = () => drill("categories", c); } wrap.append(h); });
    spec.rows.forEach((r, i) => {
      const rh = el("div", { class: "rh", title: r }, r);
      if (spec.drill_rows) { rh.style.cursor = "pointer"; rh.onclick = () => drill(spec.drill_rows === "branch" ? "branches" : "categories", spec.drill_rows === "branch" ? branchKeyByLabel(r) : r); }
      wrap.append(rh);
      spec.values[i].forEach((v, j) => {
        if (v === null || v === undefined) { wrap.append(el("div", {})); return; }
        const t = Math.max(0, Math.min(1, (v - min) / (max - min || 1)));
        const idx = Math.min(SEQ.length - 1, Math.floor(t * (SEQ.length - 1) + 0.5));
        const cell = el("div", { title: `${r} · ${spec.cols[j]}: ${fmt(v, "money")}`, style: `background:${SEQ[idx]};color:${idx >= 3 ? "#fff" : "#0b0b0b"}` }, compact(v));
        wrap.append(cell);
      });
    });
    return wrap;
  }

  // ------------------------------------------------------------------ wiring
  function boot() {
    applyLang();
    $("#langBtn").onclick = () => { state.lang = state.lang === "ar" ? "en" : "ar"; store.set("lang", state.lang); applyLang(); loadDatasets().then(loadReport); };
    $("#tokenBtn").onclick = () => { $("#tokenInput").value = state.token; $("#tokenDlg").showModal(); };
    $("#tokenDlg").addEventListener("close", async () => { if ($("#tokenDlg").returnValue === "ok") { state.token = $("#tokenInput").value.trim(); store.set("token", state.token); await init(); } });
    $("#uploadBtn").onclick = () => $("#fileInput").click();
    $("#fileInput").onchange = (e) => upload(e.target.files);
    const dz = $("#dropzone");
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
    dz.addEventListener("drop", (e) => upload(e.dataTransfer.files));
    $("#datasetSelect").onchange = (e) => { state.dsId = e.target.value || null; store.set("ds", state.dsId || ""); resetFilters(); state.tab = "summary"; loadReport(); };
    $("#applyBtn").onclick = applyFilters;
    $("#clearBtn").onclick = () => { resetFilters(); loadReport(); };
    $("#pdfBtn").onclick = () => download("pdf"); $("#xlsxBtn").onclick = () => download("xlsx");
    init();
  }
  async function init() {
    try {
      if (!state.modules.length) { state.modules = await api("/api/analysis"); if (!state.modules.find((m) => m.key === state.module)) state.module = state.modules[0].key; applyLang(); }
      await loadDatasets(); await loadReport();
    } catch (e) { notice(`${T().failed}: ${e.message}`, "err"); }
  }
  boot();
})();
