/* Mag desk — tab shell (primary doors). */
(function () {
  const STORAGE = "mag_cli_wins_v8";
  const LAYOUT_VER = 8;
  const PRIMARY = new Set(["sessions", "chat", "home", "ideas", "stack"]);
  const ALIAS = {
    office: "home",
    days: "sessions",
    tapestry: "sessions",
    diary: "sessions",
    story: "sessions",
    chronicle: "sessions",
    viewports: "chat",
    map: "home",
  };

  function resolve(id) {
    id = ALIAS[id] || id;
    return id;
  }

  function loadFocus() {
    try {
      const raw = JSON.parse(localStorage.getItem(STORAGE) || "null");
      if (raw && raw.v === LAYOUT_VER && raw.focus) return resolve(raw.focus);
    } catch {
      /* ignore */
    }
    return "home";
  }

  function saveFocus(id) {
    try {
      localStorage.setItem(
        STORAGE,
        JSON.stringify({ v: LAYOUT_VER, focus: resolve(id), savedAt: Date.now() })
      );
    } catch {
      /* ignore */
    }
  }

  function syncDock(id) {
    id = resolve(id);
    document.querySelectorAll(".dock-btn[data-win]").forEach((b) => {
      const wid = resolve(b.dataset.win);
      const on = wid === id || (id === "sessions" && wid === "sessions");
      b.classList.toggle("on", on);
      b.classList.toggle("open", on);
    });
  }

  function openWin(id) {
    id = resolve(id);
    const target = document.querySelector(`.win[data-win="${id}"]`);
    if (!target) return null;
    document.querySelectorAll(".win[data-win]").forEach((win) => {
      const on = win.dataset.win === id;
      win.classList.toggle("minimized", !on);
      win.classList.toggle("focused", on);
      win.classList.toggle("pane", on);
      win.setAttribute("aria-hidden", on ? "false" : "true");
      win.style.left = "";
      win.style.top = "";
      win.style.width = "";
      win.style.height = "";
      delete win.dataset.maxed;
    });
    syncDock(id);
    saveFocus(id);
    window.dispatchEvent(new CustomEvent("mag:win-open", { detail: { id } }));
    requestAnimationFrame(() => {
      window.dispatchEvent(new CustomEvent("mag:win-resize", { detail: { id } }));
    });
    return target;
  }

  function closeWin(_id) {
    if (typeof window.magOpenTab === "function") window.magOpenTab("home");
    else openWin("home");
  }

  function focusWin(win) {
    if (win?.dataset?.win) openWin(win.dataset.win);
  }

  function resetLayout() {
    try {
      localStorage.removeItem(STORAGE);
      localStorage.removeItem("mag_cli_wins_v1");
      localStorage.removeItem("mag_cli_wins_v2");
      localStorage.removeItem("mag_cli_wins_v3");
      localStorage.removeItem("mag_cli_wins_v4");
      localStorage.removeItem("mag_cli_wins_v5");
      localStorage.removeItem("mag_cli_wins_v6");
    } catch {
      /* ignore */
    }
    openWin("home");
  }

  function wireChrome(win) {
    win.querySelectorAll(".win-min, .win-max, .win-close, .win-resize").forEach((el) => {
      el.hidden = true;
    });
    const bar = win.querySelector(".win-titlebar");
    if (bar) bar.classList.add("tab-bar");
  }

  function ensureTopActions() {
    /* catch-up / refresh already in header */
  }

  function refreshTopStatus() {
    // Quotes owned by app.js (MAG_QUOTES). Do not overwrite with status junk.
    const q = document.getElementById("cliQuote");
    if (q && !q.dataset.seeded && q.textContent.trim() === "…") {
      q.innerHTML =
        '<span class="q-text">“Feed the Mag what matters. It grows with you.”</span>';
      q.dataset.seeded = "1";
    }
  }

  function initialFocusFromUrl() {
    try {
      const params = new URLSearchParams(window.location.search);
      const q = (params.get("tab") || params.get("view") || "").trim().toLowerCase();
      if (q === "desk" || q === "chat") return "chat";
      if (q === "office" || q === "home" || q === "map") return "home";
      if (q === "days" || q === "sessions") return "sessions";
      if (q) return resolve(q);
      const hash = (window.location.hash || "").replace(/^#/, "").trim().toLowerCase();
      if (hash === "desk" || hash === "chat") return "chat";
      if (hash === "home" || hash === "office") return "home";
      if (hash === "days" || hash === "sessions") return "sessions";
      if (hash) return resolve(hash);
    } catch {
      /* ignore */
    }
    return null;
  }

  function initWindows() {
    document.body.classList.add("cli", "desk-tabs");
    ensureTopActions();
    refreshTopStatus();
    setInterval(refreshTopStatus, 60000);

    document.querySelectorAll(".win[data-win]").forEach(wireChrome);

    document.querySelectorAll(".dock-btn[data-win], [data-dashboard-view], [data-dashboard-default]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = resolve(btn.dataset.win || btn.dataset.dashboardView || btn.dataset.dashboardDefault);
        if (typeof window.magOpenTab === "function") window.magOpenTab(id);
        else openWin(id);
        const more = btn.closest("details.dock-more");
        if (more) more.open = false;
      });
    });

    // Status lab instrument buttons
    document.querySelectorAll("[data-bury]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-bury");
        if (typeof window.magOpenTab === "function") window.magOpenTab(id);
        else openWin(id);
      });
    });

    let focus = initialFocusFromUrl() || loadFocus();
    if (!PRIMARY.has(focus) && !document.querySelector(`.win[data-win="${focus}"]`)) {
      focus = "home";
    }
    // Semantic deep links may target a supporting view directly. Keep the
    // primary set for persistence/navigation, but do not overwrite a real
    // requested window during DOMContentLoaded.
    openWin(focus);
    // app.js calls setTab(parseInitialTab()) after bind — avoid double desk init/polls
  }

  window.magWin = {
    open: openWin,
    close: closeWin,
    focus: focusWin,
    init: initWindows,
    reset: resetLayout,
    persist: () =>
      saveFocus(document.querySelector(".win.focused")?.dataset?.win || "home"),
    mode: () => "tabs",
    resolve,
    PRIMARY,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWindows);
  } else {
    initWindows();
  }
})();
