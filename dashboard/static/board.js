/**
 * Mag modular board — Data Studio lite.
 * Residual/registry → post-it cards on a kanban; PDF is export only.
 */
(function (global) {
  "use strict";

  const COLUMNS = [
    { id: "now", title: "Now", hint: "Latest / pinned focus" },
    { id: "open", title: "Open", hint: "Missing residual or leaf" },
    { id: "filed", title: "Filed", hint: "Lean DNA complete" },
    { id: "stickers", title: "Export ready", hint: "Residual yes · PDF optional" },
  ];

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function columnFor(s, latestId) {
    const filed = !!(s.has_residual || s.has_dossier) && !!(s.has_leaf || s.verkle_filename);
    const open = !filed;
    if (s.session_id === latestId) return "now";
    if (open) return "open";
    if (filed && !s.has_pdf) return "stickers";
    return "filed";
  }

  function postItHtml(s) {
    const tens =
      s.tension_index != null ? `T=${Number(s.tension_index).toFixed(2)}` : "";
    const theme = s.dominant_theme
      ? `<span class="theme-chip">${esc(s.dominant_theme)}</span>`
      : "";
    const pills = [
      s.has_residual || s.has_dossier ? `<span class="pill on">RES</span>` : "",
      s.has_leaf || s.verkle_filename ? `<span class="pill on">LEAF</span>` : "",
      s.has_pdf ? `<span class="pill">PDF</span>` : "",
    ]
      .filter(Boolean)
      .join("");
    const bullets = (s.bullets || []).slice(0, 3);
    const bl = bullets.length
      ? `<ul class="postit-bullets">${bullets.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>`
      : "";
    return `<button type="button" class="postit" data-sid="${esc(s.session_id)}" title="${esc(
      s.session_id || ""
    )}">
      <div class="postit-top">
        <strong>${esc(s.title || s.session_id?.slice(0, 12) || "Session")}</strong>
        ${theme}
      </div>
      <p class="postit-blurb">${esc(s.blurb || s.one_liner || "No card yet")}</p>
      ${bl}
      <div class="postit-foot">
        <span class="muted small">${esc(tens)}</span>
        <span>${pills}</span>
      </div>
    </button>`;
  }

  function renderKanban(host, sessions, latestId) {
    if (!host) return;
    const buckets = { now: [], open: [], filed: [], stickers: [] };
    const list = sessions.slice().sort((a, b) => {
      const ta = a.end_minute || a.start_minute || "";
      const tb = b.end_minute || b.start_minute || "";
      return tb.localeCompare(ta);
    });

    // Ensure latest appears in Now even if also filed
    let latest = null;
    if (latestId) {
      latest = list.find((s) => s.session_id === latestId) || null;
    }
    if (!latest && list.length) latest = list[0];

    for (const s of list) {
      if (latest && s.session_id === latest.session_id) continue;
      const col = columnFor(s, null);
      buckets[col].push(s);
    }
    if (latest) buckets.now.unshift(latest);

    host.innerHTML = COLUMNS.map((col) => {
      const cards = buckets[col.id] || [];
      const body =
        cards.length > 0
          ? cards
              .slice(0, col.id === "filed" ? 24 : 12)
              .map(postItHtml)
              .join("")
          : `<p class="muted small postit-empty">Empty</p>`;
      return `<div class="kanban-col" data-col="${col.id}">
        <header class="kanban-col-head">
          <h3>${esc(col.title)} <span class="count">${cards.length}</span></h3>
          <p class="muted small">${esc(col.hint)}</p>
        </header>
        <div class="kanban-col-body">${body}</div>
      </div>`;
    }).join("");
  }

  function renderStats(host, board, overview) {
    if (!host) return;
    const rt = (board && board.runtime) || {};
    const rk = (board && board.records_kpi) || {};
    const tip = (overview && overview.verkle_tip) || {};
    const alive = rt.alive ? "UP" : "DOWN";
    host.innerHTML = `
      <div class="stat"><b style="color:${rt.alive ? "var(--good)" : "var(--warn)"}">${alive}</b><span>integral</span></div>
      <div class="stat"><b>${rk.n_leaves ?? tip.n_leaves ?? "—"}</b><span>leaves</span></div>
      <div class="stat"><b>${rk.complete_pct != null ? rk.complete_pct + "%" : "—"}</b><span>filed</span></div>
      <div class="stat"><b>${board?.grok_budget_remaining ?? "—"}</b><span>L2 left</span></div>
      <div class="stat"><b>${board?.grok_escalations_today ?? 0}</b><span>L2 used</span></div>
      <div class="stat"><b class="mono">${String(tip.root || "").slice(0, 10) || "—"}</b><span>tip</span></div>
    `;
  }

  function fillTextPanels(board) {
    const b = board || {};
    const set = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text || "—";
    };
    set("briefOut", b.latest_brief || "(no brief yet)");
    set("liveOut", b.live_from_grok || "(empty)");
    set("attOut", b.attention || "(empty)");
    set("todoOut", b.todo || "(empty)");
    set(
      "statusOut",
      ((b.mag_status || "") + "\n\n--- CURRENT ---\n" + (b.current || "")).trim() || "—"
    );
  }

  async function openDrawer(sid, api) {
    const drawer = document.getElementById("boardDrawer");
    if (!drawer || !api) return;
    drawer.classList.remove("hidden");
    const data = await api.getJSON(`/api/session/${encodeURIComponent(sid)}`);
    const d = data.dossier || {};
    const card = data.session_card || d.session_card || {};
    const stats = data.stats || {};
    const sk = d.scalar_knot || {};
    const time = d.time || {};

    const title = document.getElementById("bdTitle");
    const idEl = document.getElementById("bdId");
    const blurb = document.getElementById("bdBlurb");
    const bullets = document.getElementById("bdBullets");
    const st = document.getElementById("bdStats");
    const actions = document.getElementById("bdActions");
    const note = document.getElementById("bdExportNote");

    if (title) title.textContent = card.title || time.title || sid.slice(0, 16);
    if (idEl) idEl.textContent = sid;
    if (blurb) blurb.textContent = card.blurb || d.tldr || "—";
    if (bullets) {
      bullets.innerHTML = (card.bullets || [])
        .slice(0, 7)
        .map((b) => `<li>${esc(b)}</li>`)
        .join("");
    }
    const T = stats.tension_index ?? sk.tension_index;
    const Q = stats.Q_proxy ?? sk.Q_proxy;
    const msgs = stats.num_chat_messages ?? time.num_chat_messages;
    if (st) {
      st.innerHTML = `
        <div class="stat"><b>${T != null ? Number(T).toFixed(2) : "—"}</b><span>tension</span></div>
        <div class="stat"><b>${Q != null ? esc(Q) : "—"}</b><span>Q</span></div>
        <div class="stat"><b>${msgs != null ? esc(msgs) : "—"}</b><span>msgs</span></div>
        <div class="stat"><b>${esc(stats.dominant_theme || (sk.theme_vector || {}).dominant || "—")}</b><span>theme</span></div>
        <div class="stat"><b>${data.has_residual ? "yes" : "no"}</b><span>residual</span></div>
        <div class="stat"><b>${data.has_pdf ? "yes" : "—"}</b><span>PDF</span></div>
      `;
    }
    if (actions) {
      const pdfBtn = data.has_pdf
        ? `<a class="btn ghost" href="${esc((data.links || {}).pdf)}" target="_blank">Open PDF</a>`
        : `<button type="button" class="btn ghost" id="bdExportPdf">Export PDF</button>`;
      actions.innerHTML = `
        <button type="button" class="btn" id="bdFullDetail">Full detail</button>
        ${pdfBtn}
        <button type="button" class="btn ghost" id="bdExportVis">${
          data.has_visual ? "Open visual" : "Export visual"
        }</button>
        <a class="btn ghost" href="${esc(
          (data.links || {}).residual || (data.links || {}).dossier_json || "#"
        )}" target="_blank">Residual</a>
      `;
      document.getElementById("bdFullDetail")?.addEventListener("click", () => {
        if (typeof api.openSession === "function") api.openSession(sid);
      });
      document.getElementById("bdExportPdf")?.addEventListener("click", async () => {
        if (note) note.textContent = "Rendering PDF…";
        try {
          const r = await api.postJSON("/api/export", {
            session_id: sid,
            pdf: true,
            visual: false,
          });
          if (r.ok && r.pdf?.url) {
            if (note) note.textContent = "PDF ready";
            window.open(r.pdf.url, "_blank");
            openDrawer(sid, api);
          } else if (note) note.textContent = r.pdf?.error || r.error || "failed";
        } catch (e) {
          if (note) note.textContent = String(e.message || e);
        }
      });
      document.getElementById("bdExportVis")?.addEventListener("click", async () => {
        if (data.has_visual && typeof api.openSessionVisual === "function") {
          api.openSessionVisual(sid);
          return;
        }
        if (note) note.textContent = "Building visual…";
        try {
          const r = await api.postJSON("/api/export", {
            session_id: sid,
            pdf: false,
            visual: true,
          });
          if ((r.ok || r.visual?.ok) && typeof api.openSessionVisual === "function") {
            if (note) note.textContent = "Visual ready";
            api.openSessionVisual(sid);
          } else if (note) note.textContent = r.visual?.error || r.error || "failed";
        } catch (e) {
          if (note) note.textContent = String(e.message || e);
        }
      });
    }
    if (note) note.textContent = "";
  }

  function closeDrawer() {
    document.getElementById("boardDrawer")?.classList.add("hidden");
  }

  /**
   * @param {object} api { getJSON, postJSON, openSession, openSessionVisual }
   */
  async function load(api) {
    const [board, overview] = await Promise.all([
      api.getJSON("/api/board"),
      api.getJSON("/api/overview").catch(() => ({ sessions: [] })),
    ]);

    const sessions = overview.sessions || [];
    const latestId =
      (overview.latest && overview.latest.session_id) ||
      (sessions[0] && sessions[0].session_id) ||
      null;

    // Prefer first session by mtime if overview doesn't mark latest
    let lid = latestId;
    if (!lid && sessions.length) {
      lid = sessions[0].session_id;
    }

    renderStats(document.getElementById("boardStats"), board, overview);
    renderKanban(document.getElementById("boardKanban"), sessions, lid);
    fillTextPanels(board);

    const note = document.getElementById("boardNote");
    if (note && board) {
      const n = sessions.length;
      note.textContent = board.instrument_note
        ? String(board.instrument_note).slice(0, 160)
        : `${n} day cards from residual · click post-it for live stats · export stickers only when needed`;
      if (!board.runtime?.alive) {
        note.textContent +=
          " · Mag integral down — start: python main.py lab";
      }
    }

    const kanban = document.getElementById("boardKanban");
    kanban?.querySelectorAll(".postit").forEach((btn) => {
      btn.addEventListener("click", () => openDrawer(btn.dataset.sid, api));
    });

    return { board, overview, sessions };
  }

  function wireOnce(api) {
    if (global.__magBoardWired) return;
    global.__magBoardWired = true;
    document.getElementById("btnDrawerClose")?.addEventListener("click", closeDrawer);
    document.getElementById("btnBoardRefresh")?.addEventListener("click", () => load(api));
    document.getElementById("btnCatchUpBoard")?.addEventListener("click", async () => {
      try {
        await api.postJSON("/api/catch-up", {});
      } catch (_) {}
      await load(api);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeDrawer();
    });
  }

  global.MagBoard = { load, wireOnce, openDrawer, closeDrawer, COLUMNS };
})(typeof window !== "undefined" ? window : globalThis);
