/**
 * Mag Visual Map — zoom/pan camera + chambers + Sancho ELI5 layer.
 * What you are looking at is always said in plain English first.
 */
(function (global) {
  const ROLE_COLOR = {
    topic: "#6ea8fe",
    tension: "#f0b429",
    residual: "#c89bff",
    core: "#3dd68c",
    theme: "#00d4c8",
    move: "#9ab8aa",
    loop: "#ff6b6b",
    chart: "#ff9f43",
    default: "#7a8499",
  };

  const ROLE_ELI5 = {
    topic: "The main question this session was about.",
    tension: "Where things felt stuck or pulled two ways.",
    residual: "Important leftovers — do not throw these out for a neat story.",
    core: "Rules you protect (truth, no new throne, local data).",
    theme: "A topic bucket Mag scored in the chat.",
    move: "A concrete next step you can still do.",
    loop: "A habit Mag flagged (planning theater, polish, etc.).",
    chart: "One way of looking (money / secrets / fracture / personal stake).",
  };

  const CHAMBER_SANCHO = {
    connection: {
      title: "Connection map",
      eli5: "This is a map of what this work session was made of — not a verdict.",
      shows: "Circles = ideas, tensions, leftovers, moves. Lines = how they hang together.",
      do: "Click a circle to read the full text. Filter roles on the left. Zoom with wheel or +/−.",
      colors:
        "Blue = question · Gold = tension · Purple = keep · Green = protected · Teal = theme · Red = bad loop",
      proxy: "Layout is spring/heuristic — not measured physics. Use for orientation.",
    },
    signature: {
      title: "Rhythm over time",
      eli5: "How hard the work felt across sessions — like a heartbeat of tension, not a grade.",
      shows: "Dots = sessions over time. Height = tension. Circles on the right = repeating rhythms (Fourier).",
      do: "Hover/select a session dot. Higher = more pull. Active session is brighter.",
      colors: "Teal line = tension path · Gold spokes = rhythm cycles",
      proxy: "PROXY METER: tension_index + Fourier are analysis anchors, not truth scores. Need many sessions to mean much.",
    },
    residual: {
      title: "What must stay",
      eli5: "After you clean up the chat noise, these are the threads still worth keeping.",
      shows: "Only residual / core / rope / topic — the high-fidelity leftovers.",
      do: "Click purple nodes first. Those are ‘do not delete for comfort.’",
      colors: "Purple = residual · Green = protected core · Gold = rope",
      proxy: "Residual list comes from dossier heuristics — verify against your own judgment.",
    },
    belt: {
      title: "Did we fake-close?",
      eli5: "One full walk through your frames can look done and still be twisted.",
      shows: "Ring of frames. ODD (red) = still twisted. EVEN (green) = can rest.",
      do: "If ODD, do not treat the session as a finished mirror. Re-open residual.",
      colors: "Red ring = still twisted · Green = settled enough",
      proxy: "PROXY METER: holonomy is a structural metaphor from frame transport — not a proof you ‘failed.’ Use as a pause signal.",
    },
    attention: {
      title: "Where attention pooled",
      eli5: "A heat map of which observer charts got the most weight this session.",
      shows: "Grid cells: brighter = more mutual weight between charts/themes.",
      do: "Read row/column labels. High personal-rope score is normal — name it, don’t crown it alone.",
      colors: "Brighter blue = more attention mass",
      proxy: "PROXY METER: scores from keyword/chart heuristics in the dossier, not EEG.",
    },
    dual_orbit: {
      title: "Hands vs mirror",
      eli5: "Two tracks around one question: building tools vs understanding yourself.",
      shows: "Two orbits + center question. Beads move on each track.",
      do: "If only Hands is full, you have tools but no reading. If only Mirror, talk without soil.",
      colors: "Teal bead = Hands · Green bead = Mirror · Blue center = question",
      proxy: "Theme buckets are keyword-scored — useful metaphor, not census.",
    },
    spectral: {
      title: "Cluster layout",
      eli5: "Same connections as the map, arranged so related things sit near each other.",
      shows: "Force layout of bonds — clusters are themes of work, not rank.",
      do: "Use when connection map feels tangled. Zoom into a cluster.",
      colors: "Same role colors as connection map",
      proxy: "PROXY: force-directed layout is cosmetic geometry for the same graph.",
    },
  };

  function col(role) {
    return ROLE_COLOR[role] || ROLE_COLOR.default;
  }

  class MagVisual {
    constructor(canvas, captionEl, metersEl, opts = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.captionEl = captionEl;
      this.metersEl = metersEl;
      this.sanchoEl = opts.sanchoEl || null;
      this.zoomLabelEl = opts.zoomLabelEl || null;
      this.onSelect = opts.onSelect || null;
      this.onViewChange = opts.onViewChange || null;
      this.pack = null;
      this.chamber = "connection";
      this.t = 0;
      this.raf = 0;
      this._drag = null; // { mode: 'node'|'pan', ... }
      this._nodes = [];
      this._hover = null;
      this._selected = null;
      this.roleFilter = null;
      // camera: world → screen
      this.cam = { x: 0, y: 0, scale: 1 };
      this._baseLayout = []; // world coords before camera
      this._bind();
      this._resize();
    }

    _bind() {
      window.addEventListener("resize", () => this._resize());

      this.canvas.addEventListener(
        "wheel",
        (e) => {
          e.preventDefault();
          const p = this._ptr(e);
          const factor = e.deltaY > 0 ? 0.9 : 1.12;
          this._zoomAt(p.x, p.y, factor);
        },
        { passive: false }
      );

      this.canvas.addEventListener("pointerdown", (e) => {
        const p = this._ptr(e);
        const hit = this._hit(p.x, p.y);
        if (hit && e.button === 0 && !e.shiftKey) {
          this._selected = hit;
          this._drag = {
            mode: "node",
            id: hit.id,
            lastX: p.x,
            lastY: p.y,
          };
          this.canvas.setPointerCapture(e.pointerId);
          this._emitSelect(hit);
          this._updateSancho(hit);
        } else {
          // pan: empty drag or shift+drag
          this._drag = {
            mode: "pan",
            lastX: p.x,
            lastY: p.y,
          };
          this.canvas.setPointerCapture(e.pointerId);
          this.canvas.style.cursor = "grabbing";
        }
      });

      this.canvas.addEventListener("pointermove", (e) => {
        const p = this._ptr(e);
        if (this._drag?.mode === "node") {
          const n = this._nodes.find((x) => x.id === this._drag.id);
          const b = this._baseLayout.find((x) => x.id === this._drag.id);
          if (n && b) {
            const dx = (p.x - this._drag.lastX) / this.cam.scale;
            const dy = (p.y - this._drag.lastY) / this.cam.scale;
            b.wx += dx;
            b.wy += dy;
            this._drag.lastX = p.x;
            this._drag.lastY = p.y;
            this._applyCamera();
          }
        } else if (this._drag?.mode === "pan") {
          const dx = p.x - this._drag.lastX;
          const dy = p.y - this._drag.lastY;
          this.cam.x += dx;
          this.cam.y += dy;
          this._drag.lastX = p.x;
          this._drag.lastY = p.y;
          this._applyCamera();
          this._zoomLabel();
        } else {
          this._hover = this._hit(p.x, p.y);
          this.canvas.style.cursor = this._hover ? "pointer" : "grab";
        }
      });

      this.canvas.addEventListener("pointerup", () => {
        this._drag = null;
        this.canvas.style.cursor = "grab";
      });
      this.canvas.addEventListener("pointerleave", () => {
        if (!this._drag) this._hover = null;
      });

      // double-click reset zoom on node focus
      this.canvas.addEventListener("dblclick", (e) => {
        const p = this._ptr(e);
        const hit = this._hit(p.x, p.y);
        if (hit) this.focusNode(hit.id);
        else this.resetView();
      });
    }

    _zoomAt(sx, sy, factor) {
      const old = this.cam.scale;
      let next = old * factor;
      next = Math.max(0.25, Math.min(6, next));
      // keep point under cursor stable
      const wx = (sx - this.cam.x) / old;
      const wy = (sy - this.cam.y) / old;
      this.cam.scale = next;
      this.cam.x = sx - wx * next;
      this.cam.y = sy - wy * next;
      this._applyCamera();
      this._zoomLabel();
    }

    zoomIn() {
      this._zoomAt(this.W / 2, this.H / 2, 1.2);
    }
    zoomOut() {
      this._zoomAt(this.W / 2, this.H / 2, 1 / 1.2);
    }

    resetView() {
      this.cam = { x: 0, y: 0, scale: 1 };
      this._layoutChamber();
      this._zoomLabel();
      this._updateSancho(this._selected);
    }

    fitView() {
      if (!this._baseLayout.length) {
        this.resetView();
        return;
      }
      let minX = Infinity,
        minY = Infinity,
        maxX = -Infinity,
        maxY = -Infinity;
      for (const b of this._baseLayout) {
        minX = Math.min(minX, b.wx);
        minY = Math.min(minY, b.wy);
        maxX = Math.max(maxX, b.wx);
        maxY = Math.max(maxY, b.wy);
      }
      const pad = 48;
      const bw = Math.max(40, maxX - minX);
      const bh = Math.max(40, maxY - minY);
      const sx = (this.W - pad * 2) / bw;
      const sy = (this.H - pad * 2) / bh;
      const scale = Math.max(0.25, Math.min(4, Math.min(sx, sy)));
      this.cam.scale = scale;
      this.cam.x = this.W / 2 - ((minX + maxX) / 2) * scale;
      this.cam.y = this.H / 2 - ((minY + maxY) / 2) * scale;
      this._applyCamera();
      this._zoomLabel();
    }

    focusNode(id) {
      const b = this._baseLayout.find((x) => x.id === id);
      if (!b) return;
      this.cam.scale = Math.max(this.cam.scale, 1.4);
      this.cam.x = this.W / 2 - b.wx * this.cam.scale;
      this.cam.y = this.H / 2 - b.wy * this.cam.scale;
      this._applyCamera();
      this.selectById(id);
      this._zoomLabel();
    }

    _zoomLabel() {
      if (this.zoomLabelEl) {
        this.zoomLabelEl.textContent = `${Math.round(this.cam.scale * 100)}%`;
      }
      if (this.onViewChange) this.onViewChange(this.cam);
    }

    _applyCamera() {
      const { x, y, scale } = this.cam;
      this._nodes = this._baseLayout.map((b) => ({
        ...b,
        x: b.wx * scale + x,
        y: b.wy * scale + y,
        r: (b.baseR || 10) * Math.min(1.8, Math.max(0.7, Math.sqrt(scale))),
      }));
    }

    _worldFromScreen(sx, sy) {
      return {
        x: (sx - this.cam.x) / this.cam.scale,
        y: (sy - this.cam.y) / this.cam.scale,
      };
    }

    _emitSelect(hit) {
      if (!this.onSelect || !hit) return;
      const full = this._nodeData(hit.id);
      const edges = this._edgesFor(hit.id);
      this.onSelect({
        node: hit,
        full,
        edges,
        chamber: this.chamber,
        pack: this.pack,
        eli5: ROLE_ELI5[full?.role || hit.role] || "A piece of this session’s living record.",
      });
    }

    _nodeData(id) {
      const nodes =
        this.pack?.chambers?.connection?.nodes ||
        this.pack?.chambers?.[this.chamber]?.nodes ||
        [];
      return nodes.find((n) => n.id === id) || null;
    }

    _edgesFor(id) {
      const edges = this.pack?.chambers?.connection?.edges || [];
      return edges.filter((e) => e.source === id || e.target === id);
    }

    selectById(id) {
      const n = this._nodes.find((x) => x.id === id);
      if (n) {
        this._selected = n;
        this._emitSelect(n);
        this._updateSancho(n);
      }
    }

    setRoleFilter(roles) {
      this.roleFilter = roles;
      this._layoutChamber();
    }

    _ptr(e) {
      const r = this.canvas.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    }

    _hit(x, y) {
      for (let i = this._nodes.length - 1; i >= 0; i--) {
        const n = this._nodes[i];
        const d = Math.hypot(x - n.x, y - n.y);
        if (d < (n.r || 14) + 6) return n;
      }
      return null;
    }

    _resize() {
      const parent = this.canvas.parentElement;
      const w = parent ? parent.clientWidth : 800;
      const h = Math.max(360, parent ? parent.clientHeight : 480);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.canvas.width = w * dpr;
      this.canvas.height = h * dpr;
      this.canvas.style.width = w + "px";
      this.canvas.style.height = h + "px";
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.W = w;
      this.H = h;
      if (this.pack) {
        this._layoutChamber(true);
      }
    }

    setPack(pack) {
      this.pack = pack;
      this.cam = { x: 0, y: 0, scale: 1 };
      this._layoutChamber();
      this._reading();
      this._updateSancho(null);
      this._zoomLabel();
      if (!this.raf) this._loop();
      // fit after first layout
      requestAnimationFrame(() => this.fitView());
    }

    setChamber(id) {
      this.chamber = id;
      this.cam = { x: 0, y: 0, scale: 1 };
      this._layoutChamber();
      this._reading();
      this._updateSancho(this._selected);
      this._zoomLabel();
      requestAnimationFrame(() => this.fitView());
    }

    _updateSancho(hit) {
      if (!this.sanchoEl) return;
      const c = CHAMBER_SANCHO[this.chamber] || CHAMBER_SANCHO.connection;
      const en = this.pack?.english || {};
      let pick = "";
      if (hit) {
        const full = this._nodeData(hit.id) || hit;
        const role = full.role || hit.role;
        pick = `
          <div class="sancho-pick">
            <div class="sancho-pick-h">You clicked: <b>${esc(full.label || hit.label)}</b>
              <span class="role-tag">${esc(role || "?")}</span></div>
            <p>${esc(ROLE_ELI5[role] || "A piece of the living record.")}</p>
            <p class="muted">${esc(full.plain || "No extra text.")}</p>
          </div>`;
      }
      this.sanchoEl.innerHTML = `
        <div class="sancho-mark">SANCHO · ELI5</div>
        <div class="sancho-title">${esc(c.title)}</div>
        <p class="sancho-eli5">${esc(c.eli5)}</p>
        <p><b>What this shows</b> — ${esc(c.shows)}</p>
        <p><b>What to do</b> — ${esc(c.do)}</p>
        <p class="muted"><b>Colors</b> — ${esc(c.colors)}</p>
        ${
          c.proxy
            ? `<p class="sancho-proxy"><b>Proxy honesty</b> — ${esc(c.proxy)}</p>`
            : ""
        }
        ${
          en.move
            ? `<p class="sancho-move"><b>Next move</b> — ${esc(en.move)}</p>`
            : ""
        }
        ${pick}
        <p class="muted sancho-hint">Scroll = zoom · drag empty = pan · drag node = move · double-click = fit/focus · +/− buttons</p>
      `;
    }

    _reading() {
      if (!this.pack || !this.captionEl) return;
      const r = (this.pack.readings || []).find((x) => x.chamber === this.chamber);
      const c = CHAMBER_SANCHO[this.chamber];
      const en = this.pack.english || {};
      this.captionEl.innerHTML = `
        <div class="vis-q">${esc(c?.title || this.chamber)} · ${esc(r?.question || "")}</div>
        <div class="vis-h">${esc(r?.headline || en.headline || "")}</div>
        <div class="vis-b">${esc(r?.body || c?.eli5 || "")}</div>
        <div class="vis-move"><b>Move:</b> ${esc(en.move || "—")}</div>
      `;
      if (this.metersEl) {
        const m = this.pack.meters || {};
        this.metersEl.innerHTML = [
          meter("Tension", m.tension_index != null ? Number(m.tension_index).toFixed(3) : "—"),
          meter("Q", m.Q_proxy != null ? Number(m.Q_proxy).toFixed(0) : "—"),
          meter("Gap", m.gap_proxy != null ? Number(m.gap_proxy).toFixed(3) : "—"),
          meter("Belt", m.holonomy_odd ? "ODD" : "EVEN"),
          meter("Commit", (this.pack.commit || "").slice(0, 8)),
        ].join("");
      }
    }

    _layoutChamber(keepCam = false) {
      if (!this.pack) return;
      const ch = (this.pack.chambers || {})[this.chamber] || {};
      const cx = 0;
      const cy = 0;
      // layout in world space centered at 0,0 — camera places it
      const scale = 80;

      if (
        this.chamber === "connection" ||
        this.chamber === "spectral" ||
        this.chamber === "residual"
      ) {
        let nodes = ch.nodes || this.pack.chambers?.connection?.nodes || [];
        const edges = ch.edges || this.pack.chambers?.connection?.edges || [];
        if (this.roleFilter && this.roleFilter.size) {
          nodes = nodes.filter(
            (n) => n.role === "topic" || this.roleFilter.has(n.role)
          );
        }
        this._edges = edges;
        this._baseLayout = nodes.map((n) => ({
          id: n.id,
          label: n.label,
          role: n.role,
          plain: n.plain,
          wx: (n.x || 0) * scale,
          wy: (n.y || 0) * scale,
          baseR: n.role === "topic" ? 16 : n.role === "residual" ? 12 : 10,
          weight: n.weight || 0.5,
        }));
      } else if (this.chamber === "signature") {
        const pts = ch.points || [];
        this._edges = [];
        this._series = pts;
        this._fourier = ch.fourier || [];
        const n = Math.max(pts.length - 1, 1);
        this._baseLayout = pts.map((p, i) => ({
          id: "p" + i,
          label: p.label || p.theme || String(i),
          role: p.active ? "topic" : "theme",
          plain: `Tension ${p.S} · session ${String(p.session_id || "").slice(0, 8)}`,
          wx: (i / n) * 320 - 160,
          wy: -(p.S || 0) * 140,
          baseR: p.active ? 11 : 7,
          active: p.active,
        }));
      } else if (this.chamber === "belt") {
        const frames = ch.frames || [];
        const n = frames.length || 1;
        this._edges = [];
        this._holonomy = ch;
        this._baseLayout = frames.map((f, i) => {
          const th = (i / n) * Math.PI * 2 - Math.PI / 2;
          return {
            id: "f" + i,
            label: String(f).replace(/_/g, " "),
            role: "chart",
            plain: "A frame Mag held this session.",
            wx: Math.cos(th) * 140,
            wy: Math.sin(th) * 140,
            baseR: 14,
          };
        });
      } else if (this.chamber === "attention") {
        this._attn = ch;
        this._edges = [];
        this._baseLayout = [];
      } else if (this.chamber === "dual_orbit") {
        this._dual = ch;
        this._edges = [];
        this._baseLayout = [
          {
            id: "center",
            label: ch.center || "topic",
            role: "topic",
            plain: "Shared question both tracks orbit.",
            wx: 0,
            wy: 0,
            baseR: 16,
          },
          {
            id: "a",
            label: ch.track_a?.label || "Hands",
            role: "theme",
            plain: (ch.track_a?.items || []).join(", ") || "Build / tools track",
            wx: -150,
            wy: 0,
            baseR: 14,
          },
          {
            id: "b",
            label: ch.track_b?.label || "Mirror",
            role: "core",
            plain: (ch.track_b?.items || []).join(", ") || "Self / meta track",
            wx: 150,
            wy: 0,
            baseR: 14,
          },
        ];
      } else {
        this._baseLayout = [];
        this._edges = [];
      }

      if (!keepCam) {
        // leave cam; fitView often called after
      }
      this._applyCamera();
    }

    _loop() {
      this.t += 0.016;
      this._draw();
      this.raf = requestAnimationFrame(() => this._loop());
    }

    _draw() {
      const ctx = this.ctx;
      const W = this.W;
      const H = this.H;
      if (!W) return;
      const g = ctx.createRadialGradient(W / 2, H / 2, 10, W / 2, H / 2, Math.max(W, H) * 0.7);
      g.addColorStop(0, "#141a24");
      g.addColorStop(1, "#0a0c10");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);

      // camera-aware faint grid
      ctx.save();
      ctx.translate(this.cam.x, this.cam.y);
      ctx.scale(this.cam.scale, this.cam.scale);
      ctx.strokeStyle = "rgba(110,168,254,0.05)";
      ctx.lineWidth = 1 / this.cam.scale;
      const grid = 40;
      for (let x = -400; x <= 400; x += grid) {
        ctx.beginPath();
        ctx.moveTo(x, -400);
        ctx.lineTo(x, 400);
        ctx.stroke();
      }
      for (let y = -400; y <= 400; y += grid) {
        ctx.beginPath();
        ctx.moveTo(-400, y);
        ctx.lineTo(400, y);
        ctx.stroke();
      }
      ctx.restore();

      if (!this.pack) {
        ctx.fillStyle = "#9aa3b2";
        ctx.font = "14px system-ui";
        ctx.fillText("No visual pack — rebuild", 24, 40);
        return;
      }

      // legend chip
      ctx.fillStyle = "rgba(15,17,21,0.75)";
      ctx.fillRect(10, 10, 200, 22);
      ctx.fillStyle = "#9aa3b2";
      ctx.font = "11px system-ui";
      const c = CHAMBER_SANCHO[this.chamber];
      ctx.fillText((c?.title || this.chamber) + " · scroll to zoom", 16, 25);

      if (this.chamber === "attention") this._drawAttention(ctx);
      else if (this.chamber === "signature") this._drawSignature(ctx);
      else if (this.chamber === "belt") this._drawBelt(ctx);
      else if (this.chamber === "dual_orbit") this._drawDual(ctx);
      else this._drawGraph(ctx);

      if (this._hover) {
        const n = this._hover;
        const tx = Math.min(n.x + 16, W - 240);
        const ty = Math.max(n.y - 52, 36);
        ctx.fillStyle = "rgba(20,24,32,0.94)";
        ctx.strokeStyle = col(n.role);
        ctx.lineWidth = 1.5;
        roundRect(ctx, tx, ty, 230, 62, 6);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = "#e8eaed";
        ctx.font = "600 12px system-ui";
        ctx.fillText(n.label || n.id, tx + 10, ty + 18);
        ctx.fillStyle = "#6ea8fe";
        ctx.font = "10px system-ui";
        ctx.fillText(ROLE_ELI5[n.role] || n.role || "", tx + 10, ty + 34);
        ctx.fillStyle = "#9aa3b2";
        ctx.font = "11px system-ui";
        wrapText(ctx, n.plain || "", tx + 10, ty + 50, 210, 12);
      }
    }

    _drawGraph(ctx) {
      const byId = Object.fromEntries(this._nodes.map((n) => [n.id, n]));
      for (const e of this._edges || []) {
        const a = byId[e.source];
        const b = byId[e.target];
        if (!a || !b) continue;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        const kind = e.kind || "";
        ctx.strokeStyle =
          kind === "residual"
            ? "rgba(200,155,255,0.55)"
            : kind === "tension"
              ? "rgba(240,180,41,0.5)"
              : kind === "core"
                ? "rgba(61,214,140,0.45)"
                : "rgba(110,168,254,0.28)";
        ctx.lineWidth = 1 + (e.weight || 0.4) * 2;
        ctx.stroke();
      }
      for (const n of this._nodes) {
        const pulse = n.role === "topic" ? 1 + 0.06 * Math.sin(this.t * 3) : 1;
        const sel = this._selected && this._selected.id === n.id;
        ctx.beginPath();
        ctx.arc(n.x, n.y, (n.r || 10) * pulse * (sel ? 1.12 : 1), 0, Math.PI * 2);
        ctx.fillStyle = col(n.role);
        ctx.globalAlpha = 0.9;
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = sel ? "#fff" : "rgba(255,255,255,0.3)";
        ctx.lineWidth = sel ? 2.5 : 1;
        ctx.stroke();
        // label only if zoomed enough or selected/hover
        const showLabel =
          this.cam.scale >= 0.85 ||
          sel ||
          (this._hover && this._hover.id === n.id) ||
          n.role === "topic";
        if (showLabel) {
          ctx.fillStyle = "#c8d0dc";
          ctx.font = (sel ? "600 " : "") + "11px system-ui";
          ctx.textAlign = "center";
          ctx.fillText(n.label || "", n.x, n.y + (n.r || 10) + 12);
          ctx.textAlign = "left";
        }
      }
    }

    _drawSignature(ctx) {
      const pts = this._nodes;
      if (pts.length > 1) {
        ctx.beginPath();
        pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
        ctx.strokeStyle = "rgba(0,212,200,0.7)";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      const four = this._fourier || [];
      let x = this.W * 0.72;
      let y = this.H * 0.55;
      for (const c of four.slice(0, 6)) {
        const rad = (8 + (c.amp_n || 0) * 40) * Math.min(1.5, this.cam.scale);
        const ang = this.t * (0.4 + c.k * 0.35) + (c.phase || 0);
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(110,168,254,${0.15 + 0.35 * (c.amp_n || 0)})`;
        ctx.stroke();
        const nx = x + Math.cos(ang) * rad;
        const ny = y + Math.sin(ang) * rad;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(nx, ny);
        ctx.strokeStyle = "rgba(240,180,41,0.5)";
        ctx.stroke();
        x = nx;
        y = ny;
      }
      this._drawGraph(ctx);
    }

    _drawBelt(ctx) {
      const cx = this.W / 2 + this.cam.x * 0.02;
      const cy = this.H / 2 + this.cam.y * 0.02;
      const odd = this._holonomy?.odd;
      const r = 100 * this.cam.scale;
      ctx.beginPath();
      ctx.arc(this.W / 2, this.H / 2, Math.max(40, r), 0, Math.PI * 2);
      ctx.strokeStyle = odd ? "rgba(255,107,107,0.75)" : "rgba(61,214,140,0.75)";
      ctx.lineWidth = 4;
      ctx.stroke();
      ctx.fillStyle = odd ? "#ff6b6b" : "#3dd68c";
      ctx.font = "700 16px system-ui";
      ctx.textAlign = "center";
      ctx.fillText(
        odd ? "ODD · still twisted" : "EVEN · can rest",
        this.W / 2,
        this.H / 2 + 4
      );
      ctx.textAlign = "left";
      this._drawGraph(ctx);
    }

    _drawAttention(ctx) {
      const frames = this._attn?.frames || [];
      const M = this._attn?.matrix || [];
      const n = frames.length;
      if (!n) return;
      const cell = Math.min(48, (Math.min(this.W, this.H) - 100) / n) * this.cam.scale;
      const ox = this.W / 2 - (cell * n) / 2 + this.cam.x * 0.1;
      const oy = this.H / 2 - (cell * n) / 2 + this.cam.y * 0.1;
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          const v = M[i]?.[j] ?? 0;
          ctx.fillStyle = `rgba(110,168,254,${0.12 + v * 0.75})`;
          ctx.fillRect(ox + j * cell, oy + i * cell, cell - 2, cell - 2);
        }
        ctx.fillStyle = "#9aa3b2";
        ctx.font = "10px system-ui";
        ctx.fillText(String(frames[i]).slice(0, 12), ox + i * cell, oy + n * cell + 14);
      }
    }

    _drawDual(ctx) {
      const cx = this.W / 2;
      const cy = this.H / 2;
      const ra = 90 * this.cam.scale;
      const rb = 70 * this.cam.scale;
      const t = this.t;
      ctx.strokeStyle = "rgba(0,212,200,0.35)";
      ctx.beginPath();
      ctx.ellipse(cx, cy, ra * 1.6, ra * 0.7, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.strokeStyle = "rgba(61,214,140,0.35)";
      ctx.beginPath();
      ctx.ellipse(cx, cy, rb * 1.8, rb * 0.65, Math.PI / 5, 0, Math.PI * 2);
      ctx.stroke();
      const ax = cx + Math.cos(t) * ra * 1.6;
      const ay = cy + Math.sin(t) * ra * 0.7;
      const bx = cx + Math.cos(-t * 1.2 + 1) * rb * 1.8;
      const by = cy + Math.sin(-t * 1.2 + 1) * rb * 0.65;
      ctx.fillStyle = "#00d4c8";
      ctx.beginPath();
      ctx.arc(ax, ay, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#3dd68c";
      ctx.beginPath();
      ctx.arc(bx, by, 8, 0, Math.PI * 2);
      ctx.fill();
      this._drawGraph(ctx);
    }
  }

  function meter(k, v) {
    return `<div class="stat"><b>${esc(v)}</b><span>${esc(k)}</span></div>`;
  }
  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }
  function wrapText(ctx, text, x, y, maxW, lh) {
    const words = String(text).split(/\s+/);
    let line = "";
    for (const w of words) {
      const test = line ? line + " " + w : w;
      if (ctx.measureText(test).width > maxW) {
        ctx.fillText(line, x, y);
        line = w;
        y += lh;
      } else line = test;
    }
    if (line) ctx.fillText(line, x, y);
  }

  global.MagVisual = MagVisual;
  global.MAG_CHAMBER_SANCHO = CHAMBER_SANCHO;
  global.MAG_ROLE_ELI5 = ROLE_ELI5;
})(window);
