/* Mag desk — tab shell (primary doors). */
(function () {
  const STORAGE = "mag_cli_wins_v7";
  const LAYOUT_VER = 7;
  const PRIMARY = new Set([
    "home",
    "sessions",
    "diary",
    "story",
    "ideas",
    "chat",
    "status",
    "agents",
    "chronicle",
  ]);
  const ALIAS = {
    office: "home",
    days: "sessions",
    tapestry: "sessions",
    map: "home",
    // story is its own pane (not diary)
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
    openWin("home");
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

  function initWindows() {
    document.body.classList.add("cli", "desk-tabs");
    ensureTopActions();
    refreshTopStatus();
    setInterval(refreshTopStatus, 60000);

    document.querySelectorAll(".win[data-win]").forEach(wireChrome);

    document.querySelectorAll(".dock-btn[data-win]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = resolve(btn.dataset.win);
        if (typeof window.magOpenTab === "function") window.magOpenTab(id);
        else openWin(id);
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

    let focus = loadFocus();
    if (!PRIMARY.has(focus) && !document.querySelector(`.win[data-win="${focus}"]`)) {
      focus = "home";
    }
    // Prefer primary doors on cold start after upgrade
    if (!PRIMARY.has(focus)) focus = "home";
    openWin(focus);
    // app.js loads after this file; defer so magOpenTab can fetch tab data
    queueMicrotask(() => {
      if (typeof window.magOpenTab === "function") window.magOpenTab(focus);
    });
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
