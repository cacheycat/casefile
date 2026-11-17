import { h, api, follow, fmt, flowStrip, traceList, flowStatus } from "/kit/kit.js";

const $ = (id) => document.getElementById(id);
const S = { meta: null, runs: [], runId: null, run: null, events: [], graph: null, report: null,
            anns: {}, live: false, stop: null, pinned: null };

function latest() {
  // graph/report/annotations come from output when done, else from the event stream
  const out = S.run?.output;
  S.graph = out?.graph_json || [...S.events].reverse().find((e) => e.type === "graph_state")?.payload || null;
  S.report = out?.report || S.events.find((e) => e.type === "report")?.payload || null;
  S.anns = out?.annotations || Object.fromEntries(S.events.filter((e) => e.type === "annotation").map((e) => [e.payload.address, e.payload]));
}

function renderStats() {
  const out = S.run?.output, g = S.graph;
  const spent = out?.spent ?? S.events.filter((e) => e.type === "expanded").length;
  const budget = S.run?.input?.budget ?? "–";
  const totalUsd = g ? g.edges.reduce((s, e) => s + e.usd, 0) : 0;
  const stat = (label, value, note, cls = "") => h("dl", { class: "stat" }, h("dt", {}, label), h("dd", { class: cls }, value), h("small", {}, note));
  $("stats").replaceChildren(
    stat("Expansions", [`${spent}/${budget}`, h("span", { class: "pips" }, Array.from({ length: +budget || 0 }, (_, i) => h("i", { class: i < spent ? "used" : "" })))], "each spends one fetch of an address's history"),
    stat("Addresses mapped", g ? g.nodes.length : 0, g ? `${g.nodes.filter((n) => n.expanded).length} expanded, rest frontier` : "–"),
    stat("Flow aggregated", fmt.usd(totalUsd), g ? `${g.edges.length} edges · ETH + ERC-20` : "–"),
    stat("Roles annotated", Object.keys(S.anns).length, "agent's calls, each tied to an address"),
    stat("Risk", S.report?.risk ?? "–", S.report ? `${S.report.confidence} confidence` : "report pending", S.report ? `risk-${S.report.risk}` : ""));
}

const short = (a) => a ? a.slice(0, 6) + "…" + a.slice(-4) : "–";

function renderGraph() {
  const el = $("graph"), g = S.graph;
  if (!g || !g.nodes.length) { el.replaceChildren(h("div", { class: "empty" }, "The graph appears as the agent expands addresses.")); return; }
  const flow = (n) => n.in_usd + n.out_usd;
  const keep = new Set(g.nodes.filter((n) => n.expanded || n.depth === 0).map((n) => n.hash));
  const annotated = new Set(Object.keys(S.anns));
  [...g.nodes].filter((n) => !keep.has(n.hash))
    .sort((a, b) => (annotated.has(b.hash) - annotated.has(a.hash)) || flow(b) - flow(a))
    .slice(0, 16).forEach((n) => keep.add(n.hash));
  const nodes = g.nodes.filter((n) => keep.has(n.hash));
  const hidden = g.nodes.length - nodes.length;
  const depths = [...new Set(nodes.map((n) => Math.min(n.depth ?? 3, 3)))].sort((a, b) => a - b);
  const colW = 240, rowH = 46, pad = 24;
  const byDepth = new Map(depths.map((d) => [d, []]));
  nodes.sort((a, b) => flow(b) - flow(a)).forEach((n) => byDepth.get(Math.min(n.depth ?? 3, 3)).push(n));
  const rows = Math.max(...[...byDepth.values()].map((c) => c.length));
  const W = depths.length * colW + pad, H = Math.max(rows * rowH + 50, 240);
  const pos = {};
  depths.forEach((d, ci) => byDepth.get(d).forEach((n, ri) => {
    const col = byDepth.get(d);
    pos[n.hash] = { x: pad + ci * colW + 60, y: 40 + ri * rowH + (rows - col.length) * rowH * 0.5 };
  }));
  const maxUsd = Math.max(...g.edges.map((e) => e.usd), 1);
  const svg = h("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` });
  depths.forEach((d, ci) => svg.append(h("text", { class: "g-depth", x: pad + ci * colW + 60, y: 16, "text-anchor": "middle" },
    d === 0 ? "SEED" : `DEPTH ${d}${d === 3 ? "+" : ""}`)));
  const hotEdges = new Set((S.report?.findings || []).flatMap((f) => f.addresses));
  for (const e of g.edges) {
    const a = pos[e.from], b = pos[e.to];
    if (!a || !b) continue;
    const w = 0.6 + 3.4 * Math.sqrt(e.usd / maxUsd);
    const mx = (a.x + b.x) / 2;
    svg.append(h("path", { class: "g-edge" + (hotEdges.has(e.from) && hotEdges.has(e.to) ? " hot" : ""),
      d: `M${a.x},${a.y} C${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`, "stroke-width": w.toFixed(1) }));
  }
  const tip = h("div", { class: "g-tip", hidden: true });
  for (const n of nodes) {
    const p = pos[n.hash], r = 5 + 9 * Math.sqrt(flow(n) / Math.max(...nodes.map(flow), 1));
    const ann = S.anns[n.hash];
    const cls = ["g-node", n.depth === 0 ? "seed" : "", n.expanded ? "expanded" : "", n.scam_flag ? "flagged" : "",
      S.pinned && S.pinned !== n.hash ? "dim" : ""].join(" ");
    const shape = n.contract
      ? h("rect", { class: "shape", x: p.x - r, y: p.y - r, width: 2 * r, height: 2 * r, transform: `rotate(45 ${p.x} ${p.y})` })
      : h("circle", { class: "shape", cx: p.x, cy: p.y, r });
    const gEl = h("g", { class: cls,
      onclick: () => { S.pinned = S.pinned === n.hash ? null : n.hash; renderGraph(); },
      onmouseenter: (ev) => {
        tip.hidden = false;
        tip.replaceChildren(
          h("div", {}, h("b", {}, short(n.hash)), n.contract ? " · contract" : " · wallet", n.expanded ? " · expanded" : ""),
          n.name ? h("div", {}, `label: “${n.name}” (unverified)`) : null,
          n.scam_flag ? h("div", { class: "warn" }, "explorer scam flag") : null,
          h("div", {}, `in ${fmt.usd(n.in_usd)} · out ${fmt.usd(n.out_usd)}`),
          ann ? h("div", {}, `role: ${ann.role} — ${ann.note}`) : null);
        const r2 = el.getBoundingClientRect();
        tip.style.left = Math.min(ev.clientX - r2.left + 14, el.clientWidth - 280) + "px";
        tip.style.top = (ev.clientY - r2.top + 10) + "px";
      }, onmouseleave: () => { tip.hidden = true; } },
      shape,
      h("text", { x: p.x + r + 5, y: p.y - 1 }, n.name ? n.name.slice(0, 16) : short(n.hash)),
      ann ? h("text", { class: "role", x: p.x + r + 5, y: p.y + 10 }, ann.role) : null);
    svg.append(gEl);
  }
  el.replaceChildren(svg, tip);
  $("graph-legend").replaceChildren(...[
    h("span", {}, `${g.nodes.length} addresses (${nodes.length} drawn${hidden > 0 ? `, ${hidden} smaller counterparties hidden` : ""})`),
    h("span", {}, `ETH at ${fmt.usd(g.eth_usd)}`),
    S.pinned ? h("span", {}, `pinned ${short(S.pinned)} — click it again to clear`) : null].filter(Boolean));
}

function renderReport() {
  const el = $("report"), r = S.report;
  $("report-hint").textContent = S.run?.output?.done_reason || "";
  if (!r) { el.replaceChildren(h("div", { class: "empty" }, S.live ? "The report is written when the loop concludes…" : "Open a case to generate a report.")); return; }
  el.replaceChildren(
    h("div", { class: "report-head" }, h("span", { class: `badge ${r.risk}` }, `${r.risk} risk`),
      h("span", { class: "badge low", style: { color: "var(--muted)" } }, `${r.confidence} confidence`)),
    h("h3", {}, r.headline),
    h("p", { class: "narrative" }, r.narrative),
    ...r.findings.map((f) => h("div", { class: `finding ${f.severity}` },
      h("h4", {}, f.title, h("span", { class: "sev" }, f.severity)),
      h("p", {}, f.detail),
      h("div", { class: "addrs" }, f.addresses.map((a) => h("span", { class: "addr-chip", onclick: () => { S.pinned = a; renderGraph(); } }, short(a)))))),
    r.next_steps?.length ? h("ol", { class: "next-steps" }, r.next_steps.map((s) => h("li", {}, s))) : null);
}

function renderAnns() {
  const entries = Object.entries(S.anns);
  $("annotations").replaceChildren(...(entries.length ? entries.map(([a, v]) => h("div", { class: "ann" },
    h("div", {}, h("div", { class: "role-tag" }, v.role), h("div", { class: "who" }, short(a))),
    h("div", {}, v.note))) : [h("div", { class: "empty" }, "No roles annotated yet.")]));
}

async function renderHeuristics() {
  const rows = await api("/api/memory");
  $("heuristics").replaceChildren(...(rows.length ? rows.sort((a, b) => b.utility - a.utility).map((m) =>
    h("div", { class: "lesson" },
      h("div", { class: "u" }, fmt.num(m.utility, 2), h("small", {}, `${m.uses} recalls`)),
      h("p", {}, m.text))) : [h("div", { class: "empty" }, "No heuristics yet — the agent writes one per concluded case.")]));
}

function renderTrace() {
  traceList($("trace"), S.events, (ev) => {
    const p = ev.payload, row = (label, note, cls = "sub") => h("div", { class: `kit-trace-row ${cls}` },
      h("span", { class: "kit-trace-time" }, ""), h("span", { class: "kit-trace-node" }, label), h("span", { class: "kit-trace-note" }, note), h("span", {}));
    if (ev.type === "expanded") return row("expanded", `${short(p.address)} · ${p.transfers} transfers · ${p.spent}/${p.budget} spent`);
    if (ev.type === "annotation") return row("annotated", `${short(p.address)} as ${p.role}`);
    if (ev.type === "rejected") return row("rejected", `${p.address}: ${p.reason}`, "sub warn");
    if (ev.type === "lesson") return row("heuristic", p.text);
    return null;
  });
  const calls = S.events.filter((e) => e.type === "llm" && e.payload.source !== "baseline");
  $("trace-hint").textContent = calls.length ? `${calls.length} model calls · ${fmt.ms(calls.reduce((s, e) => s + e.payload.ms, 0))}` : "";
}

function render() {
  latest();
  renderStats(); renderGraph(); renderReport(); renderAnns(); renderTrace();
  flowStrip($("flow"), S.meta.graph, flowStatus(S.events));
  $("start").disabled = S.live; $("start").textContent = S.live ? "Investigating…" : "Open case";
}

async function loadRuns() {
  S.runs = await api("/api/runs?kind=case");
  $("run-select").replaceChildren(...(S.runs.length ? S.runs.map((r) =>
    h("option", { value: r.id, selected: r.id === S.runId }, `#${r.id} · ${r.title}${r.status === "running" ? " · live" : ""}`)) : [h("option", { value: "" }, "no cases yet")]));
}

async function openRun(id) {
  S.stop && S.stop(); S.pinned = null;
  S.runId = id; S.run = await api(`/api/runs/${id}`); S.events = S.run.events; S.live = S.run.status === "running";
  render(); renderHeuristics();
  if (S.live) {
    S.events = [];
    let timer = null;
    S.stop = follow(id, (ev) => { S.events.push(ev); if (!timer) timer = setTimeout(() => { timer = null; render(); }, 150); },
      async () => { S.live = false; await loadRuns(); await openRun(id); renderHeuristics(); });
  }
}

async function main() {
  S.meta = await api("/api/meta");
  $("mode").textContent = S.meta.mode === "baseline" ? "no model configured: heuristic triage only" : `${S.meta.model} via ${S.meta.mode}`;
  $("seed").value = S.meta.demo_seed;
  await loadRuns();
  if (S.runs.length) await openRun(S.runs[0].id); else { render(); renderHeuristics(); }
  $("run-select").addEventListener("change", (e) => e.target.value && openRun(+e.target.value));
  $("controls").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const { run_id } = await api("/api/case", { seed: $("seed").value.trim(), budget: +$("budget").value, per_round: 2, note: "" });
      await loadRuns(); await openRun(run_id); await loadRuns();
    } catch (err) { alert(err.message); }
  });
}
main();
