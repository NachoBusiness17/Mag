/* Mag Resource Harness — companion office (Magatama lineage) */
const $ = (s) => document.querySelector(s);

let overview = null;
let selectedId = null;
let visualSessionId = "latest";

/** Top bar inspiration — people who feed this craft. Not status jargon. */
const MAG_QUOTES = [
  {
    t: "I do not pretend to understand the moral universe; the arc is a long one… from what I see I am sure it bends towards justice.",
    a: "Theodore Parker",
  },
  {
    t: "Architecture is a kind of law — it constrains and enables more reliably than sermons.",
    a: "Lawrence Lessig (spirit)",
  },
  {
    t: "We shape our tools, and thereafter our tools shape us.",
    a: "John Culkin",
  },
  {
    t: "Freedom is the freedom to say that two plus two make four. If that is granted, all else follows.",
    a: "George Orwell",
  },
  {
    t: "What I cannot create, I do not understand.",
    a: "Richard Feynman",
  },
  {
    t: "The best way to predict the future is to invent it.",
    a: "Alan Kay",
  },
  {
    t: "A mag grows with its master. Feed it well; it will stand with you.",
    a: "PSO Mag spirit",
  },
  {
    t: "Too much sanity may be madness — and maddest of all, to see life as it is and not as it should be.",
    a: "Cervantes / Man of La Mancha",
  },
  {
    t: "I have always imagined that Paradise will be a kind of library.",
    a: "Jorge Luis Borges",
  },
  {
    t: "The medium is the message.",
    a: "Marshall McLuhan",
  },
  {
    t: "Stay hungry. Stay foolish.",
    a: "Stewart Brand · Whole Earth",
  },
  {
    t: "The only way to deal with an unfree world is to become so absolutely free that your very existence is an act of rebellion.",
    a: "Albert Camus",
  },
  {
    t: "Do not go gentle into that good night.",
    a: "Dylan Thomas",
  },
  {
    t: "The map is not the territory.",
    a: "Alfred Korzybski",
  },
  {
    t: "Miles to go before I sleep.",
    a: "Robert Frost",
  },
];

let _quoteIdx = Math.floor(Math.random() * MAG_QUOTES.length);

function rotateMagQuote(advance = true) {
  const el = $("#cliQuote");
  if (!el || !MAG_QUOTES.length) return;
  if (advance) _quoteIdx = (_quoteIdx + 1) % MAG_QUOTES.length;
  const q = MAG_QUOTES[_quoteIdx % MAG_QUOTES.length];
  el.innerHTML = `<span class="q-text">“${esc(q.t)}”</span> <span class="q-attr">— ${esc(q.a)}</span>`;
  el.dataset.seeded = "1";
  el.title = "Click for another line";
}

const PIN_KEY = "mag_vis_pins_v1";
const MIRROR_INTRO_KEY = "mag_mirror_intro_v1";

const MIRROR_GUIDE_STEPS = [
  {
    title: "Hi — I'm your Mirror",
    body:
      "Mag reflects what you filed on disk — sessions, proof, steering — not a smoother invented story. I'll point at the rooms that matter.",
    tab: null,
    highlight: null,
  },
  {
    title: "Office — been → now → next",
    body:
      "Start here for posture: what you finished, what's live, and the next honest move before you dive into threads.",
    tab: "home",
    highlight: '.dock-btn[data-win="home"]',
  },
  {
    title: "Body — seats & workers",
    body:
      "Who's plugged in: Cursor, Chat, outbound seats, worker registry, governance. This is the wiring diagram — not theater.",
    tab: "status",
    highlight: '.dock-btn[data-win="status"]',
  },
  {
    title: "Days — workday beads",
    body:
      "Each day is a bead with real subsessions and runs underneath. Toggle the Verkle lattice for semi-visible structure; inspect for layman what / where / why.",
    tab: "sessions",
    highlight: '.dock-btn[data-win="sessions"]',
  },
  {
    title: "Chat — steer while it runs",
    body:
      "Talk to Mag from filed memory. Queue guidance in the dock below — it drains at checkpoints instead of fighting the agent mid-turn.",
    tab: "chat",
    highlight: "#operatorInboxDock",
  },
  {
    title: "Pulse — honest activity",
    body:
      "What actually happened: attention.md, seat feed, workers. Labels say when something is sourced vs inferred — no invented commentary.",
    tab: "chronicle",
    highlight: '.dock-btn[data-win="chronicle"]',
  },
  {
    title: "Strike desk (optional mirror)",
    body:
      "This dashboard is home (:8765). The sovereign mirror / strike desk (:8743) loads your corpus as you presented it — Shell here opens owned chrome for deep edits.",
    tab: null,
    highlight: 'a.dock-btn[href="/shell"]',
  },
  {
    title: "You're set",
    body:
      "Replay this tour anytime from the Mirror button in the header. Queue steering in Chat; Body and Pulse stay honest. Go build.",
    tab: "home",
    highlight: "#btnMirrorReplay",
  },
];

let _mirrorGuideStep = 0;

function mirrorGuideSeen() {
  try {
    return localStorage.getItem(MIRROR_INTRO_KEY) === "1";
  } catch {
    return false;
  }
}

function mirrorGuideMarkSeen() {
  try {
    localStorage.setItem(MIRROR_INTRO_KEY, "1");
  } catch {
    /* ignore */
  }
}

function mirrorGuideClearSpotlight() {
  document.querySelectorAll(".mirror-spotlight").forEach((el) => el.classList.remove("mirror-spotlight"));
}

function mirrorGuideRenderDots(step) {
  const dots = $("#mirrorGuideDots");
  if (!dots) return;
  dots.innerHTML = MIRROR_GUIDE_STEPS.map((_, i) => `<span class="${i === step ? "on" : ""}"></span>`).join("");
}

function mirrorGuideShowStep(step) {
  _mirrorGuideStep = Math.max(0, Math.min(step, MIRROR_GUIDE_STEPS.length - 1));
  const s = MIRROR_GUIDE_STEPS[_mirrorGuideStep];
  if ($("#mirrorGuideTitle")) $("#mirrorGuideTitle").textContent = s.title;
  if ($("#mirrorGuideText")) $("#mirrorGuideText").textContent = s.body;
  mirrorGuideRenderDots(_mirrorGuideStep);
  if ($("#btnMirrorBack")) $("#btnMirrorBack").disabled = _mirrorGuideStep === 0;
  if ($("#btnMirrorNext")) {
    $("#btnMirrorNext").textContent =
      _mirrorGuideStep >= MIRROR_GUIDE_STEPS.length - 1 ? "Got it" : "Next";
  }
  mirrorGuideClearSpotlight();
  if (s.tab) setTab(s.tab);
  if (s.highlight) {
    const el = document.querySelector(s.highlight);
    if (el) {
      el.classList.add("mirror-spotlight");
      el.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
    }
  }
}

function mirrorGuideOpen(force = false) {
  if (!force && mirrorGuideSeen()) return;
  if (document.body.classList.contains("agents-embed")) return;
  $("#mirrorGuideBackdrop")?.classList.remove("hidden");
  $("#mirrorGuide")?.classList.remove("hidden");
  mirrorGuideShowStep(0);
}

function mirrorGuideClose(markSeen = true) {
  if (markSeen) mirrorGuideMarkSeen();
  mirrorGuideClearSpotlight();
  $("#mirrorGuideBackdrop")?.classList.add("hidden");
  $("#mirrorGuide")?.classList.add("hidden");
}

function wireMirrorGuide() {
  $("#btnMirrorNext")?.addEventListener("click", () => {
    if (_mirrorGuideStep >= MIRROR_GUIDE_STEPS.length - 1) {
      mirrorGuideClose(true);
      toast("Mirror tour complete — replay from header anytime", 2600);
      return;
    }
    mirrorGuideShowStep(_mirrorGuideStep + 1);
  });
  $("#btnMirrorBack")?.addEventListener("click", () => {
    if (_mirrorGuideStep > 0) mirrorGuideShowStep(_mirrorGuideStep - 1);
  });
  $("#btnMirrorSkip")?.addEventListener("click", () => mirrorGuideClose(true));
  $("#btnMirrorReplay")?.addEventListener("click", () => mirrorGuideOpen(true));
}

function maybeStartMirrorGuide() {
  if (mirrorGuideSeen()) return;
  setTimeout(() => mirrorGuideOpen(false), 900);
}

function loadPins() {
  try {
    const raw = localStorage.getItem(PIN_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function savePins(pins) {
  localStorage.setItem(PIN_KEY, JSON.stringify(pins.slice(0, 12)));
}

function sessionLabel(s) {
  if (!s) return "—";
  const t = s.title || s.session_id?.slice(0, 12) || "session";
  const when = s.end_minute || s.start_minute || "";
  const day = when ? String(when).slice(0, 10) : "";
  return day ? `${day} · ${t}` : t;
}

/** Prefer /api/v1 — single REST surface. */
const API = "/api/v1";

async function parseApiResponse(r, url) {
  const text = await r.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Bad JSON from ${url} (${r.status})`);
  }
  if (!r.ok || data?.ok === false) {
    const err = data?.error || r.statusText || String(r.status);
    throw new Error(`${url}: ${err}`);
  }
  return data;
}

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  return parseApiResponse(r, url);
}

async function postJSON(url, body, opts = {}) {
  const ms = opts.timeoutMs ?? 120000;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
      signal: ctrl.signal,
    });
    return await parseApiResponse(r, url);
  } catch (e) {
    if (e?.name === "AbortError") {
      throw new Error(
        `Timeout after ${Math.round(ms / 1000)}s — ${url}. If seat is Local, is Ollama running? For remote, check .env key + Status.`
      );
    }
    throw e;
  } finally {
    clearTimeout(t);
  }
}

async function patchJSON(url, body) {
  const r = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return parseApiResponse(r, url);
}

function toast(msg, ms = 3200) {
  const el = $("#toast");
  if (!el) {
    console.info("[mag]", msg);
    return;
  }
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), ms);
}

function activePane() {
  const win = document.querySelector(".win.focused[data-win]");
  if (win?.dataset?.win) return win.dataset.win;
  const dock = document.querySelector(".dock-btn.on");
  return dock?.dataset?.win || "home";
}

function kvRows(tbody, rows) {
  if (!tbody) return;
  tbody.innerHTML = rows
    .map(
      ([k, v, cls]) =>
        `<tr class="${cls || ""}"><th scope="row">${esc(k)}</th><td>${esc(
          v == null || v === "" ? "—" : String(v)
        )}</td></tr>`
    )
    .join("");
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function shortHash(h) {
  if (!h) return "—";
  return String(h).slice(0, 10) + "…";
}

function setTab(name) {
  if (name === "osdepth") {
    const strip = $("#magOsStrip");
    if (strip) {
      strip.classList.toggle("hidden");
      if (!strip.classList.contains("hidden")) loadMagOs();
    }
    return;
  }
  if (name === "office") name = "home";
  if (name === "days" || name === "tapestry") name = "sessions";

  // Single-focus desk: dock opens one full pane
  if (window.magWin?.open) {
    window.magWin.open(name);
  }
  document.querySelectorAll(".panel").forEach((p) => {
    // Only real content panels — never treat the empty tapestry stub as active
    const on = p.id === `panel-${name}` || (name === "sessions" && p.id === "panel-sessions");
    p.classList.toggle("active", on);
  });
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".dock-btn").forEach((b) => {
    const w = b.dataset.win;
    b.classList.toggle("on", w === name || (name === "home" && w === "home"));
  });

  if (name === "home") loadHome();
  if (name === "chat") {
    renderChat();
    refreshEconomy();
    startOperatorInboxPoll();
    setTimeout(() => $("#chatInput")?.focus(), 50);
  }
  if (name === "operate") loadOperate();
  if (name === "orchestrate") loadOrchestrate();
  if (name === "blast") loadBlast();
  if (name === "flow") loadFlow();
  if (name === "verkle") loadVerkle();
  if (name === "viewports") loadViewports();
  if (name === "ingest") loadIngest();
  if (name === "board") loadBoard();
  if (name === "visual") loadVisual();
  if (name === "ideas") loadIdeas();
  if (name === "status") loadStatus();
  if (name === "chronicle") startChroniclePoll();
  if (name === "agents") {
    const fr = $("#agentsFrame");
    if (fr && !fr.dataset.loaded) {
      fr.dataset.loaded = "1";
      fr.src = "/static/agents.html?embed=1&t=" + Date.now();
    }
  }
  if (name === "diary") loadDiary();
  if (name === "story") loadStory();
  if (name === "sessions") {
    document.body.classList.add("desk-tabs", "cli");
    const win = document.getElementById("win-sessions");
    if (win) {
      win.classList.remove("minimized");
      win.classList.add("focused", "pane");
      win.setAttribute("aria-hidden", "false");
      win.style.display = "flex";
      win.style.visibility = "visible";
      win.style.opacity = "1";
    }
    // Hide empty tapestry stub if any CSS resurrects it
    const stub = document.getElementById("panel-tapestry");
    if (stub) {
      stub.hidden = true;
      stub.style.cssText = "display:none!important;height:0!important;overflow:hidden!important;pointer-events:none!important";
    }
    const ps = document.getElementById("panel-sessions");
    if (ps) {
      ps.classList.add("active");
      ps.style.cssText =
        "display:flex!important;flex-direction:column;flex:1;min-height:0;height:100%;width:100%;visibility:visible;opacity:1;overflow:hidden;position:relative;z-index:2";
    }
    const host = document.getElementById("sessionRows");
    if (host) {
      host.innerHTML = `<p class="muted" style="padding:0.75rem">Loading your workdays…</p>`;
    }
    getJSON("/api/v1/overview")
      .catch(() => getJSON("/api/overview"))
      .then((o) => {
        overview = o;
        window.__lastOverview = o;
        try {
          renderStats(o);
          renderSessions(o.sessions || []);
          fillSessionSelect(o.sessions || []);
        } catch (err) {
          console.error("renderSessions", err);
          if (host)
            host.innerHTML = `<p class="muted" style="padding:0.75rem;color:var(--warn)">List render error: ${esc(
              err.message || err
            )}</p>`;
        }
        const kick = () => {
          try {
            tapestryView?.resize?.({ forceFit: true });
          } catch (_) {
            /* ignore */
          }
        };
        requestAnimationFrame(() => {
          kick();
          setTimeout(kick, 120);
          setTimeout(kick, 400);
        });
      })
      .catch((e) => {
        const h = document.getElementById("sessionRows");
        if (h) {
          h.innerHTML = `<p class="muted" style="padding:0.75rem;color:var(--warn)">Could not load workdays: ${esc(
            e.message || e
          )}. Try Refresh. Lab must be running on :8765.</p>`;
        }
      });
    loadTapestry().catch((e) => console.warn("tapestry", e));
  }
  if (name === "detail" && selectedId) {
    if (typeof selectSession === "function") selectSession(selectedId);
  }
}
window.magOpenTab = setTab;

function renderVerkleMap(h) {
  const tip = h.tip || {};
  const bead = h.latest_bead || {};
  const ship = h.ship || {};
  const verify = h.verify || {};
  const prov = h.provenance || {};
  const phoenix = h.phoenix || {};
  const econ = h.economy_today || {};
  const compose = h.compose || {};

  const tree = $("#vmapTree");
  if (!tree) return;

  const tipHash = tip.root_short || "—";
  const sid = bead.session_id ? String(bead.session_id).slice(0, 16) + "…" : "—";

  // Plain-English chain map (design principle: jargon second)
  tree.innerHTML = `
    <div class="chain-node tip">
      <div class="chain-label">Step A · Chain tip (is memory alive?)</div>
      <div class="chain-body"><strong>${esc(tipHash)}</strong></div>
      <div class="meta muted" style="margin-top:0.25rem">Saved days in chain: ${esc(
        String(tip.n_leaves ?? "—")
      )} · dig notes filed: ${esc(String(tip.dig_edges_n ?? 0))}</div>
    </div>
    <div class="chain-join">↓ filed work hangs under the tip</div>
    <div class="chain-node bead">
      <div class="chain-label">Step B · Latest workday (bead on disk)</div>
      <div class="chain-body"><strong>${esc(bead.title || "No day filed yet")}</strong></div>
      <div class="meta muted">${esc(
        [bead.end_minute || "", bead.dominant_theme || "", sid].filter(Boolean).join(" · ")
      )}</div>
      <div class="chain-body" style="margin-top:0.35rem;opacity:0.9">${esc(
        (bead.blurb || "Finish a session so Mag can save a bead.").slice(0, 320)
      )}</div>
      <div class="meta muted" style="margin-top:0.35rem">File: <code>${esc(
        prov.residual_rel || "—"
      )}</code></div>
    </div>
    <div class="chain-join">↓ unfinished business = edges (not a new “truth engine”)</div>
    <div class="chain-node">
      <div class="chain-label">Step C · Open edges (loops · next · bonds)</div>
      <div class="chain-body">Open loops: <strong>${esc(
        String((h.open_loops || []).length)
      )}</strong> · Next items: <strong>${esc(
    String((h.next_moves || []).length + (h.working_open || []).length)
  )}</strong> · Bonds: <strong>${esc(String((h.residual_bonds || []).length))}</strong></div>
      <div class="meta muted">Details listed in cards below.</div>
    </div>
    <div class="chain-join">↓ brief the AI without pasting your whole life</div>
    <div class="chain-node load">
      <div class="chain-label">Step D · Load (pack for AI)</div>
      <div class="chain-body">Status <strong>${esc(
        ship.status || "—"
      )}</strong> · verify ${esc(String(verify.pass ?? "—"))}/${esc(
    String(verify.n ?? "—")
  )} · local smoke ${esc(h.multi_smoke_ok ? "PASS" : "needs run")}</div>
      <div class="meta muted">${
        phoenix.on
          ? "Needs fix: " + esc((phoenix.fixes || [])[0] || (phoenix.reasons || [])[0] || "")
          : "Office coherent enough to work."
      }</div>
      <div class="meta muted">CLI: mag.cmd context-pack · path ${esc(
        h.path || "FIND → FILE → LOAD"
      )}</div>
    </div>
  `;
}

async function loadHome() {
  let h = {};
  try {
    h = await getJSON("/api/v1/home");
  } catch {
    try {
      h = await getJSON("/api/home");
    } catch (e) {
      if ($("#homeBeadTitle")) {
        $("#homeBeadTitle").textContent = "Home API failed — restart dashboard?";
      }
      if ($("#homeBeadBlurb")) $("#homeBeadBlurb").textContent = String(e.message || e);
      if ($("#homeShip")) {
        $("#homeShip").textContent = "PROVISIONAL";
        $("#homeShip").className = "ship-badge ship-prov";
      }
      if ($("#homeHeadline")) {
        $("#homeHeadline").textContent = "Office API failed — restart dashboard?";
      }
      return;
    }
  }
  if (!h || h.ok === false) {
    if ($("#homeBeadBlurb")) $("#homeBeadBlurb").textContent = h?.error || "empty";
    return;
  }
  const health = h.health || {};
  const tip = h.tip || {};
  const bead = h.latest_bead || {};
  const prev = h.previous_bead || (h.trail && h.trail.previous) || {};
  const traj = h.trajectory || {};
  const now = h.now || {};
  const econ = h.economy_today || {};
  const ship = h.ship || {};
  const phoenix = h.phoenix || {};
  const verify = h.verify || {};
  const prov = h.provenance || {};

  if ($("#homeHeadline")) {
    $("#homeHeadline").textContent = h.headline || "Your last filed day";
  }

  const lp = h.launch_pad || {};
  const launchEl = $("#homeLaunchPad");
  if (launchEl) {
    if (lp.show) {
      launchEl.classList.remove("hidden");
      if ($("#homeLaunchTitle")) $("#homeLaunchTitle").textContent = lp.headline || "Launch point";
      if ($("#homeLaunchSubtitle")) $("#homeLaunchSubtitle").textContent = lp.subtitle || "";
      if ($("#homeLaunchFramework")) {
        $("#homeLaunchFramework").innerHTML = (lp.framework || [])
          .map(
            (f) =>
              `<li><strong>${esc(f.label)}</strong> · ${f.ok ? "shipped" : "missing"} · <code class="mono">${esc(f.path)}</code></li>`
          )
          .join("");
      }
      if ($("#homeLaunchOps")) {
        $("#homeLaunchOps").innerHTML = (lp.core_ops || [])
          .map((op) => {
            if (op.kind === "tab") {
              return `<li><button type="button" class="btn ghost btn-sm launch-op" data-tab="${esc(op.target)}">${esc(op.label)}</button></li>`;
            }
            const cmd = op.cmd || op.cmd_unix || "";
            return `<li><span>${esc(op.label)}</span> · <code class="mono sm">${esc(cmd)}</code></li>`;
          })
          .join("");
        launchEl.querySelectorAll(".launch-op").forEach((btn) => {
          btn.addEventListener("click", () => setTab(btn.dataset.tab));
        });
      }
      const rep = lp.republic || {};
      if ($("#homeLaunchRepublic")) {
        $("#homeLaunchRepublic").textContent = rep.detected
          ? `Mycelial Republic detected at ${rep.root}`
          : `Clone Mycelial Republic beside Mag → ${rep.root || "../mycelial-republic"}`;
      }
    } else {
      launchEl.classList.add("hidden");
    }
  }

  // Top bar quotes live in rotateMagQuote — do not paint ship/caveat into chrome

  // NOW
  if ($("#homeNowList")) {
    const rows = [
      ["Lane", now.working_lane || "—"],
      ["Open run", now.active_run || (h.compose || {}).active_run || "none"],
      ["Tip", now.tip_short || tip.root_short || "—"],
      ["Days filed", String(now.n_sessions ?? h.n_sessions ?? "—")],
      ["Ollama", health.ollama ? "ON" : "OFF"],
      ["Smoke", h.multi_smoke_ok ? "PASS" : "needs run"],
    ];
    $("#homeNowList").innerHTML = rows
      .map(([k, v]) => `<li><strong>${esc(k)}</strong> · ${esc(v)}</li>`)
      .join("");
  }

  // GOING
  if ($("#homePrimaryNext")) {
    $("#homePrimaryNext").textContent = traj.primary_next || "No next move filed";
  }
  if ($("#homeGoingList")) {
    const bits = [];
    (traj.ideas_open || (h.ideas || {}).open || []).slice(0, 5).forEach((n) => {
      bits.push(`[idea] ${n.title || n.id}`);
    });
    (traj.working_open || h.working_open || []).slice(0, 4).forEach((x) => bits.push(x));
    (traj.loops || h.open_loops || []).slice(0, 3).forEach((x) => bits.push(x));
    (traj.next_moves || h.next_moves || []).slice(0, 3).forEach((x) => bits.push(`next: ${x}`));
    $("#homeGoingList").innerHTML = bits.length
      ? bits.map((x) => `<li>${esc(String(x).replace(/^-\s*/, ""))}</li>`).join("")
      : `<li class="muted">Nothing open — seed ideas or file a day</li>`;
  }

  if ($("#homePrevLine")) {
    if (prev && prev.title) {
      $("#homePrevLine").textContent = `Earlier: ${prev.title}${
        prev.end_minute ? " · " + String(prev.end_minute).slice(0, 16) : ""
      }`;
    } else {
      $("#homePrevLine").textContent = "No earlier bead on file";
    }
  }

  if ($("#homePath")) {
    const digN = tip.dig_edges_n ?? 0;
    $("#homePath").textContent =
      digN > 0
        ? `Daily loop: find → file → load · ${digN} research note(s) linked`
        : "Daily loop: find → file → load a short pack next time";
  }

  // Zeitgeist chips
  if ($("#homeZg")) {
    const chips = h.zeitgeist || [
      "FIND → FILE → LOAD",
      "Residual = DNA",
      "Presented ≠ consensus",
      "Pack-first",
    ];
    $("#homeZg").innerHTML = chips
      .map((c) => `<span class="zg-chip">${esc(c)}</span>`)
      .join("");
  }

  // Ship badge (ARK-shaped, Mag gates)
  if ($("#homeShip")) {
    const st = ship.status || "—";
    $("#homeShip").textContent = st;
    const tone =
      st === "OK" ? "ok" : st === "CAVEATS" ? "caveat" : "prov";
    // keep ship-badge for CLI bar + ship/ship-big for clear-UI leftovers
    $("#homeShip").className = `ship-badge ship ship-big ${tone} ship-${tone} ${st}`;
    $("#homeShip").title = (ship.why || []).join(" · ") || ship.note || "";
  }

  // Phoenix banner only when not OK
  const ph = $("#homePhoenix");
  if (ph) {
    if (phoenix.on) {
      ph.classList.remove("hidden");
      const reasons = (phoenix.reasons || []).map((r) => esc(r)).join("</li><li>");
      const fixes = (phoenix.fix || []).map((f) => esc(f)).join("</li><li>");
      ph.innerHTML = `
        <h3>Needs attention (self-check)</h3>
        <ul><li>${reasons || "—"}</li></ul>
        <p class="meta muted" style="margin:0.5rem 0 0.2rem">What to try</p>
        <ul><li>${fixes || "mag.cmd doctor"}</li></ul>
      `;
    } else {
      ph.classList.add("hidden");
      ph.innerHTML = "";
    }
  }

  if ($("#homeStats")) {
    const up = health.up;
    const smoke = h.multi_smoke_ok;
    const vp = verify.pass;
    const vn = verify.n;
    $("#homeStats").innerHTML = `
      <div class="stat"><b style="color:${up ? "var(--good)" : "var(--warn)"}">${
        up ? "UP" : "DOWN"
      }</b><span>Viewport</span></div>
      <div class="stat"><b style="color:${health.ollama ? "var(--good)" : "var(--warn)"}">${
        health.ollama ? "ON" : "OFF"
      }</b><span>Ollama</span></div>
      <div class="stat"><b>${h.n_sessions ?? "—"}</b><span>days filed</span></div>
      <div class="stat"><b>${tip.n_leaves ?? "—"}</b><span>tip leaves</span></div>
      <div class="stat"><b style="color:${smoke ? "var(--good)" : "var(--warn)"}">${
        smoke ? "PASS" : "FAIL"
      }</b><span>multi-smoke</span></div>
      <div class="stat"><b>${tip.dig_edges_n ?? 0}</b><span>research notes</span></div>
      <div class="stat"><b style="color:${
        vp === vn ? "var(--good)" : "var(--warn)"
      }">${vp ?? "—"}/${vn ?? "—"}</b><span>verify</span></div>
    `;
  }

  if ($("#homeBeadTitle")) {
    $("#homeBeadTitle").textContent = bead.title || "No days filed yet";
  }
  if ($("#homeBeadMeta")) {
    const sid = bead.session_id ? String(bead.session_id).slice(0, 14) + "…" : "";
    $("#homeBeadMeta").textContent =
      [bead.end_minute || "", bead.dominant_theme || "", sid].filter(Boolean).join(" · ") ||
      "Close a session or backfill to create a bead.";
  }
  if ($("#homeBeadBlurb")) {
    $("#homeBeadBlurb").textContent = bead.blurb || bead.error || "—";
  }
  if ($("#homeBeadBullets")) {
    const bullets = bead.bullets || [];
    $("#homeBeadBullets").innerHTML = bullets.length
      ? bullets.map((b) => `<li>${esc(b)}</li>`).join("")
      : "";
  }
  window.__osLatestSid = bead.session_id || null;

  // Provenance
  if ($("#homeProvList")) {
    const rows = [
      ["session", prov.session_id || "—"],
      ["residual", prov.residual_rel || prov.residual_abs || "—"],
      ["tip", prov.tip_rel || "memory/biography/verkle_tip.json"],
      ["bonds", prov.bonds_rel || "memory/bonds_active.md"],
      ["card", prov.operator_card || "docs/ref/OPERATOR_CARD.md"],
    ];
    $("#homeProvList").innerHTML = rows
      .map(
        ([k, v]) =>
          `<li><span class="prov-k">${esc(k)}</span><code class="prov-v">${esc(v)}</code></li>`
      )
      .join("");
  }

  // Verify checklist
  if ($("#homeVerify")) {
    const items = verify.items || [];
    $("#homeVerify").innerHTML = items.length
      ? items
          .map(
            (it) =>
              `<li class="${it.ok ? "v-ok" : "v-bad"}">${it.ok ? "✓" : "✗"} ${esc(
                it.label || it.id
              )}</li>`
          )
          .join("")
      : `<li class="muted">No verify payload — restart dashboard for new API</li>`;
  }
  if ($("#homeVerifyScore")) {
    $("#homeVerifyScore").textContent =
      verify.n != null ? `(${verify.pass}/${verify.n})` : "";
  }

  if ($("#homeTip")) {
    $("#homeTip").textContent = tip.root_short || "—";
  }
  if ($("#homeTipMeta")) {
    $("#homeTipMeta").textContent =
      [
        tip.last_filename ? `last: ${tip.last_filename}` : "",
        tip.updated_minute ? `upd: ${String(tip.updated_minute).slice(0, 16)}` : "",
      ]
        .filter(Boolean)
        .join(" · ") || "No tip file";
  }

  if ($("#homeEcon")) {
    const loc = econ.local_tokens ?? 0;
    const saved = econ.tokens_saved ?? 0;
    const pct = econ.save_pct != null ? `${econ.save_pct}%` : "—";
    $("#homeEcon").innerHTML = `<b>${esc(String(loc))}</b> local · <b>${esc(
      String(saved)
    )}</b> saved vs dump · ${esc(pct)} · ${esc(String(econ.turns ?? 0))} turns`;
  }

  if ($("#homeSys")) {
    const compose = h.compose || {};
    const rows = [
      ["Status", health.status || (health.up ? "up" : "down")],
      ["Live stale", health.live_stale ? "yes — catch up" : "no"],
      ["Compose", compose.ok ? "ok" : compose.error || "check"],
      ["Open run", compose.active_run || "none"],
      ["Smoke models", (h.multi_smoke_models || []).join(", ") || "—"],
    ];
    $("#homeSys").innerHTML = rows
      .map(
        ([k, v]) =>
          `<li><span class="os-sys-k">${esc(k)}</span><span class="os-sys-v">${esc(v)}</span></li>`
      )
      .join("");
  }

  // Header ship pill (top bar)
  if ($("#shipBadge")) {
    const st = ship.status || "…";
    $("#shipBadge").textContent = st;
    $("#shipBadge").title = (ship.why || []).join(" · ");
  }

  const list = (id, items, empty) => {
    const el = $(id);
    if (!el) return;
    if (!items || !items.length) {
      el.innerHTML = `<li class="muted">${esc(empty)}</li>`;
      return;
    }
    el.innerHTML = items.map((x) => `<li>${esc(String(x).replace(/^-\s*/, ""))}</li>`).join("");
  };
  list("#homeLoops", h.open_loops, "No open loops in bonds");
  const next = [...(h.next_moves || []), ...(h.working_open || [])].slice(0, 8);
  list("#homeNext", next, "No next moves / working items");
  list("#homeBonds", h.residual_bonds, "No residual bonds listed");

  // Verkle step-map (primary home surface)
  try {
    renderVerkleMap(h);
  } catch (e) {
    console.error("renderVerkleMap", e);
  }
}

/* --- Chat-first home --- */
const CHAT_KEY = "mag_chat_v1";
let chatMode = "agent"; // agent | ask | dispatch | tangent
let chatBusy = false;
const AGENT_SESSION = "dashboard";
/** @type {{path:string, chip:string, attach_text:string}[]} */
let composePending = [];

function renderComposeAttach() {
  const el = $("#composeAttach");
  if (!el) return;
  if (!composePending.length) {
    el.hidden = true;
    el.innerHTML = "";
    return;
  }
  el.hidden = false;
  el.innerHTML = composePending
    .map(
      (a, i) =>
        `<div class="attach-chip" data-i="${i}">
          <span class="attach-chip-label">${esc(a.chip || a.path)}</span>
          <button type="button" class="attach-chip-x" data-i="${i}" title="Remove">×</button>
        </div>`
    )
    .join("");
  el.querySelectorAll(".attach-chip-x").forEach((btn) => {
    btn.addEventListener("click", () => {
      const i = Number(btn.getAttribute("data-i"));
      composePending.splice(i, 1);
      renderComposeAttach();
    });
  });
}

async function uploadBlob(fileOrBlob, filename) {
  const buf = await fileOrBlob.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  const b64 = btoa(binary);
  const res = await postJSON("/api/v1/agent/upload", {
    filename: filename || "paste.bin",
    data: b64,
  });
  if (!res || res.ok === false) throw new Error(res?.error || "upload failed");
  composePending.push({
    path: res.path,
    chip: res.chip || res.path,
    attach_text: res.attach_text || `[Attached: ${res.path}]`,
  });
  renderComposeAttach();
  if ($("#chatStatus")) {
    $("#chatStatus").textContent = `Attached ${res.path}`;
  }
  return res;
}

async function refreshChatQuota() {
  const el = $("#chatQuota");
  if (!el) return;
  try {
    const q = await getJSON("/api/v1/quota");
    const rows = q.providers || q.budgets || [];
    const ds =
      rows.find((r) => (r.provider || r.id) === "deepseek") ||
      (q.budgets || []).find((r) => r.provider === "deepseek");
    if (!ds) {
      el.textContent = "quota —";
      return;
    }
    const used = ds.used_tokens ?? ds.tokens ?? 0;
    const max = ds.max_tokens;
    const calls = ds.used_calls ?? ds.calls ?? 0;
    el.textContent =
      max != null
        ? `deepseek ${used}/${max} tok · ${calls} calls`
        : `deepseek ${used} tok · ${calls} calls`;
  } catch {
    el.textContent = "quota —";
  }
}

function loadChatHistory() {
  try {
    const raw = localStorage.getItem(CHAT_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.slice(-80) : [];
  } catch {
    return [];
  }
}

function saveChatHistory(msgs) {
  localStorage.setItem(CHAT_KEY, JSON.stringify(msgs.slice(-80)));
}

async function refreshEconomy() {
  try {
    const e = await getJSON("/api/v1/economy");
    const t = e.today || {};
    if ($("#econLocal")) $("#econLocal").textContent = String(t.local_tokens ?? 0);
    if ($("#econCf")) $("#econCf").textContent = String(t.counterfactual_tui_tokens ?? 0);
    if ($("#econSaved")) $("#econSaved").textContent = String(t.tokens_saved ?? 0);
    if ($("#econPct")) {
      const p = t.save_pct != null ? `${t.save_pct}% avoided` : "—";
      $("#econPct").textContent = p;
    }
    if ($("#econTurns")) $("#econTurns").textContent = `${t.turns ?? 0} turns today`;
    if ($("#economyGoal") && e.goal) $("#economyGoal").textContent = e.goal;
    if ($("#chatStatus") && e.chat_prompt_loaded) {
      // leave status unless idle
    }
  } catch {
    /* lab may be restarting */
  }
}

function mdTable(block) {
  const rows = block
    .trim()
    .split("\n")
    .map((r) => r.trim())
    .filter((r) => r.startsWith("|"));
  if (rows.length < 2) return null;
  const parse = (row) =>
    row
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim());
  const head = parse(rows[0]);
  let bodyRows = rows.slice(1);
  if (bodyRows[0] && /^\|?[\s:-]+/.test(bodyRows[0].replace(/\|/g, ""))) {
    bodyRows = bodyRows.slice(1);
  }
  let html = '<table class="md-table"><thead><tr>';
  head.forEach((h) => {
    html += `<th>${esc(h)}</th>`;
  });
  html += "</tr></thead><tbody>";
  bodyRows.forEach((r) => {
    html += "<tr>";
    parse(r).forEach((c) => {
      html += `<td>${esc(c)}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table>";
  return html;
}

function lightMd(s) {
  // Markdown-ish for chat: tables, code fences, bold, lists (escaped)
  const raw = s || "";
  const parts = [];
  let i = 0;
  const fence = /```[\w]*\n([\s\S]*?)```/g;
  let m;
  const segments = [];
  let last = 0;
  while ((m = fence.exec(raw))) {
    if (m.index > last) segments.push({ t: "text", v: raw.slice(last, m.index) });
    segments.push({ t: "code", v: m[1] });
    last = m.index + m[0].length;
  }
  if (last < raw.length) segments.push({ t: "text", v: raw.slice(last) });
  if (!segments.length) segments.push({ t: "text", v: raw });

  function formatText(chunk) {
    // extract markdown tables
    const lines = chunk.split("\n");
    let out = "";
    let buf = [];
    const flush = () => {
      if (!buf.length) return;
      const block = buf.join("\n");
      buf = [];
      if (block.includes("|") && block.split("\n").filter((l) => l.trim().startsWith("|")).length >= 2) {
        const tbl = mdTable(block);
        if (tbl) {
          out += tbl;
          return;
        }
      }
      let t = esc(block);
      t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
      t = t.replace(/^### (.+)$/gm, "<div class='md-h'>$1</div>");
      t = t.replace(/^## (.+)$/gm, "<div class='md-h'>$1</div>");
      t = t.replace(/^# (.+)$/gm, "<div class='md-h'>$1</div>");
      t = t.replace(/^\* (.+)$/gm, "<div class='md-li'>· $1</div>");
      t = t.replace(/^- (.+)$/gm, "<div class='md-li'>· $1</div>");
      t = t.replace(/^\d+\. (.+)$/gm, "<div class='md-li'>$1</div>");
      t = t.replace(/\n\n/g, "<br/><br/>");
      t = t.replace(/\n/g, "<br/>");
      out += t;
    };
    for (const line of lines) {
      if (line.trim().startsWith("|")) buf.push(line);
      else {
        flush();
        buf = [line];
        flush();
        buf = [];
      }
    }
    flush();
    return out;
  }

  for (const seg of segments) {
    if (seg.t === "code") {
      parts.push(`<pre class="md-pre"><code>${esc(seg.v)}</code></pre>`);
    } else {
      parts.push(formatText(seg.v));
    }
  }
  return parts.join("");
}

function renderChat() {
  const log = $("#chatLog");
  if (!log) return;
  const msgs = loadChatHistory();
  if (!msgs.length) {
    log.innerHTML = `<div class="chat-msg sys"><b>Agent</b> = DeepSeek + Mag tools (Grok-like hands, no Grok tokens) · <b>Ask/Dispatch</b> = talk only · <b>Copy pack</b> for DeepSeek web · paste multi-line in the box.</div>`;
    return;
  }
  log.innerHTML = msgs
    .map((m) => {
      const role = m.role === "user" ? "user" : m.role === "sys" ? "sys" : "mag";
      const meta = m.meta ? `<span class="meta">${esc(m.meta)}</span>` : "";
      let toolsHtml = "";
      if (m.tools && m.tools.length) {
        toolsHtml =
          `<div class="tool-trace">` +
          m.tools.map((t) => `<span class="tool-chip">${esc(String(t))}</span>`).join("") +
          `</div>`;
      }
      const body =
        role === "mag" || role === "sys"
          ? lightMd(m.text || "")
          : esc(m.text || "").replace(/\n/g, "<br/>");
      return `<div class="chat-msg ${role}">${meta}<div class="chat-body">${body}</div>${toolsHtml}</div>`;
    })
    .join("");
  log.scrollTop = log.scrollHeight;
}

function pushChat(role, text, meta, tools) {
  const msgs = loadChatHistory();
  msgs.push({
    role,
    text,
    meta: meta || "",
    tools: tools || null,
    ts: Date.now(),
  });
  saveChatHistory(msgs);
  renderChat();
}

function chatSeat() {
  const el = $("#chatProvider");
  return (el && el.value) || "local";
}

const REMOTE_SEATS = new Set([
  "deepseek",
  "openrouter",
  "openai",
  "anthropic",
  "groq",
  "gemini",
  "xai",
  "together",
]);

function isRemoteSeat(seat) {
  return REMOTE_SEATS.has((seat || "").toLowerCase());
}

function setChatMode(mode) {
  if (mode === "dispatch") chatMode = "dispatch";
  else if (mode === "tangent") chatMode = "tangent";
  else if (mode === "agent") chatMode = "agent";
  else chatMode = "ask";
  const modes = ["agent", "ask", "dispatch", "tangent"];
  modes.forEach((m) => {
    const id =
      m === "agent"
        ? "chatModeAgent"
        : m === "ask"
          ? "chatModeAsk"
          : m === "dispatch"
            ? "chatModeDispatch"
            : "chatModeTangent";
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle("on", chatMode === m);
    el.classList.toggle("ghost", chatMode !== m);
  });
  if ($("#chatStatus")) {
    const seat = chatSeat();
    let line;
    if (chatMode === "agent")
      line = `Ready · Agent · ${isRemoteSeat(seat) ? seat : "deepseek"} · tools on disk · no Grok`;
    else if (chatMode === "tangent") line = "Ready · Tangent (background)";
    else if (isRemoteSeat(seat))
      line = `Ready · ${seat} · pack-first (real API)`;
    else if (seat === "local")
      line = chatMode === "ask" ? "Ready · Local biographer" : "Ready · Local dispatch";
    else line = `Ready · ${chatMode} · ${seat}`;
    $("#chatStatus").textContent = line;
  }
  const ph = $("#chatInput");
  if (ph) {
    ph.placeholder =
      chatMode === "agent"
        ? "Agent goal — multi-line paste OK. Tools: read/write/search Mag files…"
        : "Ask Mag about your filed work…";
  }
}

function formatDispatchAnswer(res) {
  if (!res || typeof res !== "object") return String(res);
  if (res.error && res.ok === false && !res.result && !res.answer)
    return `Error: ${res.error}`;
  const parts = [];
  if (res.seat) parts.push(`seat: ${res.seat}`);
  if (res.job) parts.push(`job: ${res.job}`);
  const prov =
    typeof res.provider === "string"
      ? res.provider
      : res.provider?.provider || res.result?.provider;
  if (prov) parts.push(`provider: ${prov}`);
  if (res.result?.model) parts.push(`model: ${res.result.model}`);
  const head = parts.length ? `[${parts.join(" · ")}]\n\n` : "";
  const ans =
    res.answer ||
    res.result?.text ||
    res.result?.answer ||
    res.result?.local?.answer ||
    res.summary ||
    null;
  if (ans) {
    let body = head + String(ans);
    if (res.ok === false && res.hint) body += `\n\n_${res.hint}_`;
    return body;
  }
  if (res.ok === false) {
    return (
      head +
      `**Failed** ${res.hint || res.error || res.result?.error || JSON.stringify(res).slice(0, 800)}`
    );
  }
  // grok_tui pack style
  if (res.context_pack || res.pack_excerpt || res.context_pack_excerpt || res.hint) {
    return (
      head +
      (res.hint || "Escalate pack ready — open Grok with context-pack, not full chat.") +
      "\n\n" +
      String(res.pack_excerpt || res.context_pack_excerpt || res.context_chars || "").slice(0, 1200)
    );
  }
  return head + JSON.stringify(res, null, 2).slice(0, 3500);
}

async function copyContextPack() {
  const st = $("#chatStatus");
  try {
    if (st) st.textContent = "Building pack…";
    const res = await getJSON("/api/v1/context-pack");
    if (!res || res.ok === false) throw new Error(res?.error || "pack failed");
    const paste = res.paste || res.text || "";
    await navigator.clipboard.writeText(paste);
    if (st) st.textContent = `Pack copied (${res.chars || paste.length} chars) · ${res.path || ""}`;
    pushChat(
      "mag",
      `**Pack on clipboard** (${res.chars || paste.length} chars)\n\nPaste into DeepSeek web as message 1, then your goal as message 2.\n\nFile: \`${res.path || "memory/context_pack_latest.md"}\``,
      "copy-pack"
    );
  } catch (e) {
    if (st) st.textContent = "Copy pack failed";
    pushChat("mag", `Copy pack failed: ${e.message || e}`, "error");
  }
}

/**
 * Stream one Mag agent turn via SSE. Calls onDelta(text) live, then resolves
 * with the final {answer, tools, provider, ...} from the done event.
 */
async function streamAgentTurn(body, onDelta) {
  const res = await fetch("/api/v1/agent/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    const errText = await res.text().catch(() => "");
    throw new Error(`agent stream HTTP ${res.status} ${errText.slice(0, 200)}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let done = null;
  let error = null;
  for (;;) {
    const { value, done: finished } = await reader.read();
    if (finished) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk
        .split("\n")
        .find((l) => l.startsWith("data:"));
      if (!line) continue;
      let ev;
      try {
        ev = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (ev.type === "delta" && typeof ev.text === "string") {
        if (onDelta) onDelta(ev.text);
      } else if (ev.type === "tool") {
        if (onDelta) onDelta(`\n[${ev.name}] ${ev.args || ""}\n`);
      } else if (ev.type === "done") {
        done = ev;
      } else if (ev.type === "error") {
        error = ev.error || "agent stream error";
      }
    }
  }
  if (error) throw new Error(error);
  if (!done) throw new Error("agent stream ended without done event");
  return done;
}

async function sendSteer() {
  const input = $("#steerInput");
  let cmd = (input?.value || "").trim();
  if (!cmd) return;
  if (!cmd.startsWith("!")) cmd = "!" + cmd;
  try {
    const r = await postJSON("/api/v1/governance", { cmd });
    pushChat("mag", `steer: ${cmd} · chat=${r.chat_queued ? "ok" : "idle"} · workers=${(r.workers || []).length}`, r && r.ok ? "ok" : "error");
    if (input) input.value = "";
  } catch (e) {
    pushChat("mag", `steer failed: ${e.message || e}`, "error");
  }
}

async function sendGovernanceSteer(cmd) {
  cmd = (cmd || "").trim();
  if (!cmd) return;
  if (!cmd.startsWith("!")) cmd = "!" + cmd;
  try {
    const r = await postJSON("/api/v1/governance", { cmd });
    toast(`Steer ${cmd} · chat ${r.chat_queued ? "queued" : "idle"} · ${(r.workers || []).length} worker(s)`, !!r.ok);
  } catch (e) {
    toast(String(e.message || e), false);
  }
}

let _inboxPollTimer = null;

async function loadOperatorInboxStatus() {
  const el = $("#operatorInboxStatus");
  if (!el) return;
  try {
    const s = await getJSON("/api/v1/operator-inbox");
    const n = s.pending_n || 0;
    el.textContent = n ? `${n} queued for next checkpoint` : "0 queued";
    el.classList.toggle("warn", n > 0);
  } catch {
    el.textContent = "inbox offline";
  }
}

function startOperatorInboxPoll() {
  loadOperatorInboxStatus();
  if (_inboxPollTimer) clearInterval(_inboxPollTimer);
  _inboxPollTimer = setInterval(loadOperatorInboxStatus, 4000);
}

async function commitOperatorGuidance() {
  const input = $("#operatorInboxInput");
  const text = (input?.value || "").trim();
  if (!text) return;
  try {
    const r = await postJSON("/api/v1/operator-inbox", { text, source: "dashboard" });
    if (input) input.value = "";
    await loadOperatorInboxStatus();
    toast(
      r.pending_n ? `Queued · ${r.pending_n} waiting at checkpoint` : "Queued",
      !!r.ok
    );
  } catch (e) {
    toast(String(e.message || e), false);
  }
}

async function loadGovernance() {
  const lay = $("#governanceLayman");
  const themes = $("#governanceThemes");
  const cursorNote = $("#governanceCursorNote");
  const drainer = $("#govDrainerToggle");
  const behavioral = $("#govBehavioralToggle");
  try {
    const g = await getJSON("/api/v1/governance");
    if (lay) lay.textContent = g.layman || "";
    if (cursorNote) cursorNote.textContent = g.cursor_note || "";
    if (drainer) {
      drainer.disabled = !!(g.drainer && g.drainer.env_locked);
      drainer.checked = !!(g.drainer && g.drainer.enabled);
    }
    if (behavioral) {
      behavioral.checked = !!(g.autonomy && g.autonomy.inject_behavioral_pack);
    }
    const leaf = g.behavioral_loop && g.behavioral_loop.leaf;
    if (themes) {
      const rows = (leaf && leaf.themes) || [];
      themes.innerHTML = rows.length
        ? rows
            .map(
              (t) =>
                `<li><strong>${esc(t.id)}</strong> ${esc(t.title)}${t.avoid ? `<br/><span class="muted sm">${esc(t.avoid.slice(0, 140))}</span>` : ""}</li>`
            )
            .join("")
        : `<li class="muted">No behavioral leaf yet — scout mines memory/improve/daily/*-behavioral.md</li>`;
      if (leaf && leaf.path) {
        themes.innerHTML += `<li class="muted sm">source: ${esc(leaf.path)} · ${g.behavioral_loop.remedy_cards || 0} remedy cards</li>`;
      }
    }
  } catch (e) {
    if (lay) lay.textContent = "Governance unavailable: " + (e.message || e);
  }
}

async function onGovDrainerChange() {
  const t = $("#govDrainerToggle");
  if (!t || t.disabled) return;
  try {
    await postJSON("/api/v1/governance", { drainer: t.checked });
    toast(t.checked ? "Drainer ON — queue auto-advances" : "Drainer OFF", true);
    await loadStatus();
  } catch (e) {
    toast(String(e.message || e), false);
  }
}

async function onGovBehavioralChange() {
  const t = $("#govBehavioralToggle");
  if (!t) return;
  try {
    await postJSON("/api/v1/governance", { inject_behavioral_pack: t.checked });
    toast(t.checked ? "Behavioral themes in every pack" : "Behavioral pack injection off", true);
  } catch (e) {
    toast(String(e.message || e), false);
  }
}

async function sendChat() {
  if (chatBusy) return;
  const input = $("#chatInput");
  let q = (input?.value || "").trim();
  if (composePending.length) {
    const blocks = composePending.map((a) => a.attach_text).join("\n\n");
    q = q ? `${blocks}\n\n${q}` : blocks + "\n\n(Describe what to do with the attachment.)";
  }
  if (!q) return;
  chatBusy = true;
  const seat = chatSeat();
  const userShow =
    (input?.value || "").trim() ||
    (composePending.length ? composePending.map((a) => a.chip).join(", ") : q);
  if (input) input.value = "";
  composePending = [];
  renderComposeAttach();
  pushChat("user", userShow, `${chatMode} · ${seat}`);
  if ($("#chatStatus")) $("#chatStatus").textContent = `Thinking (${seat})…`;
  const pending = { role: "mag", text: "…", meta: "pending", ts: Date.now() };
  const hist = loadChatHistory();
  hist.push(pending);
  saveChatHistory(hist);
  renderChat();
  // mark last as pending visually
  const log = $("#chatLog");
  const last = log?.lastElementChild;
  if (last) last.classList.add("pending");

  try {
    let text = "";
    let meta = chatMode;
    let tools = null;
    if (chatMode === "agent") {
      const provider = isRemoteSeat(seat) ? seat : seat === "local" ? "ollama" : "deepseek";
      // Live streaming window: update the pending bubble as deltas arrive.
      let acc = "";
      const updatePending = (delta) => {
        acc += delta;
        const msgs = loadChatHistory();
        const p = msgs.find((m) => m.meta === "pending");
        if (p) {
          p.text = acc || "…";
          saveChatHistory(msgs);
          renderChat();
        }
      };
      const done = await streamAgentTurn(
        { goal: q, provider, session_id: AGENT_SESSION, reset: false },
        updatePending
      );
      text = done.answer || acc || "(empty)";
      tools = done.tools || [];
      meta = `agent · ${done.provider || provider} · tools=${(tools || []).length} · live`;
    } else if (chatMode === "tangent") {
      const res = await postJSON("/api/v1/tangent", {
        prompt: q,
        source: "dashboard",
        prefer_gemini: true,
        run: true,
        provider: isRemoteSeat(seat) ? seat : undefined,
      });
      const r = res.result || {};
      meta = `tangent · ${r.id || res.queued?.id || "?"} · ${res.ok === false || r.ok === false ? "fail" : "ok"}`;
      text =
        `**Background tangent**\n\n` +
        (r.summary || res.error || JSON.stringify(res).slice(0, 600)) +
        `\n\n_File:_ \`${r.path || "memory/tangents/latest.md"}\`\n` +
        `_Elevate to Grok only if useful — pack path, not full chat._`;
    } else if (chatMode === "dispatch" || isRemoteSeat(seat) || (chatMode === "ask" && seat !== "local")) {
      // Remote seats always dispatch pack-first with seat=remote (must hit real API).
      const body = { goal: q };
      if (seat === "local") {
        body.seat = "local";
        body.provider = "ollama";
      } else if (seat === "auto") {
        /* classify */
      } else if (isRemoteSeat(seat)) {
        body.provider = seat;
        body.seat = "remote";
      } else {
        body.provider = seat;
      }
      const res = await postJSON("/api/v1/dispatch", body);
      text = formatDispatchAnswer(res);
      const prov =
        typeof res.provider === "string"
          ? res.provider
          : res.provider?.provider || res.result?.provider || seat;
      meta = `dispatch · ${res.seat || "?"} · ${prov} · ${res.ok === false ? "fail" : "ok"}`;
      if (res.economy_last) {
        meta += ` · saved ~${res.economy_last.tokens_saved ?? "?"} tok`;
      }
    } else {
      const res = await postJSON("/api/v1/ask", { question: q, use_llm: true });
      text = res.answer || res.error || JSON.stringify(res, null, 2);
      const last = res.economy_last || {};
      const nsrc = (res.sources || []).length;
      meta =
        res.ok === false
          ? "ask · fail"
          : `ask · L0 · 0 Grok · ~${last.local_tokens ?? "?"} local · ~${last.tokens_saved ?? "?"} saved · ${nsrc} sources`;
    }
    const msgs = loadChatHistory().filter((m) => m.meta !== "pending");
    msgs.push({ role: "mag", text, meta, tools: tools || null, ts: Date.now() });
    saveChatHistory(msgs);
    renderChat();
    refreshEconomy();
    refreshChatQuota();
  } catch (e) {
    const msgs = loadChatHistory().filter((m) => m.meta !== "pending");
    msgs.push({
      role: "mag",
      text: String(e.message || e),
      meta: "error",
      ts: Date.now(),
    });
    saveChatHistory(msgs);
    renderChat();
  } finally {
    chatBusy = false;
    if ($("#chatStatus")) $("#chatStatus").textContent = "Ready";
    setChatMode(chatMode);
  }
}

const CHAT_MODES_CYCLE = ["agent", "ask", "dispatch", "tangent"];
function cycleChatMode() {
  const i = CHAT_MODES_CYCLE.indexOf(chatMode);
  const next = CHAT_MODES_CYCLE[(i + 1) % CHAT_MODES_CYCLE.length];
  setChatMode(next);
}

let tapestryView = null;
let tapestryReady = null;

function ensureTapestryModule() {
  if (window.MagTapestry) return Promise.resolve();
  if (tapestryReady) return tapestryReady;
  tapestryReady = import(`/static/tapestry.js?v=days-v3`).catch((e) => {
    console.error(e);
    if ($("#tapCaption")) {
      $("#tapCaption").textContent =
        "Could not load 3D module (needs network for three.js CDN once). " + (e.message || e);
    }
    throw e;
  });
  return tapestryReady;
}

async function loadTapestry() {
  try {
    await ensureTapestryModule();
    const pack = await getJSON("/api/v1/tapestry");
    const canvas = $("#tapCanvas");
    if (!canvas) {
      console.warn("tapCanvas missing");
      return;
    }
    if (!window.MagTapestry) {
      if ($("#tapCaption"))
        $("#tapCaption").textContent = "3D module not available";
      return;
    }
    if (!tapestryView) {
      tapestryView = new window.MagTapestry(
        canvas,
        $("#tapCaption"),
        $("#tapMeta"),
        null, // floating hover removed — rail only
        $("#tapHoverRail")
      );
    } else {
      tapestryView.captionEl = $("#tapCaption") || tapestryView.captionEl;
      tapestryView.hoverRailEl = $("#tapHoverRail") || tapestryView.hoverRailEl;
      tapestryView.metaEl = $("#tapMeta") || tapestryView.metaEl;
    }
    tapestryView.setPack(pack);
    window.__tapestryStats = pack.stats || {};
    const leg = $("#daysLegend");
    if (leg && pack.english?.legend) {
      leg.innerHTML = Object.entries(pack.english.legend)
        .map(
          ([k, v]) =>
            `<span class="legend-chip" data-kind="${esc(k)}"><b>${esc(k)}</b> ${esc(v)}</span>`
        )
        .join("");
    }
    if ($("#tapMeta") && pack.english?.blurb) {
      $("#tapMeta").textContent = pack.english.blurb;
    }
    if (window.__lastOverview) renderStats(window.__lastOverview, pack.stats);
    const kick = () => {
      try {
        tapestryView.resize({ forceFit: true });
      } catch (err) {
        console.warn("tapestry resize", err);
      }
    };
    kick();
    requestAnimationFrame(kick);
    setTimeout(kick, 100);
    setTimeout(kick, 350);
  } catch (e) {
    console.error("loadTapestry", e);
    if ($("#tapCaption")) $("#tapCaption").textContent = String(e.message || e);
    // Days list must still work even if 3D dies
    if ($("#tapMeta")) $("#tapMeta").textContent = "Graph failed — list still works";
  }
}

let operatorOs = null;

function copyText(text, statusEl) {
  const t = text || "";
  if (!t) return;
  const done = () => {
    if (statusEl) {
      statusEl.textContent = "Copied.";
      setTimeout(() => {
        statusEl.textContent = "";
      }, 2000);
    }
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(t).then(done).catch(() => {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = t;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      done();
    });
  } else {
    const ta = document.createElement("textarea");
    ta.value = t;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    done();
  }
}

async function loadOperate() {
  try {
    operatorOs = await getJSON("/api/v1/operator-os");
  } catch {
    try {
      operatorOs = await getJSON("/api/operator-os");
    } catch (e) {
      if ($("#osLead")) $("#osLead").textContent = String(e.message || e);
      return;
    }
  }
  const os = operatorOs || {};
  const h = os.health || {};
  const d = os.dna || {};
  const cards = (os.what_was_i_doing || {}).cards || [];
  const bead = cards[0] || {};
  const t = os.next_ticket || {};

  if ($("#osStats")) {
    const up = h.integral === "up";
    const holes = d.n_incomplete || 0;
    $("#osStats").innerHTML = `
      <div class="stat"><b style="color:${up ? "var(--good)" : "var(--warn)"}">${
        up ? "ON" : "OFF"
      }</b><span>Mag office</span></div>
      <div class="stat"><b style="color:${h.ollama ? "var(--good)" : "var(--warn)"}">${
        h.ollama ? "ON" : "OFF"
      }</b><span>Local AI</span></div>
      <div class="stat"><b>${d.n_leaves ?? "—"}</b><span>days filed</span></div>
      <div class="stat"><b style="color:${holes ? "var(--warn)" : "var(--good)"}">${holes}</b><span>holes</span></div>
    `;
  }

  // Latest bead — the thing someone is looking at
  if ($("#osBeadTitle")) {
    $("#osBeadTitle").textContent = bead.title || "No days filed yet";
  }
  if ($("#osBeadMeta")) {
    const sid = bead.session_id ? String(bead.session_id).slice(0, 13) + "…" : "";
    $("#osBeadMeta").textContent = [
      bead.end_minute || bead.start_minute || "",
      bead.dominant_theme || "",
      sid,
    ]
      .filter(Boolean)
      .join(" · ") || "Close a Grok session (or backfill) to create the first bead.";
  }
  if ($("#osBeadBlurb")) {
    $("#osBeadBlurb").textContent = bead.blurb || bead.one_liner || "—";
  }
  if ($("#osBeadBullets")) {
    const bullets = bead.bullets || [];
    $("#osBeadBullets").innerHTML = bullets.length
      ? bullets.map((b) => `<li>${esc(b)}</li>`).join("")
      : "";
  }
  if ($("#osOpenBits")) {
    const loops = (os.what_was_i_doing || {}).open_loops || [];
    const todos = (os.what_was_i_doing || {}).todo_open || [];
    const bits = [];
    if (loops[0]) bits.push(`Open loop: ${loops[0].replace(/^-\s*/, "")}`);
    if (todos[0]) bits.push(`Todo: ${todos[0]}`);
    $("#osOpenBits").textContent = bits.join(" · ");
  }

  if ($("#osTicket")) {
    $("#osTicket").innerHTML = `
      <div class="os-ticket-id">${esc(t.id || "—")}</div>
      <div class="os-ticket-title">${esc(t.title || "")}</div>
      <p class="os-ticket-body">${esc(t.prompt || "")}</p>
    `;
  }

  if ($("#osSysList")) {
    const rows = [
      ["Mag office", h.integral === "up" ? "running" : "stopped — start: python main.py lab"],
      ["Local AI (Ollama)", h.ollama ? "up" : "down"],
      ["Diary complete", `${d.complete_pct ?? "—"}% of ${d.n_sessions ?? "—"} days`],
      ["Roadmap", (os.forest || {}).position || "—"],
    ];
    $("#osSysList").innerHTML = rows
      .map(
        ([k, v]) =>
          `<li><span class="os-sys-k">${esc(k)}</span><span class="os-sys-v">${esc(v)}</span></li>`
      )
      .join("");
  }

  if ($("#osFeed") && os.templates?.build) {
    $("#osFeed").value = os.templates.build;
    document.querySelectorAll("[data-tpl]").forEach((b) => {
      b.classList.toggle("tpl-on", b.dataset.tpl === "build");
      b.classList.toggle("ghost", b.dataset.tpl !== "build");
    });
  }

  // stash latest session id for buttons
  window.__osLatestSid = bead.session_id || null;
}

function showOsTemplate(key) {
  if (!operatorOs?.templates) return;
  const t = operatorOs.templates[key];
  if ($("#osFeed") && t) $("#osFeed").value = t;
  document.querySelectorAll("[data-tpl]").forEach((b) => {
    const on = b.dataset.tpl === key;
    b.classList.toggle("tpl-on", on);
    b.classList.toggle("ghost", !on);
  });
}

function barRow(label, value, max, suffix) {
  const pct = max > 0 ? Math.max(2, Math.round((100 * value) / max)) : 0;
  return `<div class="fbar">
    <div class="fbar-lab" title="${esc(label)}">${esc(label)}</div>
    <div class="fbar-track"><div class="fbar-fill" style="width:${pct}%"></div></div>
    <div class="fbar-val">${esc(String(value))}${suffix ? esc(suffix) : ""}</div>
  </div>`;
}

async function loadFlow() {
  const meta = $("#flowMeta");
  if (meta) meta.textContent = "Loading…";
  try {
    const d = await getJSON("/api/idea-flow");
    if (!d.ok && d.error) throw new Error(d.error);
    const pic = d.spend?.combined_picture || {};
    if (meta) {
      meta.textContent = `as of ${String(d.ts || "").slice(0, 19)} · local-first ledger`;
    }
    if ($("#flowNote")) $("#flowNote").textContent = d.note || "";
    if ($("#flowStats")) {
      const ideas = d.ideas_summary || {};
      const art = d.artifacts?.counts || {};
      $("#flowStats").innerHTML = `
        <div class="stat"><b>${pic.chat_calls ?? 0}</b><span>chat calls</span></div>
        <div class="stat"><b>~${pic.local_est_out_tokens ?? 0}</b><span>local est out tok</span></div>
        <div class="stat"><b>${pic.local_api_tokens ?? 0}</b><span>local API tok</span></div>
        <div class="stat"><b>${pic.remote_api_tokens ?? 0}</b><span>remote API tok</span></div>
        <div class="stat"><b>${pic.wall_s ?? 0}s</b><span>wall time</span></div>
        <div class="stat"><b>${ideas.reconciled ?? 0}/${ideas.n ?? 0}</b><span>ideas closed</span></div>
        <div class="stat"><b>${art.research_pdfs ?? 0}</b><span>research PDFs</span></div>
        <div class="stat"><b>${art.ingest ?? 0}</b><span>ingest items</span></div>`;
    }

    const models = d.models || [];
    const maxC = Math.max(1, ...models.map((m) => m.calls || 0));
    const maxW = Math.max(1, ...models.map((m) => m.wall_s || 0));
    const maxT = Math.max(1, ...models.map((m) => m.est_out_tokens || 0));
    if ($("#flowModelBars")) {
      $("#flowModelBars").innerHTML =
        models
          .map((m) => {
            const roles = Object.entries(m.roles || {})
              .map(([k, v]) => `${k}:${v}`)
              .join(" ");
            const tag = m.local ? "local" : "cloud?";
            return `<div class="fbar-block">
              <div class="fbar-head"><span class="mono">${esc(m.model)}</span>
                <span class="muted">${esc(tag)} · ok ${m.ok}/${m.calls} · ${roles || "—"}</span></div>
              ${barRow("calls", m.calls, maxC, "")}
              ${barRow("wall s", m.wall_s, maxW, "s")}
              ${barRow("est out", m.est_out_tokens, maxT, " tok")}
            </div>`;
          })
          .join("") || `<div class="muted">No chat rows in usage.jsonl yet</div>`;
    }

    const roles = d.roles || [];
    const maxRC = Math.max(1, ...roles.map((r) => r.calls || 0));
    if ($("#flowRoleBars")) {
      $("#flowRoleBars").innerHTML =
        roles
          .map((r) => {
            const mods = Object.entries(r.models || {})
              .map(([k, v]) => `${k}×${v}`)
              .join(", ");
            return `<div class="fbar-block">
              <div class="fbar-head"><b>${esc(r.role)}</b>
                <span class="muted">${esc(mods)} · ~${r.est_out_tokens} tok · ${r.wall_s}s</span></div>
              ${barRow("calls", r.calls, maxRC, "")}
            </div>`;
          })
          .join("") || `<div class="muted">No roles yet</div>`;
    }

    if ($("#flowProvTable")) {
      $("#flowProvTable").innerHTML =
        (d.providers || [])
          .map((p) => {
            const mark = p.local ? "●" : p.fail && !p.ok ? "✗" : "○";
            const mods = Object.keys(p.models || {}).join(", ") || "—";
            return `<div class="row"><span class="k">${mark} ${esc(p.provider)}</span>
              <span class="v">${p.calls}c · ${p.tokens}t (in ${p.prompt_tokens}/out ${p.completion_tokens}) · ok ${p.ok} fail ${p.fail}<br/><span class="muted">${esc(mods)}</span></span></div>`;
          })
          .join("") || `<div class="muted">No provider_usage.jsonl yet</div>`;
    }

    if ($("#flowRemainTable")) {
      $("#flowRemainTable").innerHTML =
        (d.remaining || [])
          .map((p) => {
            const rem = p.unlimited
              ? "∞ local"
              : `left ${p.remaining_calls ?? "—"}c / ${p.remaining_tokens ?? "—"}t`;
            const used = `used ${p.used_calls ?? 0}c / ${p.used_tokens ?? 0}t`;
            const cfg = p.configured ? "" : " · no key";
            const ok = p.budget_ok === false ? "⚠" : "·";
            return `<div class="row"><span class="k">${ok} ${esc(p.provider)}</span>
              <span class="v">${used} · ${rem}${cfg}${p.unlimited ? "" : ` · reset ~${p.reset_in_hours}h`}</span></div>`;
          })
          .join("") || `<div class="muted">No quota state</div>`;
    }

    // path graph: group role→model edges
    const edges = (d.edges || []).filter((e) => e.kind === "role_model" || e.kind === "idea_seat");
    const maxE = Math.max(1, ...edges.map((e) => e.weight || 0));
    if ($("#flowEdges")) {
      $("#flowEdges").innerHTML =
        edges
          .slice(0, 48)
          .map((e) => {
            const w = e.weight || 0;
            const pct = Math.max(4, Math.round((100 * w) / maxE));
            return `<div class="fedge">
              <span class="fedge-from mono">${esc(e.from)}</span>
              <span class="fedge-arr">→</span>
              <span class="fedge-to mono">${esc(e.to)}</span>
              <span class="fedge-bar"><i style="width:${pct}%"></i></span>
              <span class="fedge-w">${w}</span>
            </div>`;
          })
          .join("") || `<div class="muted">No edges yet — run multi-smoke or research-pack</div>`;
    }

    if ($("#flowIdeas")) {
      const ideas = d.ideas || [];
      $("#flowIdeas").innerHTML =
        ideas
          .map((idea) => {
            const rec = idea.reconciliation || {};
            const srcs = (idea.sources || [])
              .map((s) => (s.ok ? "✓" : "✗") + " " + (s.url || "").slice(0, 48))
              .join(" · ");
            const ans = (idea.answers || [])
              .map(
                (a) =>
                  `<div class="idea-ans"><span class="role-tag">${esc(a.seat)}</span> ~${a.est_tokens} tok<br/><span class="muted">${esc((a.preview || "").slice(0, 200))}</span></div>`
              )
              .join("");
            const links = [];
            if (idea.files?.pdf) links.push(`<a href="${esc(idea.files.pdf)}" target="_blank">PDF</a>`);
            if (idea.files?.json) links.push(`<a href="${esc(idea.files.json)}" target="_blank">JSON</a>`);
            if (idea.files?.prompt) links.push(`<a href="${esc(idea.files.prompt)}" target="_blank">prompt</a>`);
            return `<div class="idea-card">
              <div class="idea-head">
                <span class="status-pill ${esc(rec.status || "open")}">${esc(rec.status || "open")}</span>
                <span class="muted mono">${esc(idea.id || "")}</span>
              </div>
              <div class="idea-ask">${esc(idea.ask || "")}</div>
              <div class="muted">sources ${esc(rec.sources_ok || "")} · elevate → ${esc(String(rec.elevate_to || "—"))} · ${esc(rec.note || "")}</div>
              <div class="muted" style="margin-top:0.25rem">${esc(srcs || "no sources")}</div>
              ${ans || '<div class="muted">No lesser-model answers on disk yet</div>'}
              <div class="idea-links">${links.join(" · ") || "—"}</div>
            </div>`;
          })
          .join("") || `<div class="muted">No research packs yet. <code>python main.py research-pack --ask "…" --url "…" --run</code></div>`;
    }

    const art = d.artifacts || {};
    const counts = art.counts || {};
    if ($("#flowArtifacts")) {
      $("#flowArtifacts").innerHTML = `
        <div class="row"><span class="k">research PDFs</span><span class="v">${counts.research_pdfs ?? 0}</span></div>
        <div class="row"><span class="k">dossiers</span><span class="v">${counts.dossiers ?? 0}</span></div>
        <div class="row"><span class="k">briefs</span><span class="v">${counts.briefs ?? 0}</span></div>
        <div class="row"><span class="k">visual packs</span><span class="v">${counts.visual_packs ?? 0}</span></div>
        <div class="row"><span class="k">ingest</span><span class="v">${counts.ingest ?? 0}</span></div>
        <div class="row"><span class="k">context pack</span><span class="v">${art.context_pack ? "yes" : "no"}</span></div>
        <div class="row"><span class="k">verkle tip</span><span class="v mono">${esc(shortHash(art.verkle_tip?.root))}</span></div>`;
    }
    if ($("#flowArtifactList")) {
      const list = [
        ...(art.research_pdfs || []).map((x) => ({ ...x, label: "PDF" })),
        ...(art.briefs || []).slice(0, 6).map((x) => ({ ...x, label: "brief" })),
        ...(art.visual_packs || []).slice(0, 4).map((x) => ({ ...x, label: "visual" })),
      ];
      $("#flowArtifactList").innerHTML = list
        .map((x) => {
          const href = x.href ? `<a href="${esc(x.href)}" target="_blank">${esc(x.name)}</a>` : esc(x.name);
          return `<div class="art-row"><span class="role-tag">${esc(x.label || x.kind)}</span> ${href}</div>`;
        })
        .join("");
    }

    if ($("#flowTimeline")) {
      $("#flowTimeline").textContent =
        (d.timeline || [])
          .map((r) => {
            const mod = r.model ? ` ${r.model}` : "";
            const role = r.role ? `/${r.role}` : "";
            const artf = r.artifact ? ` → ${r.artifact}` : "";
            const tok = r.est_out_tokens != null ? ` ~${r.est_out_tokens}t` : "";
            const ms = r.ms != null ? ` ${r.ms}ms` : "";
            return `${String(r.ts || "").slice(0, 19)}  ${r.lane || "?"}  ${r.action}${role}${mod}${ms}${tok}  ${r.ok ? "ok" : "fail"}  ${(r.detail || "").slice(0, 50)}${artf}`;
          })
          .join("\n") || "(empty)";
    }
  } catch (e) {
    if (meta) meta.textContent = "Failed to load flow";
    if ($("#flowNote")) $("#flowNote").textContent = String(e.message || e);
  }
}

const CHAMBERS = [
  ["connection", "Connection"],
  ["signature", "Fourier signature"],
  ["residual", "Residual"],
  ["belt", "Belt / twist"],
  ["attention", "Attention"],
  ["dual_orbit", "Dual orbit"],
  ["spectral", "Spectral"],
];

let vis = null;
let visPack = null;
let walkTimer = null;

function renderVisInspector(sel) {
  const el = $("#visDetail");
  if (!el) return;
  if (!sel) {
    el.innerHTML = `<p class="muted">Click a circle. You’ll get plain English first, then full text and links.</p>`;
    return;
  }
  const f = sel.full || sel.node || {};
  const edges = sel.edges || [];
  const eli5 =
    sel.eli5 ||
    (window.MAG_ROLE_ELI5 && window.MAG_ROLE_ELI5[f.role]) ||
    "A piece of this session’s living record.";
  el.innerHTML = `
    <span class="role-tag">${esc(f.role || "node")}</span>
    <div><b>${esc(f.label || f.id)}</b></div>
    <p style="margin:0.35rem 0;color:var(--accent)">${esc(eli5)}</p>
    <div class="muted mono" style="font-size:0.72rem">${esc(f.id)}</div>
    <p style="margin:0.5rem 0"><b>Full text</b><br/>${esc(f.plain || "—")}</p>
    ${f.weight != null ? `<div class="muted">weight ${Number(f.weight).toFixed(3)} (how strong this pull is — not a grade)</div>` : ""}
    ${f.score != null ? `<div class="muted">score ${esc(f.score)}</div>` : ""}
    <div class="links">
      <b>Connected to (${edges.length})</b>
      ${
        edges
          .map(
            (e) =>
              `<div><span class="mono">${esc(e.kind)}</span> · ${esc(e.source)} → ${esc(e.target)}
              ${e.reason ? ` · ${esc(e.reason)}` : ""}</div>`
          )
          .join("") || "<div class='muted'>—</div>"
      }
    </div>
  `;
}

function renderVisTable(pack, chamber) {
  const el = $("#visTable");
  if (!el || !pack) return;
  const ch = (pack.chambers || {})[chamber] || {};
  const rows = [];
  if (chamber === "connection" || chamber === "residual" || chamber === "spectral") {
    (ch.nodes || []).slice(0, 40).forEach((n) => {
      rows.push([n.role, `${n.label}: ${(n.plain || "").slice(0, 80)}`]);
    });
  } else if (chamber === "signature") {
    (ch.points || []).forEach((p) => {
      rows.push([p.theme || p.label, `T=${p.S} ${p.active ? "· active" : ""}`]);
    });
    (ch.fourier || []).slice(0, 6).forEach((c) => {
      rows.push([`k=${c.k}`, `amp_n=${Number(c.amp_n || 0).toFixed(3)}`]);
    });
  } else if (chamber === "belt") {
    rows.push(["holonomy", ch.odd ? "ODD" : "EVEN"]);
    rows.push(["note", ch.note || ""]);
    (ch.frames || []).forEach((f) => rows.push(["frame", f]));
  } else if (chamber === "attention") {
    (ch.frames || []).forEach((f, i) => {
      rows.push([f, `score ${ch.scores?.[i] ?? "—"}`]);
    });
  } else if (chamber === "dual_orbit") {
    rows.push(["center", ch.center || ""]);
    rows.push(["hands", (ch.track_a?.items || []).join(", ")]);
    rows.push(["mirror", (ch.track_b?.items || []).join(", ")]);
    rows.push(["tension", String(ch.tension ?? "")]);
  }
  el.innerHTML = rows
    .map(([k, v]) => `<div class="row"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`)
    .join("") || `<div class="muted">No rows</div>`;
}

function renderVisModules(pack) {
  const list = $("#visModuleList");
  const filters = $("#visFilters");
  if (!list || !pack) return;
  const nodes = pack.chambers?.connection?.nodes || [];
  const byRole = {};
  nodes.forEach((n) => {
    const r = n.role || "other";
    if (!byRole[r]) byRole[r] = [];
    byRole[r].push(n);
  });
  const mods = [
    ["all", `All nodes (${nodes.length})`],
    ...Object.entries(byRole).map(([r, arr]) => [r, `${r} (${arr.length})`]),
  ];
  list.innerHTML = mods
    .map(
      ([id, label], i) =>
        `<button type="button" data-mod="${esc(id)}" class="${i === 0 ? "on" : ""}">${esc(label)}</button>`
    )
    .join("");
  list.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      list.querySelectorAll("button").forEach((b) => b.classList.remove("on"));
      btn.classList.add("on");
      const mod = btn.dataset.mod;
      if (mod === "all") {
        vis?.setRoleFilter(null);
        renderVisInspector(null);
      } else {
        vis?.setRoleFilter(new Set([mod]));
        const first = byRole[mod]?.[0];
        if (first) vis?.selectById(first.id);
      }
      renderVisTable(pack, vis?.chamber || "connection");
    });
  });
  // node list under filters — clickable fidelity
  const flat = nodes.slice(0, 60);
  filters.innerHTML = flat
    .map(
      (n) =>
        `<label data-nid="${esc(n.id)}"><input type="checkbox" checked data-role="${esc(
          n.role
        )}" /> <span class="mono">${esc(n.role)}</span> ${esc(n.label)}</label>`
    )
    .join("");
  filters.querySelectorAll("label").forEach((lab) => {
    lab.addEventListener("click", (e) => {
      if (e.target.tagName === "INPUT") return;
      e.preventDefault();
      vis?.selectById(lab.dataset.nid);
    });
  });
}

function fillSessionSelect(sessions) {
  const sel = $("#visSessionSelect");
  if (!sel) return;
  const list = sessions && sessions.length ? sessions : overview?.sessions || [];
  const cur = visualSessionId || "latest";
  const opts = [
    `<option value="latest">latest (pointer)</option>`,
    ...list.map(
      (s) =>
        `<option value="${esc(s.session_id)}">${esc(sessionLabel(s))} · ${esc(
          s.session_id.slice(0, 8)
        )}…</option>`
    ),
  ];
  sel.innerHTML = opts.join("");
  // keep selection if present
  const ids = new Set(["latest", ...list.map((s) => s.session_id)]);
  sel.value = ids.has(cur) ? cur : "latest";
}

function renderPins() {
  const host = $("#visPins");
  if (!host) return;
  const pins = loadPins();
  const sessions = overview?.sessions || [];
  const byId = Object.fromEntries(sessions.map((s) => [s.session_id, s]));
  if (!pins.length) {
    host.innerHTML = `<span class="muted" style="font-size:0.75rem">Pin sessions to flip maps without hunting the table.</span>`;
    return;
  }
  host.innerHTML = pins
    .map((id) => {
      const lab = sessionLabel(byId[id] || { session_id: id, title: id.slice(0, 12) });
      const on = id === visualSessionId ? "on" : "";
      return `<button type="button" class="${on}" data-pin="${esc(id)}" title="${esc(id)}">${esc(
        lab
      )} <span class="x" data-unpin="${esc(id)}">×</span></button>`;
    })
    .join("");
  host.querySelectorAll("button[data-pin]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const unpin = e.target?.dataset?.unpin;
      if (unpin) {
        e.stopPropagation();
        savePins(loadPins().filter((x) => x !== unpin));
        renderPins();
        return;
      }
      loadVisual(btn.dataset.pin);
    });
  });
}

function pinSession(id) {
  if (!id || id === "latest") return;
  const pins = loadPins().filter((x) => x !== id);
  pins.unshift(id);
  savePins(pins);
  renderPins();
}

async function loadVisual(sessionId) {
  try {
    if (sessionId) visualSessionId = sessionId;
    const sid = visualSessionId || "latest";
    fillSessionSelect(overview?.sessions || []);
    if ($("#visSessionSelect")) $("#visSessionSelect").value = sid;

    if ($("#visMeta")) $("#visMeta").textContent = `Loading ${sid.slice(0, 13)}…`;
    visPack = await getJSON(`/api/visual/${encodeURIComponent(sid)}`);
    if (!visPack?.ok && !visPack?.chambers) {
      const reb = await postJSON("/api/visual/rebuild", {
        session_id: sid === "latest" ? null : sid,
      });
      if (reb.ok) visPack = await getJSON(`/api/visual/${encodeURIComponent(sid)}`);
    }
    // if pack reports a concrete session id, remember it
    if (visPack?.session_id && sid === "latest") {
      visualSessionId = "latest";
    }

    const host = $("#visChambers");
    if (host && !host.dataset.ready) {
      host.innerHTML = CHAMBERS.map(
        ([id, label]) =>
          `<button type="button" data-ch="${id}" class="${id === "connection" ? "on" : ""}">${label}</button>`
      ).join("");
      host.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          host.querySelectorAll("button").forEach((b) => b.classList.remove("on"));
          btn.classList.add("on");
          vis?.setChamber(btn.dataset.ch);
          renderVisTable(visPack, btn.dataset.ch);
          renderVisInspector(null);
        });
      });
      host.dataset.ready = "1";
    }
    const canvas = $("#visCanvas");
    if (canvas && window.MagVisual) {
      if (!vis) {
        vis = new MagVisual(canvas, $("#visCaption"), $("#visMeters"), {
          sanchoEl: $("#visSancho"),
          zoomLabelEl: $("#visZoomLabel"),
          onSelect: (sel) => renderVisInspector(sel),
        });
      }
      vis.setPack(visPack);
      vis.setChamber("connection");
    }
    renderVisModules(visPack);
    renderVisTable(visPack, "connection");
    const leg = $("#visLegend");
    if (leg) {
      leg.textContent =
        "This is a map of one work session Mag recorded — question, tensions, leftovers, next moves. Not a score. Not a verdict. Use Sancho above for ELI5. Use Session dropdown or pins to switch days.";
    }
    const en = visPack?.english || {};
    if ($("#visEnglish")) {
      $("#visEnglish").textContent = [
        en.headline && `Headline: ${en.headline}`,
        en.rope && `Rope: ${en.rope}`,
        en.residual && `Residual: ${en.residual}`,
        en.move && `Move: ${en.move}`,
        en.commitment && `Commitment: ${en.commitment}`,
        en.lane_hint && en.lane_hint,
        visPack?.repro?.file && `File: ${visPack.repro.file}`,
        visPack?.commit && `Commit: ${visPack.commit}`,
      ]
        .filter(Boolean)
        .join("\n\n");
    }
    const shown = visPack?.session_id || sid;
    if ($("#visMeta")) {
      $("#visMeta").textContent = `${String(shown).slice(0, 13)}… · ${visPack?.commit || "—"} · ${
        (visPack?.chambers?.connection?.nodes || []).length
      } nodes · pack=${sid === "latest" ? "latest" : "session"}`;
    }
    renderPins();
  } catch (e) {
    if ($("#visCaption")) $("#visCaption").textContent = String(e.message || e);
  }
}

async function loadMagOs() {
  const chips = $("#magOsChips");
  const prov = $("#magOsProv");
  const ver = $("#magOsVer");
  const phoenix = $("#magOsPhoenix");
  const ship = $("#shipBadge");
  const cardBody = $("#magOsCardBody");
  try {
    const os = await getJSON("/api/v1/mag-os");
    if (ver) ver.textContent = `Mag OS ${os.version || "v2"}`;
    if (ship) {
      const st = os.ship_status || "—";
      ship.textContent = st;
      ship.className = "ship-badge " + st;
    }
    const smoke = os.smoke || {};
    const compose = os.compose || {};
    const run = os.run || {};
    const health = os.health || {};
    if (prov) {
      prov.textContent = [
        `ship=${os.ship_status || "—"}`,
        `health=${health.status || "—"}`,
        `smoke=${smoke.ok ? "PASS" : "FAIL"}`,
        `compose=${compose.ok ? "ok" : "red"}`,
        run.open ? `run=${String(run.seat || "?")}` : "run=—",
        os.pin?.commitment ? `pin=${String(os.pin.commitment).slice(0, 18)}…` : "pin=—",
      ].join(" · ");
    }
    if (chips) {
      const nn = os.non_negotiables || [];
      const flags = [
        { t: "DNA", on: true },
        { t: "Presented", on: true, tip: "Load corpus as presented on thesis asks" },
        { t: "Pack-first", on: true },
        {
          t: "Seat",
          on: !run.open || !!run.seat,
          warn: !!run.open,
          tip: run.open ? `open run · ${run.seat}` : "no open run",
        },
        { t: "Smoke", on: !!smoke.ok, warn: !smoke.ok },
        { t: "Compose", on: !!compose.ok, warn: !compose.ok },
      ];
      chips.innerHTML =
        nn
          .slice(0, 6)
          .map((x) => `<span class="mag-os-chip" title="non-negotiable">${esc(x)}</span>`)
          .join("") +
        flags
          .map((f) => {
            const cls = f.warn ? "mag-os-chip warn" : f.on ? "mag-os-chip on" : "mag-os-chip";
            return `<span class="${cls}" title="${esc(f.tip || f.t)}">${esc(f.t)}</span>`;
          })
          .join("");
    }
    if (phoenix) {
      const ph = os.phoenix || [];
      if (ph.length) {
        phoenix.hidden = false;
        phoenix.textContent = "Phoenix: " + ph.join(" · ");
      } else {
        phoenix.hidden = true;
        phoenix.textContent = "";
      }
    }
    if (cardBody && os.card_md) cardBody.textContent = os.card_md;
    return os;
  } catch (e) {
    if (prov) prov.textContent = "mag-os unavailable — restart lab";
    if (chips) chips.innerHTML = "";
    return null;
  }
}

async function pollHealth() {
  const pill = $("#healthPill");
  const banner = $("#healthBanner");
  try {
    const h = await getJSON("/api/health");
    const st = h.status || "down";
    if (pill) {
      pill.textContent = st.toUpperCase();
      pill.className = "health-pill " + st;
    }
    if (banner) {
      if (st === "up" && !h.recording?.live_stale) {
        banner.hidden = true;
        banner.textContent = "";
      } else {
        banner.hidden = false;
        const miss = (h.missing_while_down || []).join("; ") || "recording lag";
        banner.innerHTML = `<b>Mag ${esc(st)}</b> — ${esc(miss)}. 
          <button type="button" class="btn ghost" id="btnBannerCatchUp">Catch up now</button>
          · CLI: <code>python main.py lab</code> · <code>python main.py guard --restart</code>`;
        $("#btnBannerCatchUp")?.addEventListener("click", () => doCatchUp());
      }
    }
  } catch (e) {
    if (pill) {
      pill.textContent = "DOWN";
      pill.className = "health-pill down";
    }
    if (banner) {
      banner.hidden = false;
      banner.textContent =
        "Cannot reach Mag API — integral process likely killed. Run: python main.py lab";
    }
  }
  await loadMagOs();
}

async function doCatchUp() {
  toast("Catch-up running…");
  try {
    let r;
    try {
      r = await postJSON("/api/v1/catch-up", {});
    } catch {
      r = await postJSON("/api/catch-up", {});
    }
    await pollHealth();
    try {
      await loadBoard();
    } catch {
      /* board optional */
    }
    const ok = r && r.ok !== false;
    toast(ok ? "Catch-up done — board refreshed" : "Catch-up partial — check Status / doctor");
    if ($("#boardNote")) {
      $("#boardNote").textContent = ok
        ? "Catch-up ok — live board refreshed, session amended if needed."
        : "Catch-up partial — see doctor.";
    }
    // refresh current view so user sees change
    await refresh();
  } catch (e) {
    toast("Catch-up failed: " + (e.message || e));
  }
}



function renderStats(o, tapestryStats) {
  const el = $("#stats");
  if (!el) return;
  const sessions = o?.sessions || o || [];
  const sessList = Array.isArray(sessions) ? sessions : [];
  const tip = o?.verkle_tip || {};
  const ingest = o?.ingest || {};
  const ts = tapestryStats || window.__tapestryStats || {};
  el.innerHTML = `
    <div class="stat"><b>${sessList.length}</b><span>workdays</span></div>
    <div class="stat"><b>${ts.n_subsessions ?? "—"}</b><span>live turns</span></div>
    <div class="stat"><b>${ts.n_runs ?? "—"}</b><span>worker runs</span></div>
    <div class="stat"><b>${ts.n_lattice ?? tip.n_leaves ?? "—"}</b><span>proof beads</span></div>
    <div class="stat"><b>${ingest.count ?? "—"}</b><span>ingested</span></div>
  `;
  if ($("#footRoot")) $("#footRoot").textContent = o?.root || tip.root || "";
}

function clipText(s, n = 140) {
  const t = String(s || "")
    .replace(/\s+/g, " ")
    .trim();
  if (!t) return "";
  return t.length > n ? t.slice(0, n - 1).trimEnd() + "…" : t;
}

function shortWhen(s) {
  // 2026-07-28T10:48:00Z → 2026-07-28 10:48
  const raw = String(s || "").trim();
  if (!raw) return "";
  const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/);
  if (m) return `${m[1]} ${m[2]}`;
  return clipText(raw, 16);
}

function stripTracking(url) {
  try {
    const u = new URL(url);
    ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "s", "triedRedirect"].forEach(
      (k) => u.searchParams.delete(k)
    );
    const q = u.searchParams.toString();
    return u.origin + u.pathname + (q ? "?" + q : "");
  } catch {
    return url;
  }
}

function shortUrl(url, max = 42) {
  try {
    const clean = stripTracking(url);
    const u = new URL(clean);
    let path = u.pathname.replace(/\/$/, "") || "/";
    if (path.length > 28) path = path.slice(0, 14) + "…" + path.slice(-10);
    const host = u.host.replace(/^www\./, "");
    const out = host + path;
    return out.length > max ? out.slice(0, max - 1) + "…" : out;
  } catch {
    return clipText(url, max);
  }
}

/** Clean residual blurbs: collapse URLs, drop tag dumps, clip length. */
function cleanBlurb(text, max = 160) {
  let t = String(text || "");
  // URLs → short host/path
  t = t.replace(/https?:\/\/[^\s)\]>'"]+/gi, (u) => shortUrl(u, 36));
  // "Tags: a, b, c" noise
  t = t.replace(/\bTags?:\s*[^.]*\.?/gi, "");
  t = t.replace(/\(\d+\s*operator turns[^)]*\)/gi, "");
  t = t.replace(/\s+/g, " ").trim();
  return clipText(t, max);
}

function cleanBullet(b) {
  let t = String(b || "").trim();
  if (/^https?:\/\//i.test(t)) return shortUrl(t, 40);
  t = t.replace(/https?:\/\/[^\s)\]>'"]+/gi, (u) => shortUrl(u, 32));
  return clipText(t, 90);
}

function renderSessions(sessions) {
  const host = $("#sessionRows");
  if (!host) return;
  if (!sessions.length) {
    host.innerHTML = `<p class="muted">No sessions yet. Run lab / summarize-session.</p>`;
    return;
  }
  host.innerHTML = sessions
    .map((s) => {
      const arts = [
        s.has_residual || s.has_dossier
          ? `<span class="pill on" title="residual filed">RES</span>`
          : "",
        s.has_leaf || s.verkle_filename
          ? `<span class="pill on" title="chain leaf">LEAF</span>`
          : "",
        s.has_pdf ? `<span class="pill" title="PDF export">PDF</span>` : "",
        s.has_visual ? `<span class="pill" title="visual pack">VIS</span>` : "",
      ]
        .filter(Boolean)
        .join("");
      const sel = s.session_id === selectedId ? "selected" : "";
      const bullets = (s.bullets || [])
        .map(cleanBullet)
        .filter(Boolean)
        .filter((b) => !/^https?:\/\//i.test(String(b)) || b.length < 50)
        .slice(0, 3);
      // drop bullets that are just the same URL as blurb
      const bulletHtml = bullets.length
        ? `<ul class="sc-bullets">${bullets.map((b) => `<li title="${esc(b)}">${esc(b)}</li>`).join("")}</ul>`
        : "";
      const day =
        shortWhen(s.end_minute) || shortWhen(s.start_minute) || "—";
      const theme = s.dominant_theme
        ? `<span class="theme-chip">${esc(clipText(s.dominant_theme, 18))}</span>`
        : "";
      const tens =
        s.tension_index != null
          ? `<span class="sc-t" title="tension proxy">T ${Number(s.tension_index).toFixed(2)}</span>`
          : "";
      // Full title in the rail (CSS wraps); only clip extreme length
      const title = clipText(s.title || s.session_id?.slice(0, 12) || "Session", 120);
      const blurb = cleanBlurb(s.blurb || s.one_liner || "", 180) || "No summary yet.";
      const sidShort = String(s.session_id || "").slice(0, 8);
      return `<article class="session-card ${sel}" data-id="${esc(s.session_id)}" title="${esc(
        s.title || ""
      )}">
        <div class="sc-top">
          <h3>${esc(title)}</h3>
          <div class="sc-meta">
            ${theme}
            <span class="sc-when">${esc(day)}</span>
            ${tens}
          </div>
        </div>
        <p class="sc-blurb">${esc(blurb)}</p>
        ${bulletHtml}
        <div class="sc-foot">
          <div class="sc-arts">${arts}<span class="mono muted sc-sid" title="${esc(
            s.session_id || ""
          )}">${esc(sidShort)}</span></div>
          <div class="sc-actions">
            <button type="button" class="btn ghost btn-sm" data-open="${esc(
              s.session_id
            )}">Open</button>
            <button type="button" class="btn ghost btn-sm" data-pin="${esc(
              s.session_id
            )}">Pin</button>
          </div>
        </div>
      </article>`;
    })
    .join("");

  host.querySelectorAll(".session-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      selectDayOnDesk(card.dataset.id, sessions);
    });
  });
  host.querySelectorAll("button[data-open]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openSession(btn.dataset.open);
    });
  });
  host.querySelectorAll("button[data-pin]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      pinSession(btn.dataset.pin);
      toast("Pinned " + String(btn.dataset.pin).slice(0, 8));
    });
  });
  fillSessionSelect(sessions);
  renderPins();
}

function selectDayOnDesk(id, sessions) {
  selectedId = id;
  const list = sessions || overview?.sessions || [];
  const s = list.find((x) => x.session_id === id) || { session_id: id };
  document.querySelectorAll(".session-card").forEach((c) => {
    c.classList.toggle("selected", c.dataset.id === id);
  });
  const cap = $("#tapCaption");
  if (cap) {
    const bullets = (s.bullets || [])
      .map(cleanBullet)
      .filter(Boolean)
      .slice(0, 4);
    const blurb = cleanBlurb(s.blurb || s.one_liner || "", 220) || "No blurb";
    const day = shortWhen(s.end_minute) || shortWhen(s.start_minute) || "";
    const theme = s.dominant_theme ? clipText(s.dominant_theme, 24) : "";
    const tens =
      s.tension_index != null ? Number(s.tension_index).toFixed(2) : null;
    cap.innerHTML = `
      <p class="insp-title">${esc(clipText(s.title || id.slice(0, 12), 80))}</p>
      <p class="insp-meta muted">${esc(
        [theme && `theme ${theme}`, day, tens != null && `T ${tens}`]
          .filter(Boolean)
          .join(" · ") || "Workday bead"
      )}</p>
      <p class="insp-blurb">${esc(blurb)}</p>
      ${
        bullets.length
          ? `<ul class="insp-bullets">${bullets
              .map((b) => `<li title="${esc(b)}">${esc(b)}</li>`)
              .join("")}</ul>`
          : ""
      }
      <p class="mono muted insp-sid" title="${esc(id)}">${esc(String(id).slice(0, 13))}…</p>
    `;
  }
  try {
    tapestryView?.focusSession?.(id);
  } catch {
    /* ignore */
  }
}

async function wireDaysDesk() {
  $("#btnDaysOpenDetail")?.addEventListener("click", () => {
    if (selectedId) openSession(selectedId);
    else setTab("detail");
  });
  $("#btnDaysOpenVisual")?.addEventListener("click", () => {
    if (selectedId) openSessionVisual(selectedId);
    else setTab("visual");
  });
  $("#btnHomeChat")?.addEventListener("click", () => {
    setTab("chat");
    const input = $("#chatInput");
    if (input && !input.value.trim()) {
      input.value = "what was I doing?";
    }
  });
  $("#btnHomeDays")?.addEventListener("click", () => setTab("sessions"));
  $("#btnHomeIdeas")?.addEventListener("click", () => setTab("ideas"));

  $("#btnHomeDiary")?.addEventListener("click", () => setTab("diary"));
  $("#btnHomeStory")?.addEventListener("click", () => setTab("story"));
  $("#btnDiaryReload")?.addEventListener("click", () => loadDiary());
  $("#btnStoryReload")?.addEventListener("click", () => loadStory());
  $("#btnStoryOffice")?.addEventListener("click", () => setTab("home"));
  $("#btnStoryCopy")?.addEventListener("click", () => {
    const text = storyPlainText();
    if (!text) {
      toast("Load story first");
      return;
    }
    navigator.clipboard?.writeText(text).then(
      () => toast("Story copied"),
      () => prompt("Copy story:", text.slice(0, 4000))
    );
  });
  $("#btnDiaryOldest")?.addEventListener("click", () => {
    diaryNewestFirst = false;
    $("#btnDiaryOldest")?.classList.add("on");
    $("#btnDiaryNewest")?.classList.remove("on");
    if (diaryCache) renderDiaryTimeline(diaryCache);
    else loadDiary();
  });
  $("#btnDiaryNewest")?.addEventListener("click", () => {
    diaryNewestFirst = true;
    $("#btnDiaryNewest")?.classList.add("on");
    $("#btnDiaryOldest")?.classList.remove("on");
    if (diaryCache) renderDiaryTimeline(diaryCache);
    else loadDiary();
  });
  $("#btnDiaryCopy")?.addEventListener("click", async () => {
    const text = diaryStoryText();
    if (!text) {
      toast("Load diary first");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      toast("Diary story copied");
    } catch {
      prompt("Copy diary:", text.slice(0, 4000));
    }
  });

  $("#btnHomeRefresh")?.addEventListener("click", () => loadHome());
  $("#btnHomePack")?.addEventListener("click", async () => {
    const t = "python main.py context-pack";
    try {
      await navigator.clipboard.writeText(t);
      if ($("#cliStatusLine")) $("#cliStatusLine").textContent = "Copied: " + t;
    } catch {
      prompt("Copy pack CLI:", t);
    }
  });
  /* ideas buttons wired in bind() — avoid double handlers here */
}

let ideasCache = [];
let ideasFilter = "open"; // default: what still needs work (OS working set)
let ideasSelectedId = null;
let ideasSelectedPack = "";

/** Plain labels for the board — operators and lay readers, not schema jargon. */
function ideaTypeLabel(t) {
  const m = {
    open_loop: "Open loop",
    project: "Project",
    topic: "Topic",
    claim: "Claim",
    evidence: "Reference",
    entity: "Actor",
    avatar: "Proxy",
  };
  return m[t] || t || "Card";
}
function ideaStatusLabel(s) {
  const m = {
    open: "Needs work",
    held: "On the shelf",
    done: "Done",
    parked: "Parked",
  };
  return m[s] || s || "—";
}

function renderIdeasList() {
  const list = $("#ideasList");
  const pack = $("#ideasPack");
  if (!list) return;
  let nodes = ideasCache.slice();
  if (ideasFilter === "open") nodes = nodes.filter((n) => n.status === "open");
  else if (ideasFilter === "held") nodes = nodes.filter((n) => n.status === "held");
  else if (ideasFilter === "project") nodes = nodes.filter((n) => n.type === "project");
  else if (ideasFilter === "open_loop") nodes = nodes.filter((n) => n.type === "open_loop");
  // open first, then project, then rest
  nodes.sort((a, b) => {
    const rank = (n) =>
      n.status === "open" ? 0 : n.type === "project" ? 1 : n.type === "open_loop" ? 2 : 3;
    return rank(a) - rank(b) || String(a.title || "").localeCompare(String(b.title || ""));
  });
  if (!nodes.length) {
    list.innerHTML = `<p class="muted empty-hint ideas-empty">
      ${
        ideasCache.length
          ? `Nothing in this view. Try <b>Everything</b> or <b>On the shelf</b>.`
          : `The board is empty. Click <b>Pull from my notes</b> to import open items from your working notes — that is how Mag learns what you still hold.`
      }
    </p>`;
    return;
  }
  list.innerHTML = nodes
    .map(
      (n) =>
        `<button type="button" class="idea-row ${
          n.id === ideasSelectedId ? "on" : ""
        }" data-id="${esc(n.id)}" title="${esc(ideaTypeLabel(n.type))} · ${esc(
          ideaStatusLabel(n.status)
        )}">
          <span class="idea-tags"><span class="idea-type">${esc(
            ideaTypeLabel(n.type)
          )}</span><span class="idea-status st-${esc(n.status || "")}">${esc(
            ideaStatusLabel(n.status)
          )}</span></span>
          <span class="idea-title">${esc(n.title || n.id)}</span>
        </button>`
    )
    .join("");
  list.querySelectorAll(".idea-row").forEach((btn) => {
    btn.addEventListener("click", () => selectIdea(btn.dataset.id));
  });
  if (ideasSelectedId && !nodes.find((n) => n.id === ideasSelectedId)) {
    if (pack) pack.textContent = "Pick a card on the left…";
  }
}

function setIdeaActionEnabled(on) {
  ["#btnIdeasCopyPack", "#btnIdeasToChat", "#btnIdeaDone", "#btnIdeaShelf", "#btnIdeaReopen"].forEach(
    (sel) => {
      const el = $(sel);
      if (el) el.disabled = !on;
    }
  );
}

async function selectIdea(id) {
  ideasSelectedId = id;
  const pack = $("#ideasPack");
  document.querySelectorAll(".idea-row").forEach((b) => {
    b.classList.toggle("on", b.dataset.id === id);
  });
  if (pack) pack.textContent = "Building brief…";
  setIdeaActionEnabled(false);
  try {
    const p = await getJSON(`${API}/ideas/${encodeURIComponent(id)}/pack`);
    ideasSelectedPack = p.pack || p.error || "—";
    if (pack) pack.textContent = ideasSelectedPack;
    setIdeaActionEnabled(!!p.pack);
  } catch (e) {
    ideasSelectedPack = String(e.message || e);
    if (pack) pack.textContent = ideasSelectedPack;
    setIdeaActionEnabled(false);
  }
}

async function patchIdeaStatus(status) {
  if (!ideasSelectedId) return;
  try {
    const r = await patchJSON(`${API}/ideas/${encodeURIComponent(ideasSelectedId)}`, {
      status,
    });
    const label = ideaStatusLabel(status);
    toast(`Card → ${label}`);
    // refresh list; keep selection
    const keep = ideasSelectedId;
    await loadIdeas();
    if (keep) await selectIdea(keep);
    return r;
  } catch (e) {
    toast("Could not update card: " + (e.message || e));
  }
}

async function loadIdeas() {
  const list = $("#ideasList");
  const stats = $("#ideasStats");
  try {
    let d = await getJSON(`${API}/ideas`);
    ideasCache = d.nodes || [];
    // auto-seed once if graph empty (no alert theater)
    if (!ideasCache.length) {
      try {
        await postJSON(`${API}/ideas/seed`, {});
        d = await getJSON(`${API}/ideas`);
        ideasCache = d.nodes || [];
        if (ideasCache.length) toast(`Board ready · ${ideasCache.length} cards from your notes`);
      } catch (se) {
        console.warn("auto-seed failed", se);
      }
    }
    if (stats) {
      const openN =
        (d.by_status && d.by_status.open) ||
        ideasCache.filter((n) => n.status === "open").length;
      const heldN =
        (d.by_status && d.by_status.held) ||
        ideasCache.filter((n) => n.status === "held").length;
      stats.innerHTML = `
        <div class="stat"><b>${openN}</b><span>need work</span></div>
        <div class="stat"><b>${d.n_nodes ?? ideasCache.length}</b><span>cards on board</span></div>
        <div class="stat"><b>${heldN}</b><span>on the shelf</span></div>
        <div class="stat"><b>${d.n_edges ?? "—"}</b><span>links between cards</span></div>
      `;
    }
    // if Needs work empty but board has cards, fall back so the page is not blank
    if (
      ideasFilter === "open" &&
      ideasCache.length &&
      !ideasCache.some((n) => n.status === "open")
    ) {
      ideasFilter = "all";
    }
    syncIdeasFilterChips();
    renderIdeasList();
    if (!ideasSelectedId || !ideasCache.find((n) => n.id === ideasSelectedId)) {
      const first =
        ideasCache.find((n) => n.status === "open") || ideasCache[0];
      if (first) await selectIdea(first.id);
    }
  } catch (e) {
    if (list) {
      list.innerHTML = `<p class="muted empty-hint">Could not load the board: ${esc(
        e.message || e
      )}. Start Mag with <code>python main.py lab</code>, then hard-refresh.</p>`;
    }
    if (stats) {
      stats.innerHTML = `<div class="stat"><b>—</b><span>board offline</span></div>`;
    }
  }
}

function syncIdeasFilterChips() {
  const host = $("#ideasFilters");
  if (!host) return;
  host.querySelectorAll("[data-filter]").forEach((b) => {
    b.classList.toggle("on", b.dataset.filter === ideasFilter);
  });
}

async function seedIdeas() {
  toast("Pulling open items from your notes…");
  try {
    const r = await postJSON(`${API}/ideas/seed`, {});
    toast(
      r.ok
        ? `Pulled +${r.created_nodes || 0} new · ${r.total_nodes || "?"} cards total`
        : "Could not pull notes: " + (r.error || "unknown")
    );
    await loadIdeas();
  } catch (e) {
    toast("Could not pull notes: " + (e.message || e));
  }
}

let storyCache = null;

function storyPlainText() {
  const s = storyCache;
  if (!s) return "";
  const lines = [];
  lines.push(s.title || "Story");
  lines.push(s.subtitle || "");
  lines.push("");
  if (s.epigraph) {
    lines.push(s.epigraph.quote || "");
    lines.push("— " + (s.epigraph.attribution || ""));
    lines.push("");
  }
  if (s.thesis) {
    lines.push("THESIS");
    lines.push(s.thesis.one_line || "");
    for (const p of s.thesis.paragraphs || []) lines.push("", p);
    lines.push("");
  }
  if (s.poem?.body) {
    lines.push(s.poem.title || "POEM", "", s.poem.body, "");
  }
  for (const j of s.journey || []) {
    lines.push(`PHASE ${j.phase}: ${j.title}`);
    lines.push(j.prose || "");
    for (const b of j.beats || []) lines.push("  · " + b);
    lines.push("");
  }
  if (s.closing) lines.push(s.closing);
  if (s.markdown_extra) lines.push("", "---", s.markdown_extra);
  return lines.join("\n");
}

async function renderStory(s) {
  storyCache = s;
  if ($("#storyTitle")) $("#storyTitle").textContent = s.title || "Story";
  if ($("#storySub")) $("#storySub").textContent = s.subtitle || "";
  const live = s.live || {};
  if ($("#storyLive")) {
    const loops = (live.open_loops || []).slice(0, 3).map((x) => esc(String(x))).join(" · ");
    $("#storyLive").innerHTML = `
      <span class="chip">tip ${esc(live.tip_short || "—")}…</span>
      <span class="chip">leaves ${esc(String(live.n_leaves ?? "—"))}</span>
      <span class="chip">${esc(live.last_leaf || "no leaf")}</span>
      ${loops ? `<span class="muted" style="display:block;margin-top:0.35rem;font-size:0.85rem">Open: ${loops}</span>` : ""}
    `;
  }
  const toc = [
    ["plain", "Start here"],
    ["epigraph", "A long-view quote"],
    ["thesis", "In one breath"],
    ["why", "Why bother"],
    ["where", "Where we are"],
    ["houses", "Two projects"],
    ["inspiration", "Who we learned from"],
    ["journey", "The path so far"],
    ["poem", "Poem"],
    ["artifacts", "Files to open"],
    ["liveit", "What to do tomorrow"],
    ["closing", "Closing"],
  ];
  if ($("#storyToc")) {
    $("#storyToc").innerHTML = toc
      .map(([id, lab]) => `<a href="#story-${id}">${esc(lab)}</a>`)
      .join("");
  }
  const root = $("#storyRoot");
  if (!root) return;

  const epi = s.epigraph || {};
  const why = (s.why || [])
    .map(
      (w) =>
        `<h4>${esc(w.title || "")}</h4><p class="story-prose">${esc(w.body || "")}</p>`
    )
    .join("");
  const where = s.where_we_are || {};
  const list = (arr) =>
    (arr || []).map((x) => `<li>${esc(String(x))}</li>`).join("") || "<li class='muted'>—</li>";
  const insp = (s.inspiration || [])
    .map(
      (i) =>
        `<h4>${esc(i.name || "")}</h4><p class="story-prose">${esc(i.why || "")}</p>`
    )
    .join("");
  const journey = (s.journey || [])
    .map(
      (j) => `
      <article class="story-journey">
        <div class="phase">Phase ${esc(j.phase || "")}</div>
        <h4>${esc(j.title || "")}</h4>
        <p class="story-prose">${esc(j.prose || "")}</p>
        <ul class="story-list">${list(j.beats)}</ul>
      </article>`
    )
    .join("");
  const arts = (s.artifacts || [])
    .map((a) => {
      const miss = a.on_disk === false ? " missing" : "";
      const btn =
        a.href && a.on_disk !== false
          ? `<button type="button" class="btn ghost chip story-open-file" data-path="${esc(
              a.path || ""
            )}">Preview</button>`
          : "";
      return `<div class="story-art${miss}">
        <span class="t">${esc(a.title || "")}</span>
        <span class="n"> · ${esc(a.kind || "")}${a.note ? " · " + esc(a.note) : ""}</span>
        <code>${esc(a.path || "")}</code>
        ${btn}
      </div>`;
    })
    .join("");
  const houses = s.two_houses || {};
  const mag = houses.mag || {};
  const rep = houses.republic || {};
  const poem = s.poem || {};
  const echoes = (poem.echoes || [])
    .map((e) => `<li>${esc(e)}</li>`)
    .join("");
  const thesisPs = (s.thesis?.paragraphs || [])
    .map((p) => `<p class="story-prose">${esc(p)}</p>`)
    .join("");
  const liveit = list(s.how_to_live_it);
  const mdExtra = s.markdown_extra
    ? `<section class="story-section" id="story-md"><h3>Operator long form</h3>
       <pre class="story-poem" style="font-family:var(--mono);font-size:0.82rem">${esc(
         s.markdown_extra
       )}</pre>
       <p class="muted sm">Source: ${esc(s.markdown_path || "memory/story/THESIS_JOURNEY.md")}</p></section>`
    : "";

  const plain = s.plain_guide || {};
  const plainItems = (plain.items || [])
    .map(
      (it) =>
        `<h4>${esc(it.name || "")}</h4><p class="story-prose">${esc(it.body || "")}</p>`
    )
    .join("");

  root.innerHTML = `
    <section class="story-section" id="story-plain">
      <h3>${esc(plain.title || "Start here")}</h3>
      <p class="story-prose muted">Skip the jargon. These three ideas make the rest readable.</p>
      ${plainItems || "<p class='muted'>Reload story if this is empty.</p>"}
    </section>
    <section class="story-section" id="story-epigraph">
      <h3>A long-view quote</h3>
      <div class="story-epigraph">
        <div>
          <blockquote>${esc(epi.quote || "")}</blockquote>
          <p class="attr">${esc(epi.attribution || "")}</p>
          <p class="story-prose muted" style="font-size:0.9rem">${esc(epi.note || "")}</p>
        </div>
        <div>
          ${
            epi.image
              ? `<img src="${esc(epi.image)}" alt="Parker quote — moral universe arc" />`
              : ""
          }
        </div>
      </div>
    </section>
    <section class="story-section" id="story-thesis">
      <h3>In one breath</h3>
      <p class="story-prose lead">${esc(s.thesis?.one_line || "")}</p>
      ${thesisPs}
    </section>
    <section class="story-section" id="story-why">
      <h3>Why bother</h3>
      ${why}
    </section>
    <section class="story-section" id="story-where">
      <h3>Where we are</h3>
      <p class="story-prose lead">${esc(where.phase || "")}</p>
      <h4>What already works</h4><ul class="story-list">${list(where.held)}</ul>
      <h4>Still open</h4><ul class="story-list">${list(where.open)}</ul>
      <h4>What we refuse to pretend</h4><ul class="story-list">${list(where.refuse)}</ul>
    </section>
    <section class="story-section" id="story-houses">
      <h3>Two projects</h3>
      <div class="story-houses">
        <div class="story-art"><span class="t">Mag</span>
          <code>${esc(mag.path || "")}</code>
          <p class="n">${esc(mag.job || "")}</p></div>
        <div class="story-art"><span class="t">Mycelial Republic</span>
          <code>${esc(rep.path || "")}</code>
          <p class="n">${esc(rep.job || "")}</p></div>
      </div>
      <p class="story-prose muted" style="margin-top:0.75rem">${esc(houses.bridge || "")}</p>
    </section>
    <section class="story-section" id="story-inspiration">
      <h3>Who we learned from</h3>
      ${insp}
    </section>
    <section class="story-section" id="story-journey">
      <h3>The path so far</h3>
      ${journey}
    </section>
    <section class="story-section" id="story-poem">
      <h3>${esc(poem.title || "Poem")}</h3>
      <pre class="story-poem">${esc(poem.body || "")}</pre>
      <ul class="story-echoes">${echoes}</ul>
    </section>
    <section class="story-section" id="story-artifacts">
      <h3>Files to open</h3>
      <p class="story-prose muted">Real paths on your machine—not vibes. Preview when the type allows.</p>
      <div class="story-artifacts">${arts}</div>
    </section>
    <section class="story-section" id="story-liveit">
      <h3>What to do tomorrow</h3>
      <ul class="story-list">${liveit}</ul>
    </section>
    <section class="story-section" id="story-closing">
      <h3>Closing</h3>
      <p class="story-closing">${esc(s.closing || "")}</p>
    </section>
    ${mdExtra}
  `;

  root.querySelectorAll(".story-open-file").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const path = btn.getAttribute("data-path");
      if (!path) return;
      toast("Loading " + path + "…");
      try {
        const r = await getJSON(
          "/api/v1/story/file?path=" + encodeURIComponent(path)
        );
        if (!r.ok && r.error) {
          toast(r.error);
          return;
        }
        const text = r.text || "";
        const w = window.open("", "_blank");
        if (w) {
          w.document.write(
            `<pre style="white-space:pre-wrap;font:14px/1.45 ui-monospace,monospace;padding:1rem;background:#0b0d0b;color:#c8d0c8">${esc(
              text
            )}</pre>`
          );
          w.document.title = path;
        } else {
          prompt(path, text.slice(0, 3000));
        }
      } catch (e) {
        toast(String(e.message || e));
      }
    });
  });
}

async function loadStory() {
  try {
    let s;
    try {
      s = await getJSON("/api/v1/story");
    } catch {
      s = await getJSON("/api/story");
    }
    if (s?.error && !s.title) {
      if ($("#storyRoot"))
        $("#storyRoot").innerHTML = `<p class="muted">Story API failed: ${esc(
          s.error
        )}. Restart lab to pick up /api/v1/story.</p>`;
      return;
    }
    renderStory(s);
  } catch (e) {
    if ($("#storyRoot"))
      $("#storyRoot").innerHTML = `<p class="muted">Story load failed: ${esc(
        e.message || e
      )}. Restart Mag lab (dashboard) to load new route.</p>`;
    toast("Story failed — restart lab?");
  }
}

let diaryNewestFirst = false;
let diaryCache = null;

function diaryFromSessions(sessions) {
  /** Client fallback when /api/v1/diary is missing (stale dashboard process). */
  const rows = (sessions || []).slice().sort((a, b) => {
    const ka = String(a.end_minute || a.start_minute || "");
    const kb = String(b.end_minute || b.start_minute || "");
    return ka.localeCompare(kb);
  });
  const byDay = {};
  const order = [];
  const themes = {};
  const entries = rows.map((s) => {
    const end = s.end_minute || s.start_minute || "";
    const day = String(end).slice(0, 10) || "undated";
    const theme = s.dominant_theme || "";
    if (theme) themes[theme] = (themes[theme] || 0) + 1;
    const beats = (s.bullets || [])
      .map((b) => cleanBlurb(String(b), 100))
      .filter(Boolean)
      .slice(0, 3);
    const e = {
      session_id: s.session_id,
      day,
      when: shortWhen(end),
      title: cleanBlurb(s.title || "Untitled", 90) || "Untitled",
      blurb: cleanBlurb(s.blurb || s.one_liner || "", 260) || "No summary filed.",
      beats,
      theme: theme || null,
      tension: s.tension_index,
      duration_minutes: s.duration_minutes,
    };
    if (!byDay[day]) {
      byDay[day] = [];
      order.push(day);
    }
    byDay[day].push(e);
    return e;
  });
  order.sort();
  const chapters = order.map((d) => ({
    day: d,
    n: byDay[d].length,
    entries: byDay[d],
    headline: byDay[d][0]?.title,
  }));
  const first = entries[0];
  const last = entries[entries.length - 1];
  const arc =
    first && last && entries.length > 1
      ? `From ${first.day} (“${first.title}”) to ${last.day} (“${last.title}”) — ${entries.length} filed days.`
      : last
        ? `One filed day: ${last.day} — “${last.title}”.`
        : "No days filed yet.";
  return {
    ok: true,
    schema: "mag_diary.client_fallback",
    arc,
    n_days: order.length,
    n_entries: entries.length,
    first_day: first?.day,
    last_day: last?.day,
    themes: Object.entries(themes)
      .map(([id, n]) => ({ id, n }))
      .sort((a, b) => b.n - a.n)
      .slice(0, 8),
    chapters,
    entries,
    _fallback: true,
  };
}

async function fetchDiaryPayload() {
  try {
    return await getJSON("/api/v1/diary");
  } catch (e1) {
    try {
      return await getJSON("/api/diary");
    } catch (e2) {
      // Stale server without diary route — build from overview sessions
      let sessions = overview?.sessions;
      if (!sessions?.length) {
        try {
          const o = await getJSON("/api/v1/overview");
          overview = o;
          sessions = o.sessions || [];
        } catch {
          try {
            const o = await getJSON("/api/overview");
            overview = o;
            sessions = o.sessions || [];
          } catch {
            sessions = [];
          }
        }
      }
      if (sessions?.length) {
        toast("Diary API missing — using session list (restart dashboard for full route)", 4500);
        return diaryFromSessions(sessions);
      }
      throw e1;
    }
  }
}

function renderDiaryProject(proj) {
  if (!proj || typeof proj !== "object") {
    if ($("#diaryProjectOne")) {
      $("#diaryProjectOne").textContent =
        "Project prologue unavailable — restart dashboard for diary v2, or use session timeline below.";
    }
    return;
  }
  if ($("#diaryProjectOne")) {
    $("#diaryProjectOne").textContent =
      (proj.title ? proj.title + " — " : "") + (proj.one_line || "");
  }
  if ($("#diaryProjectSpine")) {
    $("#diaryProjectSpine").textContent = proj.spine || "";
  }
  if ($("#diaryProjectDual")) {
    $("#diaryProjectDual").textContent = proj.dual_house || "";
  }
  const fillList = (id, items) => {
    const el = $(id);
    if (!el) return;
    const arr = items || [];
    el.innerHTML = arr.length
      ? arr.map((x) => `<li>${esc(x)}</li>`).join("")
      : `<li class="muted">—</li>`;
  };
  fillList("#diaryOrigins", proj.origins);
  fillList("#diaryGoals", proj.goals);
  fillList("#diaryOpen", proj.open);
  const docs = proj.supporting_docs || [];
  if ($("#diaryDocsSummary")) {
    $("#diaryDocsSummary").textContent = `Supporting documents (${docs.length})`;
  }
  if ($("#diaryDocs")) {
    $("#diaryDocs").innerHTML = docs.length
      ? docs
          .map((doc) => {
            const house = doc.house ? ` · ${doc.house}` : "";
            const ex = doc.excerpt
              ? `<div class="muted diary-doc-ex">${esc(doc.excerpt)}</div>`
              : "";
            return `<li>
              <code>${esc(doc.path)}</code>
              <span class="muted">${esc(doc.role || "")}${esc(house)}</span>
              ${ex}
            </li>`;
          })
          .join("")
      : `<li class="muted">No supporting docs found on disk</li>`;
  }
}

async function loadDiary() {
  const arc = $("#diaryArc");
  const stats = $("#diaryStats");
  const themes = $("#diaryThemes");
  const tl = $("#diaryTimeline");
  try {
    const d = await fetchDiaryPayload();
    diaryCache = d;
    if (arc) {
      arc.textContent =
        (d.arc || "—") +
        (d._fallback ? "  ·  (session fallback — restart Mag dashboard for /api/v1/diary)" : "");
    }
    if (stats) {
      const nDocs = d.project?.n_docs ?? d.project?.supporting_docs?.length;
      stats.innerHTML = `
        <div class="rs-chip"><b>${d.n_days ?? "—"}</b><span>calendar days</span></div>
        <div class="rs-chip"><b>${d.n_entries ?? "—"}</b><span>sessions</span></div>
        <div class="rs-chip"><b>${esc(d.first_day || "—")}</b><span>from</span></div>
        <div class="rs-chip"><b>${esc(d.last_day || "—")}</b><span>to</span></div>
        <div class="rs-chip"><b>${nDocs ?? "—"}</b><span>law docs</span></div>
      `;
    }
    if (themes) {
      const th = d.themes || [];
      themes.innerHTML = th.length
        ? th
            .map(
              (t) =>
                `<span class="theme-chip diary-theme">${esc(t.id)} · ${esc(
                  String(t.n)
                )}</span>`
            )
            .join("")
        : "";
    }
    renderDiaryProject(d.project);
    renderDiaryTimeline(d);
    $("#btnDiaryOldest")?.classList.toggle("on", !diaryNewestFirst);
    $("#btnDiaryNewest")?.classList.toggle("on", diaryNewestFirst);
  } catch (e) {
    if (arc) arc.textContent = "Diary failed: " + (e.message || e);
    if (tl) {
      tl.innerHTML = `<p class="muted empty-hint">${esc(e.message || e)}
        <br/><br/>Restart the dashboard so new routes load:
        <code>python main.py dashboard --host 127.0.0.1 --port 8765</code>
        then hard-refresh (Ctrl+Shift+R).</p>`;
    }
  }
}

function renderDiaryTimeline(d) {
  const tl = $("#diaryTimeline");
  if (!tl) return;
  let chapters = (d.chapters || []).slice();
  if (diaryNewestFirst) chapters = chapters.slice().reverse();
  if (!chapters.length) {
    tl.innerHTML = `<p class="muted empty-hint">No filed days yet. Work, then let Mag file a bead — the diary grows from residual DNA.</p>`;
    return;
  }
  tl.innerHTML = chapters
    .map((ch) => {
      const entries = ch.entries || [];
      const body = entries
        .map((e) => {
          const beats = (e.beats || [])
            .slice(0, 3)
            .map((b) => `<li>${esc(b)}</li>`)
            .join("");
          const meta = [
            e.when,
            e.theme && `theme ${e.theme}`,
            e.tension != null && `T ${Number(e.tension).toFixed(2)}`,
            e.duration_minutes != null && `${e.duration_minutes} min`,
          ]
            .filter(Boolean)
            .join(" · ");
          return `<article class="diary-entry" data-id="${esc(e.session_id || "")}">
            <h3 class="diary-title">${esc(e.title || "Untitled")}</h3>
            <p class="diary-meta muted">${esc(meta)}</p>
            <p class="diary-blurb">${esc(e.blurb || "")}</p>
            ${beats ? `<ul class="diary-beats">${beats}</ul>` : ""}
            <div class="row diary-actions">
              <button type="button" class="btn ghost btn-sm" data-diary-open="${esc(
                e.session_id || ""
              )}">Open day</button>
              <button type="button" class="btn ghost btn-sm" data-diary-days="${esc(
                e.session_id || ""
              )}">Show in Days</button>
            </div>
          </article>`;
        })
        .join("");
      return `<section class="diary-chapter">
        <header class="diary-day-head">
          <span class="diary-day">${esc(ch.day)}</span>
          <span class="muted">${esc(String(ch.n || entries.length))} session${
            (ch.n || entries.length) === 1 ? "" : "s"
          }</span>
        </header>
        ${body}
      </section>`;
    })
    .join("");

  tl.querySelectorAll("[data-diary-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-diary-open");
      if (id) openSession(id);
    });
  });
  tl.querySelectorAll("[data-diary-days]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-diary-days");
      setTab("sessions");
      if (id) {
        selectedId = id;
        setTimeout(() => selectDayOnDesk(id), 200);
      }
    });
  });
}

function diaryStoryText() {
  if (!diaryCache) return "";
  const d = diaryCache;
  const proj = d.project || {};
  const lines = [
    "# Project story & diary",
    "",
    d.arc || "",
    "",
    "## Project",
    proj.one_line || "",
    "",
    "Spine: " + (proj.spine || ""),
    "",
    proj.dual_house || "",
    "",
  ];
  if (proj.origins?.length) {
    lines.push("### Origins", "");
    for (const o of proj.origins) lines.push("- " + o);
    lines.push("");
  }
  if (proj.goals?.length) {
    lines.push("### Goals", "");
    for (const g of proj.goals) lines.push("- " + g);
    lines.push("");
  }
  if (proj.open?.length) {
    lines.push("### Open", "");
    for (const g of proj.open) lines.push("- " + g);
    lines.push("");
  }
  if (proj.supporting_docs?.length) {
    lines.push("### Supporting documents", "");
    for (const doc of proj.supporting_docs) {
      lines.push(`- ${doc.path} — ${doc.role || ""}`);
    }
    lines.push("");
  }
  lines.push("## Day by day", "");
  let chapters = (d.chapters || []).slice();
  if (diaryNewestFirst) chapters = chapters.reverse();
  for (const ch of chapters) {
    lines.push(`## ${ch.day}`);
    for (const e of ch.entries || []) {
      lines.push(`### ${e.title}`);
      lines.push(e.blurb || "");
      for (const b of e.beats || []) lines.push(`- ${b}`);
      lines.push("");
    }
  }
  return lines.join("\n");
}

function pctBar(pct, ok) {
  if (pct == null || Number.isNaN(pct)) {
    return `<span class="pct-bar unlimited" title="Unlimited / local"><i style="width:0"></i></span><span class="pct-lab">∞</span>`;
  }
  const p = Math.max(0, Math.min(100, Number(pct)));
  const tone = p >= 80 ? "hot" : p >= 40 ? "warm" : "cool";
  const dead = ok === false ? " dead" : "";
  return `<span class="pct-bar ${tone}${dead}" title="${p}% of Mag budget"><i style="width:${p}%"></i></span><span class="pct-lab">${p}%</span>`;
}

function seatSourceLabel(src) {
  const m = {
    grok: "Grok",
    cursor: "Cursor",
    deepseek: "DeepSeek",
    agent: "Agent",
    orchestrator: "Orch",
  };
  return m[src] || src || "?";
}

function renderSeatRow(s, inbound) {
  const liveCls = s.live || (s.age && s.age !== "never seen") ? "live" : "dark";
  const age = s.age || (s.pct_used != null ? `${s.pct_used}% budget` : "—");
  const sub = inbound
    ? esc(s.layman || s.label || s.id)
    : esc(s.model || s.key_env || "");
  const title = [
    s.layman,
    s.source_path && `proof: ${s.source_path}`,
    s.mag_does_not_know && `Mag does NOT know: ${s.mag_does_not_know}`,
    s.preview && `preview: ${s.preview}`,
  ]
    .filter(Boolean)
    .join("\n");
  return `<button type="button" class="conn-row ${liveCls}" title="${esc(title)}">
    <span class="conn-dot"></span>
    <span class="conn-name">${esc(s.label || s.id)}</span>
    <span class="conn-model muted">${sub.slice(0, 72)}</span>
    <span class="conn-budget">${esc(String(age))}</span>
  </button>`;
}

async function loadSeatsPanel() {
  const inHost = $("#seatsInbound");
  const outHost = $("#seatsOutbound");
  const pills = $("#statusPills");
  const workersList = $("#workersList");
  const workersLayman = $("#workersLayman");
  if (!inHost && !outHost) return null;
  try {
    const reg = await getJSON("/api/v1/seats");
    if (inHost) {
      inHost.innerHTML = (reg.inbound || [])
        .map((s) => renderSeatRow(s, true))
        .join("") || `<p class="muted">No inbound seats detected yet</p>`;
    }
    if (outHost) {
      outHost.innerHTML = (reg.outbound || [])
        .slice(0, 12)
        .map((s) => renderSeatRow(s, false))
        .join("") || `<p class="muted">No providers in configs/providers.yaml</p>`;
    }
    if (pills) {
      const c = reg.counts || {};
      pills.innerHTML = [
        `<span class="health-pill ${c.outbound_live ? "ok" : "warn"}">${c.outbound_live || 0} API live</span>`,
        `<span class="health-pill ${c.workers_running ? "warn" : ""}">${c.workers_running || 0} workers</span>`,
        `<span class="health-pill">${c.inbound_active || 0} seats active</span>`,
      ].join("");
    }
    const w = reg.workers || {};
    if (workersLayman) workersLayman.textContent = w.layman || reg.headline || "";
    if (workersList) {
      const rows = [...(w.running || []), ...(w.recent || [])].slice(0, 10);
      workersList.innerHTML = rows.length
        ? rows
            .map((t) => {
              const st = t.status || "?";
              const tone = st === "running" ? "warn" : st === "done" ? "ok" : "muted";
              return `<li class="${tone}"><strong>${esc(st)}</strong> · ${esc(
                (t.goal || t.task_id || "").slice(0, 70)
              )}</li>`;
            })
            .join("")
        : `<li class="muted">No workers in last 48h — spawn from Workers tab</li>`;
      if (w.archived_hidden > 0) {
        workersList.innerHTML += `<li class="muted">${w.archived_hidden} older soak tests hidden</li>`;
      }
    }
    const coordLive = $("#coordinationLive");
    if (coordLive) {
      try {
        const coord = await getJSON("/api/v1/coordination?limit=12");
        const running = coord.running || [];
        const recent = coord.recent || [];
        const lines = [
          ...running.map(
            (r) =>
              `<li class="warn"><strong>${esc(r.seat || "?")}</strong> · ${esc(
                r.depth || ""
              )} · ${esc((r.goal || "").slice(0, 55))}</li>`
          ),
          ...recent.slice(0, 8).map(
            (r) =>
              `<li class="muted"><strong>${esc(r.seat || "?")}</strong> · ${esc(
                r.status || ""
              )} · ${esc((r.goal || "").slice(0, 50))}</li>`
          ),
        ];
        coordLive.innerHTML = lines.length
          ? lines.join("")
          : `<li class="muted">No cross-seat activity yet — use coordinate CLI</li>`;
      } catch {
        coordLive.innerHTML = `<li class="muted">Coordination feed unavailable</li>`;
      }
    }
    return reg;
  } catch (e) {
    if (inHost) inHost.innerHTML = `<p class="muted">Seats unavailable: ${esc(e.message || e)}</p>`;
    return null;
  }
}

let chronicleTimer = null;
async function loadChronicle() {
  const meta = $("#chronicle-meta");
  const content = $("#chronicle-content");
  const events = $("#chronicleEvents");
  const sources = $("#chronicleSources");
  const honesty = $("#chronicleHonesty");
  try {
    const d = await getJSON("/api/v1/chronicle");
    if (meta) {
      meta.textContent = d.updated
        ? `Updated ${d.updated}${d.bonds_updated ? " · bonds " + d.bonds_updated : ""}`
        : d.workers_layman || "Pulse";
    }
    if (content) content.textContent = d.content || "(empty)";
    if (honesty && d.honesty) {
      honesty.textContent = d.honesty.layman || honesty.textContent;
    }
    if (events) {
      events.innerHTML = (d.events || [])
        .map((ev) => {
          const lay = ev.layman || ev.preview || ev.technical || "?";
          const proof = ev.proof ? `<span class="muted sm"> · ${esc(ev.proof)}</span>` : "";
          return `<li><strong>${esc(lay)}</strong>${proof}</li>`;
        })
        .join("") || `<li class="muted">No events — file a session or run synthesis_agent</li>`;
    }
    if (sources && d.sources) {
      sources.textContent = "Sources: " + d.sources.join(" · ");
    }
  } catch (e) {
    if (meta) meta.textContent = "Pulse fetch failed — is dashboard + synthesis_agent running?";
    if (events) events.innerHTML = `<li class="muted">${esc(e.message || e)}</li>`;
  }
}

function startChroniclePoll() {
  if (chronicleTimer) return;
  loadChronicle();
  chronicleTimer = setInterval(loadChronicle, 10000);
}

async function loadSeatFeed() {
  const list = $("#seatFeedList");
  const sum = $("#seatFeedSummary");
  if (!list) return;
  try {
    const j = await getJSON("/api/v1/seat-feed?n=35");
    const entries = j.entries || [];
    const counts = j.counts || {};
    if (sum) {
      const parts = Object.entries(counts).map(([k, v]) => `${seatSourceLabel(k)}:${v}`);
      sum.textContent = parts.length ? parts.join(" · ") : "no events yet";
    }
    list.innerHTML = entries.length
      ? entries
          .map((e) => {
            const src = seatSourceLabel(e.source);
            const when = shortWhen(e.ts) || clipText(String(e.ts || ""), 16);
            const prev = esc(clipText(e.preview || e.event || "", 160));
            const ev = e.event ? `<span class="muted">${esc(String(e.event))}</span>` : "";
            return `<li class="seat-feed-item" data-source="${esc(e.source || "")}">
              <span class="seat-feed-src">${esc(src)}</span>
              <span class="seat-feed-when muted">${esc(when)}</span>
              ${ev}
              <span class="seat-feed-preview">${prev}</span>
            </li>`;
          })
          .join("")
      : `<li class="muted">No seat events yet — use Grok, Cursor hooks, or DeepSeek agent.</li>`;
  } catch (e) {
    if (sum) sum.textContent = "feed error";
    list.innerHTML = `<li class="muted">${esc(e.message || e)}</li>`;
  }
}

async function syncDrainerToggle(router) {
  const toggle = $("#drainerToggle");
  const govToggle = $("#govDrainerToggle");
  const hint = $("#drainerHint");
  const dr = router?.drainer || {};
  if (toggle) {
    toggle.disabled = !!dr.env_locked;
    toggle.checked = !!dr.enabled;
  }
  if (govToggle) {
    govToggle.disabled = !!dr.env_locked;
    govToggle.checked = !!dr.enabled;
  }
  if (hint) {
    hint.textContent = dr.hint || (dr.enabled ? "Drainer ON" : "Drainer OFF");
  }
}

async function onDrainerToggleChange() {
  const toggle = $("#drainerToggle");
  if (!toggle || toggle.disabled) return;
  try {
    await postJSON("/api/v1/drainer", { enabled: toggle.checked });
    toast(toggle.checked ? "Drainer enabled — supervisor picks up ~5s" : "Drainer disabled");
    await loadStatus();
  } catch (e) {
    toast("Drainer toggle failed: " + (e.message || e));
  }
}

async function onAutopilotOnce() {
  const hint = $("#autopilotHint");
  const btn = $("#btnAutopilotOnce");
  if (btn) btn.disabled = true;
  if (hint) hint.textContent = "Running autopilot…";
  try {
    const j = await postJSON("/api/v1/autopilot", {
      queue_improve: true,
      governor: true,
      drain: false,
      max_queue: 2,
    });
    const seed = j.seed_mirror || {};
    const queued = (j.queued || []).length;
    if (hint) {
      hint.textContent = seed.blocked
        ? `seed-mirror blocked — ${seed.hint || "no archive"}`
        : `ok · queued ${queued} · ${(j.steps || []).length} steps`;
    }
    toast("Autopilot done — see logs/autopilot_latest.json");
  } catch (e) {
    if (hint) hint.textContent = "Autopilot failed";
    toast("Autopilot failed: " + (e.message || e));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadPowerPanel() {
  const head = $("#powerHeadline");
  const pills = $("#powerPills");
  const svc = $("#powerServices");
  const hint = $("#powerHint");
  try {
    const p = await getJSON("/api/v1/power");
    const hl = p.headline || (p.stack_up ? "UP" : "DOWN");
    const tone =
      hl === "UP" ? "ok" : hl === "STOPPED" ? "muted" : hl === "ZOMBIES" ? "warn" : "warn";
    if (head) {
      head.textContent = `Stack ${hl}${p.power_off ? " (kill switch engaged)" : ""}`;
      head.className = `muted sm power-head-${tone}`;
    }
    if (pills) {
      pills.innerHTML = [
        `<span class="pill ${tone}">${esc(hl)}</span>`,
        p.power_off ? `<span class="pill warn">OFF flag</span>` : "",
        p.supervisor?.running ? `<span class="pill ok">supervisor</span>` : `<span class="pill">supervisor off</span>`,
        (p.fleet?.running || 0) > 0
          ? `<span class="pill warn">${p.fleet.running} worker(s)</span>`
          : "",
        (p.seat_guards_running || 0) > 0
          ? `<span class="pill warn">${p.seat_guards_running} seat-guard</span>`
          : "",
        (p.registered_seats || 0) > 0
          ? `<span class="pill ok">${p.registered_seats} registered seat(s)</span>`
          : "",
      ]
        .filter(Boolean)
        .join("");
    }
    if (svc) {
      const sv = p.services || {};
      kvRows(svc, [
        ["Backend :8000", sv.backend ? "UP" : "down", sv.backend ? "ok" : "warn"],
        ["Dashboard :8765", sv.dashboard ? "UP" : "down", sv.dashboard ? "ok" : "warn"],
        ["Mirror :8743", sv.mirror ? "UP" : "down", sv.mirror ? "ok" : ""],
        ["Mag processes", String(p.mag_processes ?? "—"), (p.mag_processes || 0) > 3 ? "warn" : ""],
        ["Fleet running", String(p.fleet?.running ?? 0), (p.fleet?.running || 0) > 0 ? "warn" : ""],
      ]);
    }
    if (hint) {
      hint.textContent =
        p.actions?.stop && p.actions?.start
          ? `CLI: ${p.actions.stop} · ${p.actions.start}`
          : "mag_kill.cmd to exit · mag_on.cmd to boot";
    }
  } catch (e) {
    if (head) head.textContent = "Power status unavailable (stack may be down)";
    if (hint) hint.textContent = String(e.message || e);
  }
}

async function onImproveCycle() {
  const btn = $("#btnImproveCycle");
  if (btn) btn.disabled = true;
  toast("Improve cycle running…");
  try {
    const res = await postJSON("/api/v1/improve/cycle", { source: "dashboard", drain: true, max_improve: 2 });
    toast(res.ok ? "Improve cycle OK — check Body + Workers" : "Improve cycle incomplete");
    await loadPowerPanel();
    await loadStatus();
  } catch (e) {
    toast("Improve cycle failed: " + (e.message || e));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function onPowerStop() {
  if (!confirm("Stop entire Mag stack? Dashboard will go down.")) return;
  const btn = $("#btnPowerStop");
  if (btn) btn.disabled = true;
  toast("Kill switch — shutting down…");
  try {
    await postJSON("/api/v1/power/stop", {});
    toast("Stack stopping — window may lose connection");
  } catch (e) {
    toast("Stop sent (connection may drop): " + (e.message || e));
  }
}

async function onPowerStart() {
  const btn = $("#btnPowerStart");
  if (btn) btn.disabled = true;
  toast("Turning Mag on…");
  try {
    const res = await postJSON("/api/v1/power/start", { browser: false });
    toast(res.ok ? "Stack up — reloading status" : "Start incomplete — check mag_on.cmd");
    await loadPowerPanel();
    await loadStatus();
  } catch (e) {
    toast("Start failed: " + (e.message || e));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadStatus() {
  const body = $("#statusBody");
  const spend = $("#statusSpend");
  const seats = $("#statusSeats");
  const why = $("#statusWhy");
  const actions = $("#statusActions");
  const head = $("#statusHeadline");
  const honesty = $("#statusHonesty");
  const connHost = $("#routerConnections");
  const pressureEl = $("#statusPressure");
  const summary = $("#routerSummary");
  const ingestList = $("#ingestUrlList");
  const ingestSum = $("#ingestSummary");
  const officeHead = $("#statusOfficeHeadline");

  try {
    await loadPowerPanel();
    const [router, h, seatsReg] = await Promise.all([
      getJSON("/api/v1/router-status").catch((e) => ({
        ok: false,
        error: String(e.message || e),
      })),
      getJSON("/api/v1/home").catch(() => ({})),
      loadSeatsPanel(),
    ]);

    if (head) {
      head.textContent = h.headline || seatsReg?.headline || router.headline || "Body status";
    }
    if (officeHead) {
      officeHead.textContent = seatsReg?.headline || router.headline || "";
    }
    if (honesty) {
      const hnote = seatsReg?.honesty?.layman || router.honesty;
      honesty.textContent =
        hnote ||
        "Budgets are Mag-tracked limits — not Grok TUI / ChatGPT subscription percentages.";
    }

    const conns = router.connections || [];
    const live = conns.filter((c) => c.live);
    const remoteLive = live.filter((c) => !c.local);
    const ingest = router.ingest || {};
    const mem = router.memory || {};
    const usage = router.usage_today || {};

    if (summary) {
      summary.innerHTML = `
        <div class="rs-chip"><b>${live.length}</b><span>live routes</span></div>
        <div class="rs-chip"><b>${remoteLive.length}</b><span>remote agents</span></div>
        <div class="rs-chip"><b>${ingest.count ?? "—"}</b><span>ingested</span></div>
        <div class="rs-chip"><b>${mem.idea_nodes ?? "—"}</b><span>idea nodes</span></div>
        <div class="rs-chip"><b>${mem.sessions_filed ?? "—"}</b><span>days filed</span></div>
      `;
    }

    if (connHost) {
      if (!conns.length) {
        connHost.innerHTML = `<p class="muted">${esc(
          router.connections_error || "No provider config"
        )}</p>`;
      } else {
        connHost.innerHTML = conns
          .map((c) => {
            const liveCls = c.live ? "live" : "dark";
            const budget =
              c.unlimited || c.local
                ? "local / unlimited"
                : c.max_calls != null
                  ? `${c.used_calls}/${c.max_calls} calls`
                  : c.max_tokens != null
                    ? `${c.used_tokens}/${c.max_tokens} tok`
                    : "—";
            return `<button type="button" class="conn-row ${liveCls}" data-conn="${esc(
              c.id
            )}" title="${esc(c.note || c.key_env || "")}">
              <span class="conn-dot" aria-hidden="true"></span>
              <span class="conn-name">${esc(c.name || c.id)}</span>
              <span class="conn-model muted">${esc(c.model || "")}</span>
              <span class="conn-budget">${esc(budget)}</span>
              ${pctBar(c.pct_used, c.budget_ok)}
            </button>`;
          })
          .join("");
        connHost.querySelectorAll(".conn-row").forEach((btn) => {
          btn.addEventListener("click", () => {
            const id = btn.dataset.conn;
            const c = conns.find((x) => x.id === id);
            if (!c) return;
            const detail = [
              c.live ? "LIVE (key present)" : "dark (no key in env)",
              c.local ? "local" : "remote",
              c.model && `model ${c.model}`,
              c.key_env && `env ${c.key_env}`,
              c.unlimited
                ? "unlimited Mag budget"
                : `Mag budget ${c.pct_used ?? 0}% · reset ~${c.reset_in_hours ?? "?"}h`,
              c.note,
            ]
              .filter(Boolean)
              .join(" · ");
            toast(detail, 5000);
          });
        });
      }
    }

    const byLane = usage.by_lane || {};
    kvRows(spend, [
      ["L0 local calls today", byLane.L0 ?? 0],
      ["L1 remote calls today", byLane.L1 ?? 0],
      [
        "Grok escalations (Mag)",
        `${usage.grok_escalations ?? 0} / ${usage.grok_escalation_budget ?? "—"}`,
      ],
      [
        "Grok TUI plan %",
        "not visible to Mag — check x.com / grok UI",
      ],
      ["Prefer order", (router.prefer_order || []).slice(0, 5).join(" → ") || "—"],
    ]);
    if (pressureEl) {
      const hot = router.pressure || [];
      pressureEl.innerHTML = hot.length
        ? hot.map((p) => `<li class="warn">${esc(p)}</li>`).join("")
        : `<li class="muted">No Mag-budget pressure above 25%. If Grok UI shows ~30%, that is your TUI subscription — wire usage into Mag or treat it as separate.</li>`;
    }

    kvRows(seats, [
      ["Ingest items", ingest.count ?? "—"],
      ["With URLs", ingest.all_urls_n ?? "—"],
      ["Kinds", Object.entries(ingest.kinds || {}).map(([k, v]) => `${k}:${v}`).join(" · ") || "—"],
      ["Idea nodes", mem.idea_nodes ?? "—"],
      ["Ideas open", mem.idea_open ?? "—"],
      ["Days filed", mem.sessions_filed ?? "—"],
    ]);
        loadChains();
const recent = ingest.recent_urls || [];
    if (ingestSum) ingestSum.textContent = `Recent URLs (${recent.length} shown · ${ingest.all_urls_n ?? 0} total)`;
    if (ingestList) {
      ingestList.innerHTML = recent.length
        ? recent
            .map((u) => {
              const label = shortUrl(u.url || u.title || "", 48);
              const href = u.url || "#";
              return `<li><a href="${esc(href)}" target="_blank" rel="noopener">${esc(
                label
              )}</a> <span class="muted">${esc(u.kind || "")}</span></li>`;
            })
            .join("")
        : `<li class="muted">No URLs in ingest catalog yet</li>`;
    }

    // office health collapsed
    const health = h.health || {};
    const ship = h.ship || {};
    const compose = h.compose || {};
    kvRows(body, [
      ["Ship", ship.status || "—", ship.status === "OK" ? "ok" : "warn"],
      ["Ollama", health.ollama ? "ON" : "OFF"],
      ["Smoke", h.multi_smoke_ok ? "PASS" : "needs run"],
      ["Compose", compose.ok ? "ok" : compose.error || "check"],
      ["Tip", `${h.tip?.root_short || "—"} (${h.tip?.n_leaves ?? "?"} leaves)`],
      ["Live stale", health.live_stale ? "yes — Catch up" : "no"],
    ]);
    if (why) {
      const reasons = ship.why || [];
      why.innerHTML = reasons.length
        ? reasons.map((r) => `<li>${esc(r)}</li>`).join("")
        : `<li class="muted">No ship caveats</li>`;
    }
    if (actions) {
      actions.innerHTML = health.live_stale
        ? `<button type="button" class="btn primary" id="btnStatusDoCatch">Run catch-up</button>`
        : "";
      $("#btnStatusDoCatch")?.addEventListener("click", () => doCatchUp());
    }

    const desks = $("#statusDesks");
    const mirror = router.mirror || {};
    if (desks) {
      kvRows(desks, [
        ["Mag home", "http://127.0.0.1:8765", "ok"],
        ["Sovereign Shell", "http://127.0.0.1:8765/shell", "ok"],
        [
          "Mirror desk",
          mirror.up ? "UP :8743" : "down — restart Start Everything",
          mirror.up ? "ok" : "warn",
        ],
        ["Mirror Mag tab", mirror.mag_tab || "http://127.0.0.1:8743/", ""],
      ]);
    }
    await syncDrainerToggle(router);
    await loadSeatFeed();
    await loadGovernance();

    // --- Ops overview (supervisor + fleet) ---
    const opsSup = $("#opsSupervisor");
    const opsFleet = $("#opsFleet");
    const opsList = $("#opsFleetList");
    const opsSum = $("#opsFleetSummary");
    if (opsSup) {
      const sup = h.supervisor || {};
      const supRunning = sup.running ? "RUNNING" : "stopped";
      const pids = sup.pids || {};
      const wanted = sup.wanted || {};
      const liveRoles = Object.keys(pids).filter((r) => wanted[r]);
      kvRows(opsSup, [
        ["Supervisor", supRunning, sup.running ? "ok" : "warn"],
        ["Live roles", liveRoles.length ? liveRoles.join(", ") : "—"],
        ["Started", sup.started || "—"],
        ["Check s", sup.check_s ?? "—"],
        ["PIDs", Object.keys(pids).length ? Object.entries(pids).map(([r, p]) => `${r}:${p}`).join(" ") : "—"],
      ]);
    }
    if (opsFleet) {
      const f = h.fleet || {};
      const q = h.queue || {};
      const qc = q.counts || {};
      const qRows = [
        ["Fleet total", f.total ?? "—"],
        ["Running", f.running ?? "—", (f.running || 0) > 0 ? "ok" : ""],
        ["Done", f.done ?? "—", "ok"],
        ["Failed", f.failed ?? "—", (f.failed || 0) > 0 ? "warn" : ""],
        ["Killed", f.killed ?? "—", (f.killed || 0) > 0 ? "warn" : ""],
      ];
      if (q && q.total != null) {
        qRows.push(["Queue total", q.total]);
        qRows.push(["Queue queued", qc.queued ?? 0, (qc.queued || 0) > 0 ? "warn" : ""]);
        qRows.push(["Queue running", qc.running ?? 0, (qc.running || 0) > 0 ? "ok" : ""]);
        if (q.running_task_id) qRows.push(["Queue task", q.running_task_id]);
      }
      kvRows(opsFleet, qRows);
      if (opsList && opsSum) {
        const recent = f.recent || [];
        opsSum.textContent = `Recent tasks (${recent.length})`;
        opsList.innerHTML = recent.length
          ? recent.map((t) => {
              const st = t.status || "?";
              const tone = st === "done" ? "ok" : st === "running" ? "warn" : "muted";
              return `<li class="${tone}">${esc(t.task_id || "?")} · ${esc(st)}${t.exit_code != null ? ` · exit ${t.exit_code}` : ""}</li>`;
            }).join("")
          : `<li class="muted">No recent tasks</li>`;
      }
    }
  } catch (e) {
    if (head) head.textContent = "Router status failed";
    if (connHost) connHost.innerHTML = `<p class="muted">${esc(e.message || e)}</p>`;
    kvRows(body, [["Error", e.message || e]]);
  }
}

async function exportSession(id, { pdf = true, visual = false } = {}) {
  const res = await postJSON("/api/export", {
    session_id: id,
    pdf,
    visual,
  });
  return res;
}

async function openSessionVisual(id) {
  selectedId = id;
  pinSession(id);
  setTab("visual");
  await loadVisual(id);
}

async function openSession(id) {
  selectedId = id;
  setTab("detail");
  document.querySelectorAll("#sessionRows .session-card, #sessionRows tr.clickable").forEach((el) => {
    el.classList.toggle("selected", el.dataset.id === id);
  });

  const data = await getJSON(`/api/session/${encodeURIComponent(id)}`);
  const hasAny = data.ok || data.dossier || data.narrative_md || data.has_residual;
  if (!hasAny) {
    $("#detailEmpty")?.classList.remove("hidden");
    $("#detailBody")?.classList.add("hidden");
    if ($("#detailEmpty")) {
      $("#detailEmpty").innerHTML = `No residual for <span class="mono">${esc(
        id
      )}</span> yet. Close session cleanly or run summarize-session.
        <div style="margin-top:0.75rem" class="muted">PDF/visual are export-only — file residual first.</div>`;
    }
    return;
  }
  $("#detailEmpty")?.classList.add("hidden");
  $("#detailBody")?.classList.remove("hidden");

  const d = data.dossier || {};
  const time = d.time || {};
  const chord = d.chord || {};
  const sk = d.scalar_knot || {};
  const links = data.links || {};
  const card = data.session_card || d.session_card || {};
  const stats = data.stats || {};

  $("#dTitle").textContent = card.title || time.title || id.slice(0, 16);
  $("#dId").textContent = id;
  $("#dMeta").textContent = [
    time.created_at?.iso_minute && `start ${time.created_at.iso_minute}`,
    time.updated_at?.iso_minute && `end ${time.updated_at.iso_minute}`,
    (stats.duration_minutes ?? sk.duration_minutes) != null &&
      `${stats.duration_minutes ?? sk.duration_minutes} min`,
    card.dominant_theme || stats.dominant_theme || (sk.theme_vector || {}).dominant,
    chord.commitment_hash,
  ]
    .filter(Boolean)
    .join(" · ");

  const pdfBtn = data.has_pdf
    ? `<a class="btn ghost" href="${esc(links.pdf)}" target="_blank">Open PDF</a>`
    : `<button type="button" class="btn ghost" id="btnExportPdf">Export PDF</button>`;
  const visBtn = data.has_visual
    ? `<button type="button" class="btn" id="btnOpenVis">Open visual</button>`
    : `<button type="button" class="btn ghost" id="btnExportVis">Export visual</button>`;

  $("#dLinks").innerHTML = `
    ${visBtn}
    ${pdfBtn}
    <button type="button" class="btn ghost" id="btnPinDetail">Pin</button>
    <a class="btn ghost" href="${esc(links.residual || links.dossier_json)}" target="_blank">Residual JSON</a>
    <a class="btn ghost" href="${esc(links.md)}" target="_blank">Narrative MD</a>
    <span class="muted" id="exportNote" style="font-size:0.75rem;margin-left:0.5rem"></span>
  `;
  $("#btnOpenVis")?.addEventListener("click", () => openSessionVisual(id));
  $("#btnPinDetail")?.addEventListener("click", () => pinSession(id));
  $("#btnExportPdf")?.addEventListener("click", async () => {
    const note = $("#exportNote");
    if (note) note.textContent = "Rendering PDF…";
    try {
      const r = await exportSession(id, { pdf: true, visual: false });
      if (r.ok && (r.pdf?.url || r.has_pdf)) {
        if (note) note.textContent = "PDF ready";
        if (r.pdf?.url) window.open(r.pdf.url, "_blank");
        await openSession(id);
      } else if (note) {
        note.textContent = r.pdf?.error || r.error || "export failed";
      }
    } catch (e) {
      if (note) note.textContent = String(e.message || e);
    }
  });
  $("#btnExportVis")?.addEventListener("click", async () => {
    const note = $("#exportNote");
    if (note) note.textContent = "Building visual…";
    try {
      const r = await exportSession(id, { pdf: false, visual: true });
      if (r.ok || r.visual?.ok) {
        if (note) note.textContent = "Visual ready";
        await openSessionVisual(id);
      } else if (note) {
        note.textContent = r.visual?.error || r.error || "export failed";
      }
    } catch (e) {
      if (note) note.textContent = String(e.message || e);
    }
  });

  const loops = (chord.loops_audited || [])
    .map((L) => `<li><b>${esc(L.id)}</b> — ${esc(L.plain)}</li>`)
    .join("");
  const moves = (chord.disentangled_moves || [])
    .map((m, i) => `<li>${i + 1}. ${esc(m)}</li>`)
    .join("");
  const tv = sk.theme_vector || {};
  const cardBullets = (card.bullets || [])
    .map((b) => `<li>${esc(b)}</li>`)
    .join("");
  const T = stats.tension_index ?? sk.tension_index;
  const Q = stats.Q_proxy ?? sk.Q_proxy;
  const msgs = stats.num_chat_messages ?? time.num_chat_messages;
  const commitHex = (stats.content_commit || (d.content_commit || {}).hex || "").toString();

  $("#dBody").innerHTML = `
    <div style="padding:0 1.25rem 0.5rem;max-width:48rem">
      <div class="stats-row" style="display:flex;flex-wrap:wrap;gap:0.75rem;margin-bottom:1rem">
        <div class="stat"><b>${T != null ? Number(T).toFixed(2) : "—"}</b><span>tension</span></div>
        <div class="stat"><b>${Q != null ? esc(Q) : "—"}</b><span>Q proxy</span></div>
        <div class="stat"><b>${msgs != null ? esc(msgs) : "—"}</b><span>chat msgs</span></div>
        <div class="stat"><b>${esc(stats.dominant_theme || tv.dominant || "—")}</b><span>theme</span></div>
        <div class="stat"><b>${data.has_residual ? "yes" : "no"}</b><span>residual</span></div>
        <div class="stat"><b>${data.has_pdf ? "yes" : "on demand"}</b><span>PDF</span></div>
      </div>
      <p style="line-height:1.5;margin:0 0 0.75rem"><b>What this day was</b><br/>${esc(
        card.blurb || chord.plain_english || d.tldr || "—"
      )}</p>
      ${
        cardBullets
          ? `<p class="muted" style="margin:0 0 0.25rem">What you asked / moved</p><ul class="session-card-detail-bullets" style="margin:0 0 1rem">${cardBullets}</ul>`
          : ""
      }
      <p><b>Impact:</b> ${esc(chord.personal_impact || "—")}</p>
      <p><b>Rope:</b> ${esc(chord.rope || "—")}</p>
      <p class="muted">Loops</p><ul>${loops || "<li>—</li>"}</ul>
      <p class="muted">Moves</p><ul>${moves || "<li>—</li>"}</ul>
      <p class="muted">leaf=${esc(stats.leaf || (d.verkle_knot || {}).filename)} · commit=${esc(
        commitHex.slice(0, 16)
      )}</p>
      <pre class="pre">${esc((data.narrative_md || "").slice(0, 4000))}</pre>
    </div>
  `;
}

function boardApi() {
  return {
    getJSON,
    postJSON,
    openSession,
    openSessionVisual,
  };
}

async function loadBoard() {
  try {
    if (window.MagBoard) {
      window.MagBoard.wireOnce(boardApi());
      await window.MagBoard.load(boardApi());
      return;
    }
    // Fallback if board.js missing
    const b = await getJSON("/api/board");
    if ($("#boardNote")) $("#boardNote").textContent = b.instrument_note || "";
    if ($("#briefOut")) $("#briefOut").textContent = b.latest_brief || "(no brief)";
    if ($("#liveOut")) $("#liveOut").textContent = b.live_from_grok || "(empty)";
    if ($("#attOut")) $("#attOut").textContent = b.attention || "(empty)";
    if ($("#todoOut")) $("#todoOut").textContent = b.todo || "(empty)";
    if ($("#statusOut")) {
      $("#statusOut").textContent =
        (b.mag_status || "") + "\n\n--- CURRENT ---\n" + (b.current || "");
    }
  } catch (e) {
    if ($("#boardNote")) $("#boardNote").textContent = String(e.message || e);
  }
}

async function loadBlast() {
  try {
    const b = await getJSON("/api/v1/blast").catch(() => getJSON("/api/blast"));
    const inf = b.influence || {};
    const st = b.status || {};
    const ol = b.ollama || {};
    if ($("#blastStats")) {
      const state = st.state || (b.thread_alive ? "thread" : "idle");
      $("#blastStats").innerHTML = `
        <div class="stat"><b>${esc(String(state))}</b><span>plant</span></div>
        <div class="stat"><b>${st.cycle ?? 0}</b><span>cycle</span></div>
        <div class="stat"><b>${st.digs_ok_total ?? 0}</b><span>digs ok</span></div>
        <div class="stat"><b>${ol.ok ? "UP" : "DOWN"}</b><span>ollama</span></div>
      `;
    }
    if ($("#blastFocus") && document.activeElement !== $("#blastFocus")) {
      $("#blastFocus").value = inf.focus || "";
    }
    if ($("#blastMinutes")) $("#blastMinutes").value = inf.dig_minutes ?? 45;
    if ($("#blastTickets")) $("#blastTickets").value = inf.max_tickets ?? 4;
    if ($("#blastCycle")) $("#blastCycle").value = inf.cycle_seconds ?? 300;
    if ($("#blastInfluenceMeta")) {
      $("#blastInfluenceMeta").textContent =
        `run=${inf.run} · paused=${inf.paused} · updated ${inf.updated || "—"} by ${inf.updated_by || "—"}`;
    }
    if ($("#blastStatusOut")) {
      $("#blastStatusOut").textContent = JSON.stringify(
        {
          state: st.state,
          cycle: st.cycle,
          digs_ok_total: st.digs_ok_total,
          consecutive_fails: st.consecutive_fails,
          last_phase: st.last_phase,
          last_error: st.last_error,
          deep_latest: st.deep_latest || b.deep_latest,
          focus: (inf.focus || "").slice(0, 200),
        },
        null,
        2
      );
    }
    if ($("#blastOllamaOut")) {
      $("#blastOllamaOut").textContent = JSON.stringify(
        {
          ok: ol.ok,
          base: ol.base,
          tags_n: ol.tags_n,
          tags_sample: ol.tags_sample,
          hint: b.hint,
        },
        null,
        2
      );
    }
    const host = $("#blastCandidates");
    if (host) {
      const tops = b.top_candidates || [];
      if (!tops.length) {
        host.innerHTML = `<p class="muted">No open tickets — run improve scout or start blast.</p>`;
      } else if (tops[0]?.error) {
        host.innerHTML = `<p class="muted">${esc(tops[0].error)}</p>`;
      } else {
        host.innerHTML = tops
          .map((c) => {
            const id = c.id || "";
            return `<div class="row" style="margin:0.4rem 0;align-items:flex-start;gap:0.5rem;flex-wrap:wrap">
              <code>${esc(id)}</code>
              <span class="muted">[${esc(String(c.kind || ""))} · ${c.score ?? "?"}]</span>
              <span style="flex:1">${esc(String(c.claim || "").slice(0, 120))}</span>
              <button type="button" class="btn ghost blast-promo" data-id="${esc(id)}" data-act="apply">Promote</button>
              <button type="button" class="btn ghost blast-promo" data-id="${esc(id)}" data-act="reject">Reject</button>
            </div>`;
          })
          .join("");
        host.querySelectorAll(".blast-promo").forEach((btn) => {
          btn.onclick = async () => {
            const cid = btn.getAttribute("data-id");
            const act = btn.getAttribute("data-act");
            try {
              await postJSON("/api/v1/blast/promote", {
                id: cid,
                reject: act === "reject",
                reason: act === "reject" ? "dash reject" : "",
              });
              loadBlast();
            } catch (e) {
              alert(String(e.message || e));
            }
          };
        });
      }
    }
  } catch (e) {
    if ($("#blastStatusOut")) $("#blastStatusOut").textContent = String(e.message || e);
  }
}

async function wireBlastOnce() {
  if (window._blastWired) return;
  window._blastWired = true;
  const act = async (action, extra) => {
    try {
      await postJSON("/api/v1/blast", { action, ...(extra || {}) });
      await loadBlast();
    } catch (e) {
      alert(String(e.message || e));
    }
  };
  $("#btnBlastStart")?.addEventListener("click", () => act("start"));
  $("#btnBlastStop")?.addEventListener("click", () => act("stop"));
  $("#btnBlastPause")?.addEventListener("click", () => act("pause"));
  $("#btnBlastResume")?.addEventListener("click", () => act("resume"));
  $("#btnBlastRefresh")?.addEventListener("click", () => loadBlast());
  $("#btnBlastSave")?.addEventListener("click", async () => {
    await act("patch", {
      focus: $("#blastFocus")?.value || "",
      dig_minutes: Number($("#blastMinutes")?.value || 45),
      max_tickets: Number($("#blastTickets")?.value || 4),
      cycle_seconds: Number($("#blastCycle")?.value || 300),
    });
  });
}
// wire on load
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireBlastOnce);
  } else {
    wireBlastOnce();
  }
}

async function loadOrchestrate() {
  try {
    const u = await getJSON("/api/usage");
    if ($("#orchStats")) {
      $("#orchStats").innerHTML = `
        <div class="stat"><b>${u.grok_escalations_today ?? 0}/${u.grok_budget_max ?? 8}</b><span>L2 today</span></div>
      `;
    }
    if ($("#laneCfg")) $("#laneCfg").textContent = JSON.stringify(u.lanes || {}, null, 2);
    if ($("#usageToday")) $("#usageToday").textContent = JSON.stringify(u.today || {}, null, 2);
    if ($("#usageTail")) {
      const tail = (u.tail || []).slice().reverse();
      $("#usageTail").textContent = tail
        .map((r) => {
          const m = r.meta || {};
          const mm = m.model ? ` ${m.model}` : "";
          return `${r.ts || ""}  ${r.lane}  ${r.action}${mm}  ${r.ok ? "ok" : "fail"}  ${(r.detail || "").slice(0, 60)}`;
        })
        .join("\n") || "(empty)";
    }
    await loadModelsPanel();
    const smoke = await getJSON("/api/multi-smoke/latest").catch(() => null);
    if ($("#smokeOut") && smoke && !smoke.error) {
      $("#smokeOut").textContent = `${smoke.ok ? "PASS" : "FAIL"} · ${smoke.verdict || ""}\nmodels: ${(smoke.models_seen || []).join(", ")}\n${smoke.path || ""}`;
    }
  } catch (e) {
    if ($("#usageTail")) $("#usageTail").textContent = String(e.message || e);
  }
}

async function loadModelsPanel() {
  try {
    const inv = await getJSON("/api/models");
    if ($("#modelsLine")) {
      $("#modelsLine").textContent = inv.ok
        ? `Ollama up · ${(inv.tags || []).length} models · sequential`
        : "Ollama down — multi-model offline";
    }
    if ($("#modelsMap")) {
      const rows = inv.roles || [];
      $("#modelsMap").textContent = rows
        .map((r) => `${r.present ? "✓" : "✗"}  ${r.role.padEnd(12)} → ${r.model}`)
        .join("\n");
    }
  } catch (e) {
    if ($("#modelsMap")) $("#modelsMap").textContent = String(e.message || e);
  }
  await loadQuotaPanel();
}

async function loadChains() {
  const list = $("#chainsList");
  if (!list) return;
  try {
    const data = await getJSON("/api/providers");
    const provs = data.providers || [];
    const keyed = provs.filter((p) => p.configured);
    if (!keyed.length) {
      list.innerHTML = `<p class="muted">No keys in env. Paste keys into .env, then "python main.py providers" re-probes.</p>`;
      return;
    }
    list.innerHTML = keyed
      .map((p) => {
        const n = p.key_count || (p.configured ? 1 : 0);
        const multi = p.multi_key ? ` · ${n} keys` : "";
        const dot = p.configured ? "live" : "dark";
        return `<button type="button" class="conn-row ${dot}" title="${esc(p.key_env || "")}">
          <span class="conn-dot"></span>
          <span class="conn-name">${esc(p.name || p.id)}</span>
          <span class="conn-model muted">${esc(p.default_model || "")}</span>
          <span class="conn-budget">${esc(multi || (p.free_local ? "local" : "key"))}</span>
        </button>`;
      })
      .join("");
    const hint = $("#chainsHint");
    if (hint) hint.textContent = "DeepSeek chain = DEEPSEEK_API_KEY → DEEPSEEK_OVERMIND_API_KEY failover. Vast needs VAST_OPENAI_BASE_URL + key.";
  } catch (e) {
    list.innerHTML = `<p class="muted">chains unavailable: ${esc(String(e.message || e))}</p>`;
  }
}

async function loadQuotaPanel() {
  try {
    const q = await getJSON("/api/quota");
    const st = await getJSON("/api/providers");
    let probe = null;
    try {
      probe = await getJSON("/api/probe-status");
    } catch (_) {
      probe = null;
    }
    const probeMap = {};
    (probe?.providers || []).forEach((r) => {
      probeMap[r.id] = r;
    });

    const host = $("#quotaTable");
    if (host) {
      const rows = q.providers || [];
      host.innerHTML =
        rows
          .map((p) => {
            const pr = probeMap[p.provider];
            const live = pr?.ok ? "LIVE" : pr?.probe === "fail" ? "DEAD" : p.configured ? "KEY" : "—";
            const rem = p.unlimited
              ? "∞"
              : `left ${p.remaining_calls ?? "—"}c / ${p.remaining_tokens ?? "—"}t`;
            const reset = p.unlimited ? "—" : `reset ~${p.reset_in_hours}h`;
            const ok = pr?.ok ? "●" : p.configured ? "◐" : "○";
            return `<div class="row"><span class="k">${ok} ${esc(p.provider)}</span><span class="v">${esc(live)} · used ${p.used_calls}c/${p.used_tokens}t · ${rem} · ${reset}</span></div>`;
          })
          .join("") || "<div class='muted'>No providers.yaml</div>";
    }
    if ($("#probeTable") && probe?.providers) {
      $("#probeTable").innerHTML =
        `<div class="row"><span class="k">working</span><span class="v">${esc((probe.working || []).join(", ") || "—")}</span></div>` +
        `<div class="row"><span class="k">failed</span><span class="v">${esc((probe.failed || []).join(", ") || "—")}</span></div>` +
        `<div class="row"><span class="k">no key</span><span class="v">${esc((probe.no_key || []).join(", ") || "—")}</span></div>` +
        `<div class="row"><span class="k">probed</span><span class="v">${esc(probe.ts || "—")}</span></div>`;
    }
    if ($("#providersHint")) {
      $("#providersHint").textContent = st.how_to_add_key || st.note || "";
    }
    try {
      const ur = await getJSON("/api/usage-report");
      if ($("#usageReportLine")) {
        $("#usageReportLine").textContent =
          `local ${ur.local?.tokens ?? 0} tok / ${ur.local?.calls ?? 0} calls · remote ${ur.remote?.tokens ?? 0} tok · Grok TUI: ${ur.grok_tui || "unknown"}`;
      }
      if ($("#usageReport")) {
        $("#usageReport").innerHTML = `
          <div class="row"><span class="k">local</span><span class="v">${ur.local?.calls ?? 0} calls · ${ur.local?.tokens ?? 0} tokens</span></div>
          <div class="row"><span class="k">remote</span><span class="v">${ur.remote?.calls ?? 0} calls · ${ur.remote?.tokens ?? 0} tokens</span></div>
          <div class="row"><span class="k">Grok TUI</span><span class="v">${esc(ur.grok_tui || "unknown")}</span></div>`;
      }
    } catch (_) {
      /* optional */
    }
  } catch (e) {
    if ($("#quotaTable")) $("#quotaTable").textContent = String(e.message || e);
  }
}

function _historyFromEvolution(v) {
  const evo = v.evolution || {};
  const basis = evo.theme_basis || [];
  const series = [...(evo.series || [])].sort((a, b) =>
    String(a.start_minute || "").localeCompare(String(b.start_minute || ""))
  );
  return series.map((row) => {
    const tv = row.theme_vector || row.theme_vector_normalized;
    let dominant = row.dominant_theme;
    if (!dominant && tv && basis.length) {
      const i = tv.indexOf(Math.max(...tv.map(Number)));
      dominant = basis[i] || "—";
    }
    return {
      session_id: row.session_id,
      start_minute: row.start_minute,
      dominant_theme: dominant || "—",
      tension_index: row.tension_index,
      duration_minutes: row.duration_minutes,
      filename: row.filename,
    };
  });
}

function _histFromHistory(history, basis) {
  const hist = {};
  for (const b of basis || []) hist[b] = 0;
  for (const h of history) {
    const d = h.dominant_theme || "—";
    hist[d] = (hist[d] || 0) + 1;
  }
  return hist;
}

async function loadVerkle() {
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
      const history = _historyFromEvolution(v);
      L = {
        tip: v.tip || {},
        history,
        theme_histogram: _histFromHistory(history, (v.evolution || {}).theme_basis),
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
      const root = String((v.tip || {}).root || "");
      if (L.tip && root) {
        L.tip.root_short = root.slice(0, 16);
        L.tip.alive = Boolean((v.tip || {}).n_leaves);
      }
    }
    const tip = L.tip || {};
    const plan = L.plan || {};
    const hist = L.theme_histogram || {};
    const history = L.history || [];
    const basis = L.theme_basis || Object.keys(hist);
    const maxH = Math.max(1, ...Object.values(hist).map(Number), 1);

    const graph = L.graph || {};
    const statsEl = $("#latticeStats");
    if (statsEl) {
      const alive = tip.alive ? "ALIVE" : "EMPTY";
      const tAvg = L.tension_avg != null ? Number(L.tension_avg).toFixed(2) : "—";
      const tLast = L.tension_latest != null ? Number(L.tension_latest).toFixed(2) : "—";
      statsEl.innerHTML = [
        ["tip", tip.root_short ? tip.root_short + "…" : "—"],
        ["leaves", tip.n_leaves ?? L.history_n ?? "—"],
        ["chain", L.chain_n ?? "—"],
        ["graph nodes", graph.node_count ?? "—"],
        ["graph edges", graph.edge_count ?? "—"],
        ["instrument digs", graph.kinds?.instrument_dig ?? "—"],
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
    if ($("#latticeGraph")) {
      const nc = Number(graph.node_count || 0);
      const ec = Number(graph.edge_count || 0);
      if (!graph.store_exists && !nc) {
        $("#latticeGraph").innerHTML =
          "<p class='muted'>No lattice store on disk — run <code>python main.py lattice-backfill</code> then Refresh.</p>";
      } else {
        const kindRows = Object.entries(graph.kinds || {})
          .map(([k, v]) => `<span>${esc(k)}: <strong>${esc(String(v))}</strong></span>`)
          .join("");
        const edgeRows = Object.entries(graph.edge_kinds || {})
          .map(([k, v]) => `<span>${esc(k)}: <strong>${esc(String(v))}</strong></span>`)
          .join("");
        const sampleNodes = (graph.sample_nodes || [])
          .map((n) => {
            const kind = n.kind || "node";
            const label = n.unit_id || n.id || "—";
            const theme = n.dominant_theme ? ` · ${esc(n.dominant_theme)}` : "";
            return `<div class="graph-node-row"><span class="pill">${esc(kind)}</span> <span class="mono">${esc(String(label).slice(0, 48))}</span>${theme}</div>`;
          })
          .join("");
        const sampleEdges = (graph.sample_edges || [])
          .map((e) => {
            const kind = e.kind || "edge";
            const src = String(e.source || "").slice(0, 20);
            const tgt = String(e.target || "").slice(0, 20);
            return `<div class="graph-node-row muted"><span class="pill">${esc(kind)}</span> <span class="mono">${esc(src)} → ${esc(tgt)}</span></div>`;
          })
          .join("");
        $("#latticeGraph").innerHTML = `
          <div class="graph-stat-row">${kindRows || "<span class='muted'>no nodes</span>"}</div>
          <div class="graph-stat-row">${edgeRows ? "edges: " + edgeRows : ""}</div>
          <p class="meta">${esc(String(nc))} nodes · ${esc(String(ec))} edges · paths: memory/lattice/</p>
          <div class="graph-sample">
            <p class="meta">Sample nodes</p>
            ${sampleNodes || "<p class='muted'>—</p>"}
            <p class="meta" style="margin-top:0.5rem">Sample edges</p>
            ${sampleEdges || "<p class='muted'>—</p>"}
          </div>`;
      }
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

function _renderViewportSection(sec) {
  const title = esc(sec.title || sec.kind || "Section");
  if (sec.kind === "stats") {
    const items = sec.items || [];
    return `<article class="card viewport-section viewport-stats">
      <h3>${title}</h3>
      <div class="viewport-stat-grid">${items
        .map(
          (it) =>
            `<div class="viewport-stat"><span class="k">${esc(it.label)}</span><span class="v">${esc(it.value)}</span></div>`
        )
        .join("")}</div>
    </article>`;
  }
  if (sec.kind === "todos") {
    const items = sec.items || [];
    return `<article class="card viewport-section viewport-todos">
      <h3>${title}</h3>
      <ul class="viewport-todo-list">${items
        .map(
          (it) =>
            `<li class="todo-${esc(it.status || "pending")}"><span class="todo-status">${esc(it.status || "pending")}</span> ${esc(it.content || "")}</li>`
        )
        .join("")}</ul>
    </article>`;
  }
  if (sec.kind === "table") {
    const cols = sec.columns || [];
    const rows = sec.rows || [];
    return `<article class="card viewport-section viewport-table">
      <h3>${title}</h3>
      <div class="viewport-table-wrap">
        <table class="viewport-table">
          <thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
          <tbody>${rows
            .map(
              (row) =>
                `<tr>${(row || [])
                  .map((cell) => `<td>${esc(cell)}</td>`)
                  .join("")}</tr>`
            )
            .join("")}</tbody>
        </table>
      </div>
    </article>`;
  }
  return "";
}

function _renderViewport(vp) {
  const sections = (vp.sections || []).map(_renderViewportSection).join("");
  return `<article class="card viewport-card" data-viewport-id="${esc(vp.id || "")}">
    <header class="viewport-head">
      <h2>${esc(vp.title || vp.id || "Viewport")}</h2>
      <p class="meta">${esc(vp.id || "")} · synced ${esc(vp.synced_at || "—")}</p>
    </header>
    <div class="viewport-sections">${sections || "<p class='muted'>No sections</p>"}</div>
  </article>`;
}

async function loadViewports() {
  const host = $("#viewportsHost");
  const meta = $("#viewportsMeta");
  if (!host) return;
  host.innerHTML = `<p class="muted">Loading viewports…</p>`;
  try {
    const data = await getJSON("/api/v1/viewports");
    const list = data.viewports || [];
    if (meta) meta.textContent = `${list.length} viewport(s)`;
    if (!list.length) {
      host.innerHTML = `<p class="muted">No viewports synced yet. Run <code>python main.py canvas-sync</code>.</p>`;
      return;
    }
    const parts = [];
    for (const row of list) {
      const one = await getJSON(`/api/v1/viewports/${encodeURIComponent(row.id)}`);
      const vp = one.viewport || one;
      parts.push(_renderViewport(vp));
    }
    host.innerHTML = parts.join("");
  } catch (e) {
    host.innerHTML = `<p class="muted" style="color:var(--warn)">${esc(e.message || e)}</p>`;
    if (meta) meta.textContent = "error";
  }
}

async function syncViewportsFromDesk() {
  const meta = $("#viewportsMeta");
  if (meta) meta.textContent = "syncing…";
  try {
    const r = await fetch("/api/v1/viewports/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await r.json();
    if (meta) meta.textContent = `synced ${data.written_n ?? 0}`;
    await loadViewports();
    toast(`Canvas sync: ${data.written_n ?? 0} viewport(s)`, 2200);
  } catch (e) {
    if (meta) meta.textContent = "sync failed";
    toast("Sync error: " + (e.message || e));
  }
}

async function loadIngest() {
  try {
    const data = await getJSON("/api/ingest");
    const items = Object.values((data.catalog || {}).items || {}).slice(0, 40);
    if ($("#ingestOut")) {
      $("#ingestOut").innerHTML =
        items
          .map(
            (it) =>
              `<div class="bib-item"><span class="mono">${esc(it.id)}</span> · ${esc(it.filename || "—")} · ${(it.tags || []).slice(0, 4).map(esc).join(", ")}</div>`
          )
          .join("") || "<p class='muted'>Empty catalog</p>";
    }
  } catch (e) {
    if ($("#ingestOut")) $("#ingestOut").textContent = String(e.message || e);
  }
}

async function refresh() {
  toast("Refreshing…", 1200);
  try {
    overview = await getJSON("/api/v1/overview");
  } catch {
    try {
      overview = await getJSON("/api/overview");
    } catch (e) {
      toast("Overview failed: " + (e.message || e));
      overview = overview || { sessions: [] };
    }
  }
  try {
    window.__lastOverview = overview;
    renderStats(overview);
    if (overview?.sessions) {
      renderSessions(overview.sessions || []);
      fillSessionSelect(overview.sessions || []);
    }
    renderPins();
  } catch {
    /* non-fatal */
  }
  await pollHealth();
  const active = activePane();
  try {
    if (active === "home") await loadHome();
    else if (active === "sessions" || active === "days") {
      if (overview?.sessions) renderSessions(overview.sessions);
      await loadTapestry();
    } else if (active === "ideas") await loadIdeas();
    else if (active === "status") await loadStatus();
    else if (active === "chronicle") await loadChronicle();
    else if (active === "diary") await loadDiary();
    else if (active === "board") await loadBoard();
    else if (active === "operate") await loadOperate();
    else if (active === "chat") {
      renderChat();
      await refreshEconomy();
    } else if (active === "verkle") await loadVerkle();
    else if (active === "viewports") await loadViewports();
    else if (active === "flow") await loadFlow();
    else if (active === "orchestrate") await loadOrchestrate();
    else if (active === "visual") await loadVisual();
    else if (active === "detail" && selectedId) await openSession(selectedId);
    else await loadHome();
    toast("Refreshed · " + active, 1800);
  } catch (e) {
    toast("Refresh error: " + (e.message || e));
  }
}

async function bind() {
  try { wireMirrorGuide(); } catch (e) { console.error(e); }
  try { wireDaysDesk(); } catch (e) { console.error(e); }

  document.querySelectorAll(".tab[data-tab]").forEach((t) => {
    t.addEventListener("click", () => {
      if (t.dataset.tab) setTab(t.dataset.tab);
    });
  });
  $("#btnAdvanced")?.addEventListener("click", (e) => {
    e.stopPropagation();
    const menu = $("#advMenu");
    const btn = $("#btnAdvanced");
    if (!menu) return;
    const open = menu.classList.contains("hidden");
    menu.classList.toggle("hidden", !open);
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.addEventListener("click", (e) => {
    const wrap = document.querySelector(".tab-adv-wrap");
    if (wrap && !wrap.contains(e.target)) {
      $("#advMenu")?.classList.add("hidden");
      $("#btnAdvanced")?.setAttribute("aria-expanded", "false");
    }
  });
  $("#btnRefresh")?.addEventListener("click", () => refresh());
  $("#btnCatchUp")?.addEventListener("click", () => doCatchUp());
  $("#btnOsCard")?.addEventListener("click", () => {
    const panel = $("#magOsCardPanel");
    if (!panel) return;
    panel.classList.toggle("hidden");
    if (!panel.classList.contains("hidden")) loadMagOs();
  });
  $("#btnOsRefresh")?.addEventListener("click", () => loadOperate());
  $("#btnOsCatchUp")?.addEventListener("click", () => doCatchUp());
  document.querySelectorAll("[data-tpl]").forEach((btn) => {
    btn.addEventListener("click", () => showOsTemplate(btn.dataset.tpl));
  });
  $("#btnCopyFeed")?.addEventListener("click", () => {
    copyText($("#osFeed")?.value, $("#osCopyStatus"));
  });
  $("#btnCopyTicket")?.addEventListener("click", () => {
    showOsTemplate("build");
    copyText($("#osFeed")?.value, $("#osCopyStatus"));
  });
  $("#btnOsOpenSessions")?.addEventListener("click", () => setTab("sessions"));
  $("#btnOsOpenVisual")?.addEventListener("click", () => {
    const sid = window.__osLatestSid;
    if (sid) openSessionVisual(sid);
    else setTab("visual");
  });
  $("#btnTapRebuild")?.addEventListener("click", async () => {
    if ($("#tapMeta")) $("#tapMeta").textContent = "Rebuilding…";
    try {
      await postJSON("/api/v1/tapestry/rebuild", {});
      await loadTapestry();
    } catch (e) {
      if ($("#tapCaption")) $("#tapCaption").textContent = String(e.message || e);
    }
  });
  $("#btnTapFrame")?.addEventListener("click", () => {
    const nodes = tapestryView?.pack?.connections?.nodes;
    if (tapestryView && nodes?.length) {
      tapestryView._userMoved = false;
      tapestryView.resize({ forceFit: true });
      toast("Framed graph to stage");
    } else {
      toast("Load graph first");
    }
  });
  $("#tapLatticeToggle")?.addEventListener("change", (e) => {
    tapestryView?.setLatticeVisible?.(e.target.checked);
  });
  window.addEventListener("mag:win-open", (e) => {
    const id = e.detail?.id;
    if (id === "chronicle") startChroniclePoll();
    if (id === "status") loadStatus();
    if (id === "viewports") loadViewports();
    if (id === "tapestry" || id === "sessions") {
      setTimeout(() => tapestryView?.resize?.({ forceFit: true }), 80);
      setTimeout(() => tapestryView?.resize?.({ forceFit: true }), 300);
    }
  });
  window.addEventListener("mag:win-resize", (e) => {
    const id = e.detail?.id;
    if (!id || id === "tapestry" || id === "sessions") {
      tapestryView?.resize?.({ forceFit: !tapestryView?._userMoved });
    }
  });
  window.addEventListener("mag:tapestry-session", (e) => {
    const sid = e.detail?.session_id;
    if (sid) selectDayOnDesk(sid);
  });
  // Office + Days CTAs
  $("#btnHomeRefresh")?.addEventListener("click", () => loadHome());
  $("#btnHomeChat")?.addEventListener("click", () => {
    setTab("chat");
    if ($("#chatInput") && !$("#chatInput").value.trim()) {
      $("#chatInput").value = "what was I doing?";
    }
  });
  $("#btnHomeDays")?.addEventListener("click", () => setTab("sessions"));
  $("#btnHomeIdeas")?.addEventListener("click", () => setTab("ideas"));
  $("#btnHomePack")?.addEventListener("click", async () => {
    const t = "python main.py context-pack";
    try {
      await navigator.clipboard.writeText(t);
      if ($("#cliStatusLine")) $("#cliStatusLine").textContent = "Copied: " + t;
    } catch {
      prompt("Copy pack CLI:", t);
    }
  });
  $("#btnHomeVisual")?.addEventListener("click", () => {
    const sid = window.__osLatestSid;
    if (sid) openSessionVisual(sid);
    else setTab("visual");
  });
  $("#btnHomeVerify")?.addEventListener("click", () => {
    const el = $("#homeVerifyCard");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      el.classList.add("verify-flash");
      setTimeout(() => el.classList.remove("verify-flash"), 1200);
    }
    loadHome();
  });
  $("#btnDaysOpenDetail")?.addEventListener("click", () => {
    if (selectedId) openSession(selectedId);
    else setTab("detail");
  });
  $("#btnDaysOpenVisual")?.addEventListener("click", () => {
    if (selectedId) openSessionVisual(selectedId);
    else setTab("visual");
  });
  $("#btnIdeasRefresh")?.addEventListener("click", () => loadIdeas());
  $("#btnIdeasSeed")?.addEventListener("click", () => seedIdeas());
  $("#btnIdeaDone")?.addEventListener("click", () => patchIdeaStatus("done"));
  $("#btnIdeaShelf")?.addEventListener("click", () => patchIdeaStatus("held"));
  $("#btnIdeaReopen")?.addEventListener("click", () => patchIdeaStatus("open"));
  $("#btnStatusReload")?.addEventListener("click", () => loadStatus());
  $("#btnPowerStop")?.addEventListener("click", () => onPowerStop());
  $("#btnPowerStart")?.addEventListener("click", () => onPowerStart());
  $("#btnImproveCycle")?.addEventListener("click", () => onImproveCycle());
  $("#btnSeatFeedReload")?.addEventListener("click", () => loadSeatFeed());
  $("#btnAutopilotOnce")?.addEventListener("click", () => onAutopilotOnce());
  $("#drainerToggle")?.addEventListener("change", () => onDrainerToggleChange());
  $("#govDrainerToggle")?.addEventListener("change", () => onGovDrainerChange());
  $("#govBehavioralToggle")?.addEventListener("change", () => onGovBehavioralChange());
  $("#btnGovSteerSend")?.addEventListener("click", () => sendGovernanceSteer($("#govSteerInput")?.value));
  document.querySelectorAll("[data-gov-steer]").forEach((btn) => {
    btn.addEventListener("click", () => sendGovernanceSteer(btn.dataset.govSteer));
  });
  $("#govSteerInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendGovernanceSteer($("#govSteerInput")?.value);
    }
  });
  $("#btnOpenWorkers")?.addEventListener("click", () => setTab("agents"));
  $("#btnProbeChains")?.addEventListener("click", async () => {
    const hint = $("#chainsHint");
    if (hint) hint.textContent = "probing (can take ~minutes for many keys)...";
    try {
      const r = await fetch("/api/probe-status", { method: "POST" });
      await r.json();
      loadStatus();
      if (hint) hint.textContent = "probe done - see /api/usage-report";
    } catch (e) {
      if (hint) hint.textContent = "probe failed: " + String(e.message || e);
    }
  });
  $("#btnStatusCatchUp")?.addEventListener("click", () => doCatchUp());
  $("#ideasFilters")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-filter]");
    if (!btn) return;
    ideasFilter = btn.dataset.filter || "open";
    $("#ideasFilters")
      .querySelectorAll("[data-filter]")
      .forEach((b) => b.classList.toggle("on", b === btn));
    renderIdeasList();
  });
  $("#btnIdeasCopyPack")?.addEventListener("click", async () => {
    if (!ideasSelectedPack) return;
    try {
      await navigator.clipboard.writeText(ideasSelectedPack);
      toast("Pack copied");
    } catch {
      prompt("Copy pack:", ideasSelectedPack);
    }
  });
  $("#btnIdeasToChat")?.addEventListener("click", () => {
    if (!ideasSelectedPack) return;
    setTab("chat");
    const input = $("#chatInput");
    if (input) {
      input.value =
        "Using this idea pack, what should I do next?\n\n" + ideasSelectedPack.slice(0, 3500);
    }
    toast("Pack loaded into Chat compose");
  });
  setChatMode("agent");
  renderChat();
  $("#btnChatSend")?.addEventListener("click", () => sendChat());
  $("#btnSteer")?.addEventListener("click", () => sendSteer());
  $("#steerInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); sendSteer(); }
  });
  $("#btnInboxQueue")?.addEventListener("click", () => commitOperatorGuidance());
  $("#operatorInboxInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      commitOperatorGuidance();
    }
  });
  $("#btnInboxClear")?.addEventListener("click", () => {
    const input = $("#operatorInboxInput");
    if (input) input.value = "";
  });
  document.querySelectorAll(".inbox-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = $("#operatorInboxInput");
      if (input) input.value = btn.dataset.inbox || "";
      commitOperatorGuidance();
    });
  });
  $("#btnCopyPack")?.addEventListener("click", () => copyContextPack());
  $("#btnChatClear")?.addEventListener("click", () => {
    if (confirm("Clear chat history on this browser?")) {
      localStorage.removeItem(CHAT_KEY);
      renderChat();
    }
  });
  $("#btnAgentReset")?.addEventListener("click", async () => {
    try {
      await postJSON("/api/v1/agent", {
        reset_only: true,
        session_id: AGENT_SESSION,
      });
    } catch {
      /* still clear UI */
    }
    localStorage.removeItem(CHAT_KEY);
    renderChat();
    if ($("#chatStatus")) $("#chatStatus").textContent = "Agent session reset · next turn reloads pack";
  });
  $("#chatModeAgent")?.addEventListener("click", () => setChatMode("agent"));
  $("#chatModeAsk")?.addEventListener("click", () => setChatMode("ask"));
  $("#chatModeDispatch")?.addEventListener("click", () => setChatMode("dispatch"));
  $("#chatModeTangent")?.addEventListener("click", () => setChatMode("tangent"));
  document.querySelectorAll("#chatChips .chip").forEach((b) => {
    b.addEventListener("click", () => {
      if ($("#chatInput")) $("#chatInput").value = b.dataset.q || "";
      sendChat();
    });
  });
  $("#chatInput")?.addEventListener("keydown", (e) => {
    // Grok-compose steal: Enter send · Shift/Alt+Enter newline · Shift+Tab mode
    if (e.key === "Tab" && e.shiftKey) {
      e.preventDefault();
      cycleChatMode();
      return;
    }
    if (e.key === "Enter" && !e.shiftKey && !e.altKey) {
      e.preventDefault();
      sendChat();
      return;
    }
    // Shift+Enter / Alt+Enter = newline (default textarea behavior when we don't prevent)
  });
  $("#chatInput")?.addEventListener("paste", async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const it of items) {
      if (it.type && it.type.startsWith("image/")) {
        e.preventDefault();
        const file = it.getAsFile();
        if (!file) continue;
        try {
          if ($("#chatStatus")) $("#chatStatus").textContent = "Uploading image…";
          await uploadBlob(file, `paste.${(it.type.split("/")[1] || "png").replace("jpeg", "jpg")}`);
          pushChat(
            "sys",
            `Attached image → \`${composePending[composePending.length - 1]?.path || "?"}\` (path for tools; no vision pixels yet)`,
            "attach"
          );
        } catch (err) {
          if ($("#chatStatus")) $("#chatStatus").textContent = String(err.message || err);
        }
        return;
      }
    }
  });
  $("#chatFile")?.addEventListener("change", async (e) => {
    const f = e.target?.files?.[0];
    if (!f) return;
    try {
      await uploadBlob(f, f.name);
    } catch (err) {
      if ($("#chatStatus")) $("#chatStatus").textContent = String(err.message || err);
    }
    e.target.value = "";
  });
  refreshChatQuota();

  $("#btnAsk")?.addEventListener("click", async () => {
    const q = ($("#askQ")?.value || "").trim();
    if (!q) {
      $("#askOut").textContent = "Type a question.";
      return;
    }
    $("#askOut").textContent = "Asking local model…";
    try {
      const res = await postJSON("/api/v1/ask", { question: q });
      $("#askOut").textContent = res.answer || JSON.stringify(res, null, 2);
    } catch (e) {
      $("#askOut").textContent = String(e.message || e);
    }
  });
  $("#btnBrief")?.addEventListener("click", async () => {
    $("#briefOut").textContent = "Building brief (L0)…";
    try {
      const res = await postJSON("/api/brief", { session: "latest" });
      if (res.ok) {
        const b = await getJSON("/api/brief/latest");
        $("#briefOut").textContent = b.text || res.preview || "ok";
      } else {
        $("#briefOut").textContent = JSON.stringify(res, null, 2);
      }
    } catch (e) {
      $("#briefOut").textContent = String(e.message || e);
    }
  });
  $("#btnZoomIn")?.addEventListener("click", () => vis?.zoomIn());
  $("#btnZoomOut")?.addEventListener("click", () => vis?.zoomOut());
  $("#btnFit")?.addEventListener("click", () => vis?.fitView());
  $("#btnResetView")?.addEventListener("click", () => vis?.resetView());
  $("#btnModelsRefresh")?.addEventListener("click", () => loadModelsPanel());
  $("#btnQuotaRefresh")?.addEventListener("click", () => loadQuotaPanel());
  $("#btnFlowRefresh")?.addEventListener("click", () => loadFlow());
  $("#btnProbeNow")?.addEventListener("click", async () => {
    if ($("#probeTable")) $("#probeTable").innerHTML = `<div class="muted">Probing (may take a minute)…</div>`;
    try {
      await postJSON("/api/probe-status", {});
      await loadQuotaPanel();
    } catch (e) {
      if ($("#probeTable")) $("#probeTable").textContent = String(e.message || e);
    }
  });
  $("#btnMultiSmoke")?.addEventListener("click", async () => {
    if ($("#smokeOut")) $("#smokeOut").textContent = "Running multi-smoke (clerk+worker+critic)…";
    try {
      const res = await postJSON("/api/multi-smoke", {});
      $("#smokeOut").textContent = `${res.ok ? "PASS" : "FAIL"} · ${res.verdict || ""}\nmodels: ${(res.models_seen || []).join(", ")}\n${JSON.stringify(res.steps || [], null, 2).slice(0, 2000)}`;
      await loadOrchestrate();
    } catch (e) {
      $("#smokeOut").textContent = String(e.message || e);
    }
  });
  $("#btnVisRebuild")?.addEventListener("click", async () => {
    if ($("#visMeta")) $("#visMeta").textContent = "Rebuilding…";
    const sid = visualSessionId || "latest";
    await postJSON("/api/visual/rebuild", {
      session_id: sid === "latest" ? null : sid,
    });
    await loadVisual(sid);
  });
  $("#visSessionSelect")?.addEventListener("change", (e) => {
    const v = e.target.value || "latest";
    loadVisual(v);
  });
  $("#btnVisPin")?.addEventListener("click", () => {
    const sid = visualSessionId;
    if (sid && sid !== "latest") pinSession(sid);
    else if (visPack?.session_id) pinSession(visPack.session_id);
  });
  $("#btnVisWalk")?.addEventListener("click", () => {
    if (!visPack?.walk?.length || !vis) return;
    if (walkTimer) {
      clearInterval(walkTimer);
      walkTimer = null;
      return;
    }
    let i = 0;
    const steps = visPack.walk;
    const tick = () => {
      const s = steps[i % steps.length];
      const host = $("#visChambers");
      host?.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("on", b.dataset.ch === s.chamber);
      });
      vis.setChamber(s.chamber);
      if ($("#visCaption")) {
        $("#visCaption").innerHTML = `<div class="vis-q">Walk ${s.step}/${steps.length}</div>
          <div class="vis-h">${esc(s.say || "")}</div>`;
      }
      i++;
    };
    tick();
    walkTimer = setInterval(tick, 3200);
  });
}


bind();
// Top bar: Magatama + rotating inspiration (not CAVEATS/UP theater)
rotateMagQuote(false);
$("#cliQuote")?.addEventListener("click", () => rotateMagQuote(true));
setInterval(() => rotateMagQuote(true), 90_000);
// Default = Home summary (not chat museum)
setTab("home");
refresh().catch((e) => console.error(e));
refreshEconomy();
maybeStartMirrorGuide();
// Health still polled quietly for Status; not painted as useless top badges
pollHealth();
setInterval(pollHealth, 30000);
setInterval(refreshEconomy, 20000);

// Lattice history panel
document.getElementById("btnLatticeRefresh")?.addEventListener("click", () => loadVerkle());
document.getElementById("btnViewportsRefresh")?.addEventListener("click", () => loadViewports());
document.getElementById("btnViewportsSync")?.addEventListener("click", () => syncViewportsFromDesk());
document.getElementById("btnLatticePack")?.addEventListener("click", () => {
  const t = "memory/biography/verkle_tip.json � topic_evolution.json � knot_timeline.jsonl � working.md";
  if (navigator.clipboard?.writeText) navigator.clipboard.writeText(t);
});

document.getElementById('chatProvider')?.addEventListener('change', () => setChatMode(chatMode));

