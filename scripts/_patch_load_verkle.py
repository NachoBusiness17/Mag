from pathlib import Path

p = Path("dashboard/static/app.js")
text = p.read_text(encoding="utf-8")
start = text.find("async function loadVerkle()")
end = text.find("async function loadIngest()")
if start < 0 or end < 0:
    raise SystemExit(f"markers not found start={start} end={end}")

new_fn = r'''async function loadVerkle() {
  try {
    let L;
    try {
      L = await getJSON("/api/v1/lattice-history");
    } catch {
      let v;
      try {
        v = await getJSON("/api/v1/chain");
      } catch {
        v = await getJSON("/api/verkle");
      }
      L = {
        tip: v.tip || {},
        history: [],
        theme_histogram: {},
        plan: { working_open: [], agent_next: [], suggested_focus: null },
        chain_tail: (v.chain || []).slice(-12).map((r) => ({
          filename: r.filename || r.leaf,
          session_id: r.session_id,
        })),
        plain: { one_line: "lattice-history API unavailable — tip/chain only" },
        theme_basis: (v.evolution || {}).theme_basis || [],
        history_n: (v.tip || {}).n_leaves,
        tensions: [],
        chain_n: (v.chain || []).length,
      };
    }
    const tip = L.tip || {};
    const plan = L.plan || {};
    const hist = L.theme_histogram || {};
    const history = L.history || [];
    const basis = L.theme_basis || Object.keys(hist);
    const maxH = Math.max(1, ...Object.values(hist).map(Number), 1);

    const statsEl = $("#latticeStats");
    if (statsEl) {
      const alive = tip.alive ? "ALIVE" : "EMPTY";
      const tAvg = L.tension_avg != null ? Number(L.tension_avg).toFixed(2) : "—";
      const tLast = L.tension_latest != null ? Number(L.tension_latest).toFixed(2) : "—";
      statsEl.innerHTML = [
        ["tip", tip.root_short ? tip.root_short + "…" : "—"],
        ["leaves", tip.n_leaves ?? L.history_n ?? "—"],
        ["chain", L.chain_n ?? "—"],
        ["alive", alive],
        ["tension last", tLast],
        ["tension avg", tAvg],
      ]
        .map(
          ([k, v]) =>
            `<div class="stat"><span class="k">${esc(k)}</span><span class="v">${esc(String(v))}</span></div>`
        )
        .join("");
    }
    if ($("#latticeOneLine")) {
      $("#latticeOneLine").textContent =
        (L.plain && L.plain.one_line) || tip.last_filename || "—";
    }
    if ($("#latticeFocus")) {
      $("#latticeFocus").textContent = "Focus: " + (plan.suggested_focus || "none extracted");
    }
    if ($("#latticePlanList")) {
      const items = plan.working_open || [];
      $("#latticePlanList").innerHTML =
        items
          .map(
            (it) =>
              `<li><span class="pill">${esc(it.status || "open")}</span> ${esc(it.text || "")}</li>`
          )
          .join("") || "<li class='muted'>No ## Open items in working.md</li>";
    }
    if ($("#latticeAgentNext")) {
      const items = plan.agent_next || [];
      $("#latticeAgentNext").innerHTML =
        items
          .map(
            (it) =>
              `<li><span class="pill">${esc(it.status || "—")}</span> <span class="mono">${esc(
                it.id || ""
              )}</span> ${esc(it.title || "")}</li>`
          )
          .join("") || "<li class='muted'>No agent_state next_moves (JSON)</li>";
    }
    if ($("#latticeThemes")) {
      const keys = basis.length ? basis : Object.keys(hist);
      $("#latticeThemes").innerHTML = keys
        .map((k) => {
          const n = Number(hist[k] || 0);
          const pct = Math.round((n / maxH) * 100);
          return `<div class="theme-row"><span class="mono">${esc(k)}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
            <span class="mono">${n}</span></div>`;
        })
        .join("");
    }
    if ($("#latticeHistory")) {
      const rows = history.slice().reverse();
      $("#latticeHistory").innerHTML =
        rows
          .map((h) => {
            const day = String(h.start_minute || "").slice(0, 10) || "—";
            const theme = h.dominant_theme || "—";
            const ten = h.tension_index != null ? Number(h.tension_index) : null;
            const w = ten != null ? Math.min(100, Math.round(ten * 100)) : 0;
            const sid = String(h.session_id || "").slice(0, 13);
            const dur =
              h.duration_minutes != null
                ? Math.round(Number(h.duration_minutes)) + "m"
                : "—";
            return `<div class="lat-row" title="${esc(h.session_id || "")}">
              <span class="t-date">${esc(day)}</span>
              <div>
                <div class="t-theme">${esc(theme)}</div>
                <div class="meta muted mono">${esc(sid)}… · ${esc(dur)}</div>
                <div class="t-bar"><i style="width:${w}%"></i></div>
              </div>
              <span class="t-ten">${ten != null ? ten.toFixed(2) : "—"}</span>
            </div>`;
          })
          .join("") || "<p class='muted'>No evolution series yet — finish SessionEnd beads.</p>";
    }

    const root = String(tip.root || "");
    const lines = [
      "=== TIP ===",
      `root: ${root ? root.slice(0, 20) + "…" : "—"}`,
      `leaves: ${tip.n_leaves ?? "—"}`,
      `last: ${tip.last_filename || "—"}`,
      `session: ${tip.last_session_id || "—"}`,
      `updated: ${tip.updated_minute || "—"}`,
      "",
      "=== CHAIN TAIL ===",
      ...((L.chain_tail || []).slice(-10).map((r, i) => `${i + 1}. ${r.filename || r.session_id || "—"}`)),
      "",
      "paths: memory/biography/verkle_tip.json · topic_evolution.json · knot_timeline.jsonl",
    ];
    if ($("#verkleOut")) $("#verkleOut").textContent = lines.join("\n");
  } catch (e) {
    if ($("#verkleOut")) $("#verkleOut").textContent = String(e.message || e);
    if ($("#latticeOneLine")) $("#latticeOneLine").textContent = String(e.message || e);
  }
}

'''

p.write_text(text[:start] + new_fn + text[end:], encoding="utf-8")
print("ok", start, end)
