/* Mag Sovereign Shell — Tier 4 chrome MVP */
(function () {
  let editor = null;
  let currentPath = "";

  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(path, opts);
    return r.json();
  }

  async function loadTree(path) {
    const ul = document.getElementById("fileTree");
    ul.innerHTML = "<li class='muted'>Loading…</li>";
    const j = await api("GET", `/api/v1/workspace/tree?path=${encodeURIComponent(path || "")}&depth=3`);
    if (!j.ok) {
      ul.innerHTML = `<li class='muted'>${j.error || "tree error"}</li>`;
      return;
    }
    ul.innerHTML = j.entries
      .filter((e) => e.type === "file")
      .slice(0, 120)
      .map(
        (e) =>
          `<li data-path="${e.path}" title="${e.path}">${e.path.split("/").pop()}</li>`
      )
      .join("");
    ul.querySelectorAll("li[data-path]").forEach((li) => {
      li.addEventListener("click", () => openFile(li.dataset.path));
    });
  }

  async function openFile(path) {
    const j = await api("GET", `/api/v1/workspace/file?path=${encodeURIComponent(path)}`);
    if (!j.ok) {
      document.getElementById("agentOut").textContent = j.error || "open failed";
      return;
    }
    currentPath = j.path;
    document.getElementById("openPath").textContent = j.path;
    document.getElementById("btnSave").disabled = false;
    if (editor) editor.setValue(j.text || "");
  }

  async function saveFile() {
    if (!currentPath || !editor) return;
    const j = await api("POST", "/api/v1/workspace/file", {
      path: currentPath,
      text: editor.getValue(),
    });
    document.getElementById("agentOut").textContent = j.ok
      ? `Saved ${j.path} (${j.bytes} bytes)`
      : j.error || "save failed";
  }

  async function runAgent() {
    const goal = document.getElementById("agentGoal").value.trim();
    if (!goal) return;
    const out = document.getElementById("agentOut");
    out.textContent = "Running Mag agent turn…";
    const j = await api("POST", "/api/v1/agent", {
      goal,
      session_id: "sovereign-shell",
      provider: document.getElementById("agentProvider").value,
    });
    out.textContent = JSON.stringify(j, null, 2).slice(0, 12000);
  }

  async function runAutopilot() {
    const out = document.getElementById("autopilotOut");
    out.textContent = "Running autopilot…";
    const j = await api("POST", "/api/v1/autopilot", { queue_improve: true, governor: true });
    out.textContent = JSON.stringify(j, null, 2).slice(0, 8000);
  }

  require.config({
    paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" },
  });
  require(["vs/editor/editor.main"], function () {
    editor = monaco.editor.create(document.getElementById("editor"), {
      value: "# Mag Sovereign Shell\n# Open a file from the tree, or run agent on the right.\n",
      language: "markdown",
      theme: "vs-dark",
      automaticLayout: true,
      fontSize: 13,
      minimap: { enabled: false },
    });
    loadTree("memory");
  });

  document.getElementById("btnTreeRoot").addEventListener("click", () => loadTree("memory"));
  document.getElementById("btnTreeMag").addEventListener("click", () => loadTree(""));
  document.getElementById("btnSave").addEventListener("click", saveFile);
  document.getElementById("btnAgentRun").addEventListener("click", runAgent);
  document.getElementById("btnAutopilot").addEventListener("click", runAutopilot);
})();
