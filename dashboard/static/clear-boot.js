/* Clear UI boot — progressive tabs, no window manager */
(function () {
  function showPanel(name) {
    if (name === "tools") {
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("on", "active"));
      const tools = document.getElementById("panel-tools");
      if (tools) {
        tools.classList.add("on", "active");
      }
      document.querySelectorAll(".nav button[data-tab]").forEach((b) => {
        b.classList.toggle("on", b.dataset.tab === "tools");
      });
      // lazy-load depth panels when tools opened
      if (typeof loadBoard === "function") loadBoard();
      if (typeof loadOperate === "function") loadOperate();
      return;
    }

    document.querySelectorAll(".content > .panel").forEach((p) => {
      p.classList.remove("on", "active");
    });
    // also clear nested panel-tools visibility
    const tools = document.getElementById("panel-tools");
    if (tools) tools.classList.remove("on", "active");

    const el = document.getElementById("panel-" + name);
    if (el) {
      el.classList.add("on", "active");
    }

    document.querySelectorAll(".nav button[data-tab]").forEach((b) => {
      b.classList.toggle("on", b.dataset.tab === name);
    });

    if (name === "home" && typeof loadHome === "function") loadHome();
    if (name === "chat") {
      if (typeof renderChat === "function") renderChat();
      if (typeof refreshEconomy === "function") refreshEconomy();
      setTimeout(() => document.getElementById("chatInput")?.focus(), 40);
    }
    if (name === "sessions" && typeof refresh === "function") {
      /* sessions filled by refresh */
    }
  }

  // Override setTab from app.js (window manager path)
  window.setTab = showPanel;
  window.magOpenTab = showPanel;
  // Disable window manager if present
  window.magWin = {
    open: (id) => {
      showPanel(id === "board" || id === "operate" || id === "orchestrate" || id === "flow" || id === "visual" || id === "tapestry" || id === "verkle" || id === "ingest" || id === "detail" ? "tools" : id);
    },
    focus: () => {},
    init: () => {},
  };

  // Simpler chain renderer if renderVerkleMap exists — restyle nodes after paint
  const orig = window.renderVerkleMap;
  // app.js defines function renderVerkleMap not on window — patch loadHome output via MutationObserver optional

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".nav button[data-tab]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopImmediatePropagation();
        showPanel(btn.dataset.tab);
      });
    });

    document.getElementById("btnHomeChat")?.addEventListener("click", () => showPanel("chat"));
    document.getElementById("btnHomeDays")?.addEventListener("click", () => showPanel("sessions"));

    // Force home first (after app.js bind)
    setTimeout(() => {
      showPanel("home");
      if (typeof loadHome === "function") loadHome();
    }, 50);
  });

  // Also run if already loaded
  if (document.readyState !== "loading") {
    setTimeout(() => {
      document.querySelectorAll(".nav button[data-tab]").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopImmediatePropagation();
          showPanel(btn.dataset.tab);
        });
      });
      showPanel("home");
      if (typeof loadHome === "function") loadHome();
    }, 80);
  }
})();
