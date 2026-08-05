/* Mag Sovereign Shell — curated tree, SSE agent stream (low RAM) */
(function () {
  let editor = null;
  let currentPath = "";
  let streamAbort = null;

  const QUICK = [
    { label: "Context pack", path: "memory/context_pack_latest.md" },
    { label: "Brief", path: "memory/briefs/latest.md" },
    { label: "Bonds", path: "memory/bonds_active.md" },
    { label: "Todo queue", path: "queue/todo.md" },
    { label: "Operator card", path: "docs/ref/OPERATOR_CARD.md" },
    { label: "Framework load", path: "docs/FRAMEWORK_LOAD.md" },
    { label: "Mesh integration brief", path: "memory/research_packs/mesh_forest/INTEGRATION_BRIEF.md" },
    { label: "Nervous system", path: "memory/nervous_system.json" },
  ];

  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(path, opts);
    return r.json();
  }

  function renderQuickFiles() {
    const host = document.getElementById("quickFiles");
    if (!host) return;
    host.innerHTML = QUICK.map(
      (q) => `<button type="button" data-path="${q.path}">${q.label}</button>`
    ).join("");
    host.querySelectorAll("button[data-path]").forEach((btn) => {
      btn.addEventListener("click", () => openFile(btn.dataset.path));
    });
  }

  async function loadTree(path) {
    const ul = document.getElementById("fileTree");
    ul.innerHTML = "<li class='muted'>Loading…</li>";
    const j = await api("GET", `/api/v1/workspace/tree?path=${encodeURIComponent(path || "")}&depth=2`);
    if (!j.ok) {
      ul.innerHTML = `<li class='muted'>${j.error || "tree error"}</li>`;
      return;
    }
    const files = (j.entries || []).filter((e) => e.type === "file").slice(0, 80);
    if (!files.length) {
      ul.innerHTML = "<li class='muted'>No text files here — try Quick files above.</li>";
      return;
    }
    ul.innerHTML = files
      .map((e) => `<li data-path="${e.path}" title="${e.path}">${e.path.split("/").pop()}</li>`)
      .join("");
    ul.querySelectorAll("li[data-path]").forEach((li) => {
      li.addEventListener("click", () => openFile(li.dataset.path));
    });
  }

  async function openFile(path) {
    const j = await api("GET", `/api/v1/workspace/file?path=${encodeURIComponent(path)}`);
    const out = document.getElementById("agentOut");
    if (!j.ok) {
      if (out) out.textContent = j.error || "open failed";
      return;
    }
    currentPath = j.path;
    document.getElementById("openPath").textContent = j.path;
    document.getElementById("btnSave").disabled = false;
    document.getElementById("fidelityNote").textContent =
      `Artifact: ${j.path} — this file is truth; UI is viewport only.`;
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

  async function copyPack() {
    const out = document.getElementById("agentOut");
    try {
      const r = await fetch("/api/v1/context-pack");
      const j = await r.json();
      const paste = j.paste || j.text || "";
      await navigator.clipboard.writeText(paste);
      out.textContent = `Pack copied (${j.chars || paste.length} chars)\n${j.path || "memory/context_pack_latest.md"}`;
    } catch (e) {
      out.textContent = "Copy pack failed: " + (e.message || e);
    }
  }

  async function streamAgent(goal, provider) {
    const out = document.getElementById("agentOut");
    const stopBtn = document.getElementById("btnAgentStop");
    const runBtn = document.getElementById("btnAgentRun");
    out.textContent = "";
    out.classList.add("streaming");
    runBtn.disabled = true;
    stopBtn.disabled = false;

    const ac = new AbortController();
    streamAbort = ac;

    let acc = "";
    try {
      const res = await fetch("/api/v1/agent/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          goal,
          provider,
          session_id: "sovereign-shell",
          reset: false,
        }),
        signal: ac.signal,
      });
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const chunk = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          const line = chunk.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          let ev;
          try {
            ev = JSON.parse(line.slice(5).trim());
          } catch {
            continue;
          }
          if (ev.type === "delta" && typeof ev.text === "string") {
            acc += ev.text;
            out.textContent = acc.slice(-50000);
            out.scrollTop = out.scrollHeight;
          } else if (ev.type === "tool") {
            acc += `\n[tool ${ev.name}]\n`;
            out.textContent = acc.slice(-50000);
          } else if (ev.type === "error") {
            throw new Error(ev.error || "stream error");
          } else if (ev.type === "done") {
            acc = ev.answer || acc;
            out.textContent = acc.slice(-50000);
            if (ev.tools && ev.tools.length) {
              out.textContent += `\n\n— tools: ${ev.tools.length} —`;
            }
          }
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") {
        out.textContent = (acc ? acc + "\n\n" : "") + "Error: " + (e.message || e);
      }
    } finally {
      out.classList.remove("streaming");
      runBtn.disabled = false;
      stopBtn.disabled = true;
      streamAbort = null;
    }
  }

  async function runAgent() {
    const goal = document.getElementById("agentGoal").value.trim();
    if (!goal) return;
    await streamAgent(goal, document.getElementById("agentProvider").value);
  }

  function stopAgent() {
    if (streamAbort) streamAbort.abort();
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
      value: "# Mag Sovereign Shell\n#\n# 1. Pick a Quick file (left) or browse docs/ref\n# 2. Run agent (right) — streams plain text, files artifacts\n# 3. Save edits — truth stays on disk\n",
      language: "markdown",
      theme: "vs-dark",
      automaticLayout: true,
      fontSize: 13,
      minimap: { enabled: false },
    });
    renderQuickFiles();
    loadTree("docs/ref");
  });

  document.getElementById("btnTreeDocs").addEventListener("click", () => loadTree("docs/ref"));
  document.getElementById("btnTreeMemory").addEventListener("click", () => loadTree("memory"));
  document.getElementById("btnTreeQueue").addEventListener("click", () => loadTree("queue"));
  document.getElementById("btnSave").addEventListener("click", saveFile);
  document.getElementById("btnAgentRun").addEventListener("click", runAgent);
  document.getElementById("btnAgentStop").addEventListener("click", stopAgent);
  document.getElementById("btnCopyPack").addEventListener("click", copyPack);
  document.getElementById("btnAutopilot").addEventListener("click", runAutopilot);
})();
