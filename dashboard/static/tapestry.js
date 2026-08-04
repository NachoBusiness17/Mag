/**
 * Mag Tapestry — 3D residual graph (usable inspect, auto-frame, easy pick).
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const PALETTE = {
  accent: 0xff2d95,
  accent2: 0x00f0ff,
  warn: 0xffc857,
  residual: 0xc89bff,
  muted: 0x4a2460,
  object: 0xe8fff6,
};

const KIND_HEX = {
  root: PALETTE.warn,
  session: PALETTE.object,
  turn: PALETTE.accent2,
  subsession: 0x7cffc8,
  run: 0xff9f43,
  lattice: 0x3d5a80,
  theme: PALETTE.accent,
  doc: PALETTE.residual,
  hierarchy: PALETTE.accent2,
  history: PALETTE.residual,
  affinity: PALETTE.accent,
  thread: 0x7cffc8,
  run_edge: 0xff9f43,
  lattice_chain: 0x3d5a80,
  spatial: 0x6ea8fe,
  residual: PALETTE.warn,
  unknown: PALETTE.muted,
};

const KIND_LABEL = {
  root: "Chain tip",
  session: "Workday (bead)",
  turn: "Summary bullet",
  subsession: "Operator turn",
  run: "Orchestrator run",
  lattice: "Verkle leaf",
  theme: "Theme cluster",
  doc: "Project doc",
};

function colorForS(S) {
  if (S < -3) return new THREE.Color(PALETTE.warn);
  if (S < -0.5) return new THREE.Color(PALETTE.accent);
  if (S < 0.5) return new THREE.Color(PALETTE.accent2);
  if (S < 1.2) return new THREE.Color(0xa0b8c8);
  return new THREE.Color(0xff3d5a);
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatNodeHtml(ud, { short = false } = {}) {
  const meta = ud.meta || {};
  const kindL = KIND_LABEL[ud.kind] || ud.kind || "node";
  const lines = [
    `<div class="vis-h">${escapeHtml(ud.label || ud.id || "node")}</div>`,
    `<div class="muted">${escapeHtml(kindL)}</div>`,
  ];
  if (meta.layman_what) {
    lines.push(
      `<div class="layman-block"><strong>What</strong> ${escapeHtml(meta.layman_what)}</div>`
    );
  }
  if (!short && meta.layman_why) {
    lines.push(
      `<div class="layman-block"><strong>Why it matters</strong> ${escapeHtml(meta.layman_why)}</div>`
    );
  }
  if (!short && meta.layman_where) {
    lines.push(
      `<div class="layman-block muted sm"><strong>Source</strong> <span class="mono">${escapeHtml(meta.layman_where)}</span></div>`
    );
  }
  if (meta.theme) {
    lines.push(`<div class="tap-chip">${escapeHtml(meta.theme)}</div>`);
  }
  if (meta.end_minute) {
    lines.push(`<div class="muted mono">${escapeHtml(String(meta.end_minute).slice(0, 16))}</div>`);
  }
  if (meta.blurb) {
    lines.push(`<p class="tap-blurb">${escapeHtml(String(meta.blurb).slice(0, short ? 140 : 400))}</p>`);
  }
  if (meta.text) {
    lines.push(`<p class="tap-blurb">${escapeHtml(String(meta.text).slice(0, short ? 120 : 400))}</p>`);
  }
  if (!short && Array.isArray(meta.bullets) && meta.bullets.length) {
    lines.push("<ul class='tap-bullets'>");
    for (const b of meta.bullets.slice(0, 6)) {
      lines.push(`<li>${escapeHtml(String(b).slice(0, 160))}</li>`);
    }
    lines.push("</ul>");
  }
  if (meta.session_id && !short) {
    lines.push(
      `<div class="muted mono">session ${escapeHtml(String(meta.session_id).slice(0, 18))}…</div>`
    );
  }
  if (meta.path) {
    lines.push(`<div class="muted mono">${escapeHtml(meta.path)}</div>`);
  }
  if (meta.n_days != null) {
    lines.push(`<div class="muted">${escapeHtml(String(meta.n_days))} days in theme</div>`);
  }
  if (meta.n_leaves != null) {
    lines.push(`<div class="muted">${escapeHtml(String(meta.n_leaves))} Verkle leaves</div>`);
  }
  if (meta.root) {
    lines.push(`<div class="muted mono">tip ${escapeHtml(String(meta.root).slice(0, 14))}…</div>`);
  }
  if (meta.parent && !short) {
    lines.push(`<div class="muted mono">parent ${escapeHtml(meta.parent)}</div>`);
  }
  if (ud.S != null && ud.S !== "" && !short) {
    lines.push(`<div class="muted">tension proxy S=${Number(ud.S).toFixed(2)}</div>`);
  }
  if (!short && meta.session_id) {
    lines.push(
      `<p class="muted">Open <b>DAY</b> for full residual · id pinned above.</p>`
    );
  }
  return lines.join("");
}

export class TapestryView {
  constructor(canvas, captionEl, metaEl, hoverEl, hoverRailEl) {
    this.canvas = canvas;
    this.captionEl = captionEl;
    this.metaEl = metaEl;
    // floating tooltip (optional; prefer hoverRail for stable layout)
    this.hoverEl = hoverEl || null;
    this.hoverRailEl =
      hoverRailEl ||
      (typeof document !== "undefined" ? document.getElementById("tapHoverRail") : null);
    this.pack = null;
    this.nodeMeshes = new Map();
    this.edgeLines = [];
    this.pickables = [];
    this._raf = 0;
    this._running = false;
    this.clock = new THREE.Clock();
    this._hoverId = null;
    this._pinnedId = null;
    this._spin = 0.012; // slow; pauses on interaction
    this._drag = false;
    this.showLattice = true;

    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x050a08, 1);

    this.scene = new THREE.Scene();
    // Light fog — dense fog + far camera left a dead black band above the helix
    this.scene.fog = new THREE.FogExp2(0x050a08, 0.008);

    this.camera = new THREE.PerspectiveCamera(48, 1, 0.05, 500);
    this.camera.position.set(8, 6, 14);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 1;
    this.controls.maxDistance = 200;
    this.controls.target.set(0, 0, 0);
    this.controls.addEventListener("start", () => {
      this._drag = true;
      this._spin = 0;
      this._userMoved = true;
    });
    this.controls.addEventListener("end", () => {
      this._drag = false;
      setTimeout(() => {
        if (!this._drag) this._spin = 0.006;
      }, 1600);
    });

    this.root = new THREE.Group();
    this.scene.add(this.root);

    const amb = new THREE.AmbientLight(0x99bbbb, 0.65);
    const key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(5, 10, 6);
    const rim = new THREE.PointLight(PALETTE.accent2, 0.45, 50);
    rim.position.set(-5, 3, -4);
    this.scene.add(amb, key, rim);

    this.raycaster = new THREE.Raycaster();
    // larger pick tolerance for small spheres
    this.raycaster.params.Line = { threshold: 0.2 };
    this.pointer = new THREE.Vector2();
    this._ptrDown = null;
    this._lastW = 0;
    this._lastH = 0;
    this._userMoved = false;

    this._onResize = () => this.resize({ fromWindow: true });
    this._onDown = (ev) => {
      this._ptrDown = { x: ev.clientX, y: ev.clientY, t: Date.now() };
    };
    this._onUp = (ev) => {
      if (!this._ptrDown) return;
      const dx = ev.clientX - this._ptrDown.x;
      const dy = ev.clientY - this._ptrDown.y;
      const dt = Date.now() - this._ptrDown.t;
      this._ptrDown = null;
      // treat as click if short + little movement
      if (dt < 500 && dx * dx + dy * dy < 36) {
        this._pick(ev, { pin: true });
      }
    };
    this._onMove = (ev) => this._hover(ev);
    this._onLeave = () => this._hideHover();

    window.addEventListener("resize", this._onResize);
    canvas.addEventListener("pointerdown", this._onDown);
    canvas.addEventListener("pointerup", this._onUp);
    canvas.addEventListener("pointermove", this._onMove);
    canvas.addEventListener("pointerleave", this._onLeave);

    // Reliable size when dock/CSS flex settles (window.resize alone is not enough)
    this._wrap =
      canvas.closest(".tap-canvas-wrap") || canvas.parentElement || canvas;
    if (typeof ResizeObserver !== "undefined") {
      this._ro = new ResizeObserver(() => {
        this.resize({ fromObserver: true });
      });
      this._ro.observe(this._wrap);
    }
    this.resize({ forceFit: true });
  }

  _measure() {
    const wrap =
      this.canvas.closest(".tap-canvas-wrap") ||
      this._wrap ||
      this.canvas.parentElement ||
      this.canvas;
    const rect = wrap.getBoundingClientRect();
    let w = Math.floor(rect.width);
    let h = Math.floor(rect.height);
    // Fallback if layout not ready — use stage
    if (w < 8 || h < 8) {
      const stage = this.canvas.closest(".days-tap, .tap-stage");
      if (stage) {
        const sr = stage.getBoundingClientRect();
        w = Math.max(w, Math.floor(sr.width * 0.7));
        h = Math.max(h, Math.floor(sr.height - 8));
      }
    }
    w = Math.max(8, w);
    h = Math.max(8, h);
    return { w, h, wrap };
  }

  resize(opts = {}) {
    const { w, h } = this._measure();
    const sizeChanged =
      Math.abs(w - (this._lastW || 0)) > 2 || Math.abs(h - (this._lastH || 0)) > 2;
    this.canvas.style.width = "100%";
    this.canvas.style.height = "100%";
    // Drop obsolete HTML width/height attrs that lock 800×400
    this.canvas.removeAttribute("width");
    this.canvas.removeAttribute("height");
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / Math.max(h, 1);
    this.camera.updateProjectionMatrix();
    this._lastW = w;
    this._lastH = h;

    const nodes = this.pack?.connections?.nodes;
    const shouldFit =
      nodes?.length &&
      (opts.forceFit ||
        this._needsRefit ||
        (sizeChanged && !this._userMoved) ||
        (opts.fromObserver && !this._userMoved && sizeChanged));
    if (shouldFit) {
      this.fitCamera(nodes);
      this._needsRefit = false;
    }
  }

  clear() {
    this.pickables = [];
    this.nodeMeshes.clear();
    this.edgeLines = [];
    while (this.root.children.length) {
      const o = this.root.children.pop();
      o.traverse((c) => {
        if (c.geometry) c.geometry.dispose();
        if (c.material) {
          if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
          else c.material.dispose();
        }
      });
    }
  }

  fitCamera(nodes) {
    if (!nodes?.length) return;
    // Always re-measure — flex layout often settles after first paint
    const { w, h } = this._measure();
    if (w >= 8 && h >= 8) {
      this.canvas.style.width = "100%";
      this.canvas.style.height = "100%";
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.setSize(w, h, false);
      this.camera.aspect = w / h;
      this._lastW = w;
      this._lastH = h;
    }

    const box = new THREE.Box3();
    if (this.nodeMeshes && this.nodeMeshes.size) {
      for (const mesh of this.nodeMeshes.values()) {
        box.expandByObject(mesh);
      }
    } else {
      for (const n of nodes) {
        box.expandByPoint(new THREE.Vector3(n.x || 0, n.y || 0, n.z || 0));
      }
    }
    if (box.isEmpty()) return;

    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    box.getCenter(center);
    box.getSize(size);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const radius = Math.max(sphere.radius, 2.5);

    // Narrower FOV on wide stages = less pancake / fisheye squash
    const aspect = Math.max(0.4, this.camera.aspect || 1);
    this.camera.fov = aspect > 1.8 ? 36 : aspect > 1.4 ? 38 : aspect > 1.1 ? 40 : 44;
    this.camera.updateProjectionMatrix();

    const vHalf = (this.camera.fov * Math.PI) / 360;
    const hHalf = Math.atan(Math.tan(vHalf) * aspect);
    // Leave margin so the cluster breathes (fill was too aggressive → felt squashed)
    const fill = 0.78;
    const distV = size.y / 2 / (Math.tan(vHalf) * fill);
    const distH = size.x / 2 / (Math.tan(hHalf) * fill);
    const distD = size.z / 2 / (Math.tan(hHalf) * fill);
    const distSphere = radius / (Math.sin(vHalf) * fill);
    let dist = Math.max(distV, distH, distD, distSphere, 4);
    dist = Math.min(dist, radius * 3.8);

    // True three-quarter view — height reads clearly, less flat-on squash
    this.controls.target.copy(center);
    this.camera.up.set(0, 1, 0);
    this.camera.position.set(
      center.x + dist * 0.62,
      center.y + dist * 0.48,
      center.z + dist * 0.72
    );
    this.camera.near = Math.max(0.05, dist / 80);
    this.camera.far = Math.max(400, dist * 25);
    this.camera.lookAt(center);
    this.camera.updateProjectionMatrix();

    this.controls.minDistance = Math.max(1, dist * 0.12);
    this.controls.maxDistance = Math.max(100, dist * 8);
    // Sync OrbitControls spherical state from camera (critical or lookAt is undone)
    this.controls.update();

    if (this.scene.fog) {
      this.scene.fog.density = Math.min(0.012, 0.2 / Math.max(dist, 6));
    }
    this._lastFitCenter = center.clone();
    this._lastFitDist = dist;
    this._userMoved = false;
    this._spin = 0; // no spin until user idles
    setTimeout(() => {
      if (!this._userMoved && !this._drag) this._spin = 0.005;
    }, 2500);
  }

  setPack(pack) {
    this.pack = pack || {};
    this._pinnedId = null;
    this._needsRefit = true;
    this._userMoved = false;
    try {
      this.clear();
    } catch (_) {
      /* ignore */
    }
    // Reset spin group so fit is against identity
    if (this.root) this.root.rotation.set(0, 0, 0);

    const nodes = pack?.connections?.nodes || [];
    const edges = pack?.connections?.edges || [];
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));

    // Ground under content
    let minY = 0;
    let maxR = 4;
    for (const n of nodes) {
      const y = Number(n.y) || 0;
      if (y < minY) minY = y;
      const r = Math.hypot(Number(n.x) || 0, Number(n.z) || 0);
      if (r > maxR) maxR = r;
    }
    const span = Math.max(16, maxR * 2.4);
    try {
      const grid = new THREE.GridHelper(span, 24, 0x1a4a38, 0x0d2018);
      grid.position.y = minY - 1.4;
      this.root.add(grid);
    } catch (_) {
      /* ignore grid failure */
    }

    let drawn = 0;
    for (const e of edges) {
      if (drawn++ > 1400) break;
      const a = byId[e.source];
      const b = byId[e.target];
      if (!a || !b) continue;
      const isLattice =
        a.kind === "lattice" ||
        b.kind === "lattice" ||
        e.kind === "lattice" ||
        e.kind === "lattice_chain";
      if (isLattice && !this.showLattice) continue;
      const col = new THREE.Color(KIND_HEX[e.kind] || KIND_HEX.unknown);
      const w = e.weight != null ? e.weight : 0.5;
      const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(a.x, a.y, a.z),
        new THREE.Vector3(b.x, b.y, b.z),
      ]);
      const mat = new THREE.LineBasicMaterial({
        color: col,
        transparent: true,
        opacity: isLattice
          ? Math.min(0.35, 0.08 + 0.25 * Math.min(1, w))
          : Math.min(0.75, 0.12 + 0.55 * Math.min(1, w)),
      });
      const line = new THREE.Line(geo, mat);
      line.userData = { lattice: isLattice };
      this.root.add(line);
      this.edgeLines.push(line);
    }

    for (const n of nodes) {
      if (n.kind === "lattice" && !this.showLattice) continue;
      const r =
        n.kind === "root"
          ? 0.38
          : n.kind === "session"
            ? 0.28
            : n.kind === "theme"
              ? 0.22
              : n.kind === "subsession"
                ? 0.16
                : n.kind === "run"
                  ? 0.14
                  : n.kind === "lattice"
                    ? 0.09
                    : n.kind === "doc"
                      ? 0.2
                      : 0.12;
      const isGhost = n.kind === "lattice" || n.layer === "lattice";
      const col =
        n.kind === "session"
          ? colorForS(n.S ?? 0)
          : new THREE.Color(KIND_HEX[n.kind] || KIND_HEX.unknown);
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(r, 20, 16),
        new THREE.MeshStandardMaterial({
          color: col,
          emissive: col,
          emissiveIntensity: isGhost ? 0.15 : 0.4,
          metalness: 0.15,
          roughness: 0.4,
          transparent: isGhost,
          opacity: isGhost ? 0.28 : 1,
        })
      );
      mesh.position.set(n.x || 0, n.y || 0, n.z || 0);
      // invisible larger hit shell for easier pick
      const hit = new THREE.Mesh(
        new THREE.SphereGeometry(Math.max(r * 2.4, 0.28), 12, 10),
        new THREE.MeshBasicMaterial({
          transparent: true,
          opacity: 0,
          depthWrite: false,
        })
      );
      hit.position.copy(mesh.position);
      const ud = {
        id: n.id,
        label: n.label,
        kind: n.kind,
        S: n.S,
        meta: n.meta || {},
      };
      mesh.userData = ud;
      hit.userData = ud;
      this.root.add(mesh);
      this.root.add(hit);
      this.nodeMeshes.set(n.id, mesh);
      this.pickables.push(hit, mesh);
    }

    // Fit only after meshes exist (expandByObject)
    this.resize({ forceFit: true });

    const st = pack?.stats || {};
    if (this.metaEl) {
      this.metaEl.textContent = `${st.n_days ?? 0} days · ${st.n_nodes ?? 0} nodes · ${
        st.n_edges ?? 0
      } edges · hover / click for context`;
    }
    this._showDefaultInspect();
    this.start();

    // Layout flex often settles after first paint — force two more fits
    requestAnimationFrame(() => this.resize({ forceFit: true }));
    setTimeout(() => this.resize({ forceFit: true }), 120);
    setTimeout(() => this.resize({ forceFit: true }), 400);
  }

  _showDefaultInspect() {
    if (!this.captionEl) return;
    const pack = this.pack;
    this.captionEl.innerHTML = `
      <div class="vis-h">${escapeHtml(pack?.english?.headline || "Tapestry of filed workdays")}</div>
      <p class="muted">${escapeHtml(
        pack?.english?.blurb ||
          "Each sphere is a bead (day), theme, ask, or doc. Hover for a label. Click to pin context here."
      )}</p>
      <ul class="tap-legend">
        <li><span class="dot session"></span> Workday bead</li>
        <li><span class="dot theme"></span> Theme</li>
        <li><span class="dot turn"></span> Ask / bullet</li>
        <li><span class="dot doc"></span> Doc / tip</li>
      </ul>
      <p class="muted">Drag to orbit · scroll to zoom · spin pauses while you move.</p>
    `;
  }

  _rayHits(ev) {
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return [];
    this.pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    return this.raycaster.intersectObjects(this.pickables, false);
  }

  _hideHover() {
    this._hoverId = null;
    if (this.hoverEl) {
      this.hoverEl.hidden = true;
      this.hoverEl.innerHTML = "";
    }
    this.canvas.style.cursor = "grab";
  }

  _setInspect(ud, { pin = false } = {}) {
    if (!ud) return;
    if (this.captionEl) {
      this.captionEl.innerHTML = formatNodeHtml(ud, { short: false });
    }
    if (pin) this._pinnedId = ud.id;
  }

  _setHoverRail(ud) {
    const el = this.hoverRailEl;
    if (!el) return;
    if (!ud) {
      el.innerHTML = `<p class="muted">Move over a node…</p>`;
      return;
    }
    el.innerHTML =
      formatNodeHtml(ud, { short: true }) +
      `<p class="muted rail-hint">Click graph to pin here ↓</p>`;
  }

  _hover(ev) {
    if (ev.buttons) return;
    const hits = this._rayHits(ev);
    if (!hits.length) {
      this._hideHover();
      this._setHoverRail(null);
      // pinned caption stays put — no restore thrash
      return;
    }
    const ud = hits[0].object.userData || {};
    const id = ud.id || "";
    this.canvas.style.cursor = "pointer";
    if (id !== this._hoverId) {
      this._hoverId = id;
      // Right rail only — never resize the graph by rewriting pinned caption
      this._setHoverRail(ud);
      // Keep floating tooltip off in rail mode (avoids layout jump)
      if (this.hoverEl && !this.hoverEl.classList.contains("tap-hover-off")) {
        this.hoverEl.innerHTML = formatNodeHtml(ud, { short: true });
        this.hoverEl.hidden = false;
      } else if (this.hoverEl) {
        this.hoverEl.hidden = true;
      }
    }
    // no absolute positioning of hover over canvas when rail is present
    if (this.hoverEl && !this.hoverRailEl && !this.hoverEl.classList.contains("tap-hover-off")) {
      const rect = this.canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left + 12;
      const y = ev.clientY - rect.top + 12;
      this.hoverEl.style.left = `${Math.min(x, rect.width - 200)}px`;
      this.hoverEl.style.top = `${Math.min(y, rect.height - 60)}px`;
    }
  }

  setLatticeVisible(on) {
    this.showLattice = !!on;
    if (this.pack) this.setPack(this.pack);
  }

  focusSession(sessionId) {
    if (!sessionId || !this.nodeMeshes) return false;
    const sid = String(sessionId);
    let found = null;
    for (const [id, mesh] of this.nodeMeshes) {
      const ms = mesh.userData?.meta?.session_id;
      if (ms && String(ms) === sid) {
        found = { id, mesh, ud: mesh.userData };
        break;
      }
      if (id === sid || String(id).includes(sid.slice(0, 8))) {
        found = { id, mesh, ud: mesh.userData };
      }
    }
    if (!found) return false;
    this._highlightFocus(found.id, found.ud);
    this._setInspect(found.ud, { pin: true });
    return true;
  }

  _highlightFocus(focus, ud) {
    const parent = ud?.meta?.parent;
    const sid = ud?.meta?.session_id;
    const focusDay =
      ud?.kind === "session" ? focus : parent?.startsWith("day:") ? parent : null;
    for (const [id, mesh] of this.nodeMeshes) {
      const m = mesh.userData;
      const mp = m.meta?.parent;
      const msid = m.meta?.session_id;
      const sameTree =
        id === focus ||
        mp === focus ||
        parent === id ||
        (focusDay && (id === focusDay || mp === focusDay)) ||
        (sid && msid === sid);
      const isLattice = m.kind === "lattice";
      if (isLattice && !this.showLattice) continue;
      mesh.material.emissiveIntensity = sameTree ? (isLattice ? 0.35 : 0.95) : isLattice ? 0.08 : 0.12;
      mesh.material.opacity = sameTree ? (isLattice ? 0.55 : 1) : isLattice ? 0.12 : 0.22;
      mesh.material.transparent = true;
    }
  }

  _pick(ev, opts = {}) {
    const hits = this._rayHits(ev);
    if (!hits.length) {
      this._pinnedId = null;
      // reset highlight
      for (const [, mesh] of this.nodeMeshes) {
        mesh.material.emissiveIntensity = 0.4;
        mesh.material.opacity = 1;
        mesh.material.transparent = false;
      }
      this._showDefaultInspect();
      return;
    }
    const ud = hits[0].object.userData || {};
    this._setInspect(ud, { pin: !!opts.pin });
    this._setHoverRail(ud);
    if (this.hoverEl && !this.hoverEl.classList.contains("tap-hover-off")) {
      this.hoverEl.innerHTML = formatNodeHtml(ud, { short: true });
      this.hoverEl.hidden = false;
    }

    const focus = ud.id;
    this._highlightFocus(focus, ud);

    // Notify desk (Days merge) of session pick
    const sid = ud.meta?.session_id || (ud.kind === "session" ? ud.id : null);
    if (sid && opts.pin) {
      window.dispatchEvent(
        new CustomEvent("mag:tapestry-session", { detail: { session_id: sid, ud } })
      );
    }
  }

  start() {
    if (this._running) return;
    this._running = true;
    const loop = () => {
      if (!this._running) return;
      this._raf = requestAnimationFrame(loop);
      this.controls.update();
      if (this._spin && !this._drag) {
        this.root.rotation.y += this._spin * 0.016;
      }
      this.renderer.render(this.scene, this.camera);
    };
    loop();
  }

  stop() {
    this._running = false;
    if (this._raf) cancelAnimationFrame(this._raf);
  }

  dispose() {
    this.stop();
    window.removeEventListener("resize", this._onResize);
    this.canvas.removeEventListener("pointerdown", this._onDown);
    this.canvas.removeEventListener("pointerup", this._onUp);
    this.canvas.removeEventListener("pointermove", this._onMove);
    this.canvas.removeEventListener("pointerleave", this._onLeave);
    if (this._ro) {
      try {
        this._ro.disconnect();
      } catch (_) {
        /* ignore */
      }
      this._ro = null;
    }
    this.clear();
    this.renderer.dispose();
    this.controls.dispose();
  }
}

window.MagTapestry = TapestryView;
