"""Filesystem tools jailed to config.FS_ROOTS.

Manifesto Phase 2 (2026-08-03): diff-based writes + drift detection.
- write_file accepts EITHER `content` (legacy full overwrite) OR
  `search` + `replace` (surgical diff). When a diff is given, the existing
  file must contain `search` exactly once, else the write is rejected with
  an ok=False so the model can re-anchor. This kills whole-file clobbering.
- SHA-256 snapshot guard: if `snapshot` is passed, the current file hash must
  match it (Base + Drift detection - external edits reject the write).

Manifesto Phase 3 (2026-08-03): loop-killers from session mining.
- read_file gains `line_from`/`line_to` (1-indexed) line-range addressing with
  numbered output — kills the hand-rolled numbered-region-dump snippet class.
- write_file auto-verifies `.py` writes via py_compile and returns
  `verified` + `compile_error` (diff tail), plus `changed_from`/`changed_to`
  for diff edits — collapses inspect->patch->verify->compile into one call.
"""
from __future__ import annotations

import hashlib
import py_compile
from pathlib import Path

from config import FS_ROOTS, MAX_TOOL_OUTPUT, ROOT


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    else:
        p = p.resolve()
    roots = [r.resolve() for r in FS_ROOTS]
    if not any(p == r or r in p.parents or p in r.parents or str(p).startswith(str(r)) for r in roots):
        # allow only under roots
        ok = False
        for r in roots:
            try:
                p.relative_to(r)
                ok = True
                break
            except ValueError:
                continue
        if not ok:
            raise PermissionError(f"path outside jail: {p}")
    return p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def list_dir(path: str = ".") -> dict:
    try:
        p = _resolve(path)
        if not p.exists():
            return {"ok": False, "exit_code": 1, "error": f"missing: {p}"}
        if not p.is_dir():
            return {"ok": False, "exit_code": 1, "error": f"not a dir: {p}"}
        names = sorted([x.name + ("/" if x.is_dir() else "") for x in p.iterdir()])
        text = "\n".join(names)[:MAX_TOOL_OUTPUT]
        return {"ok": True, "exit_code": 0, "path": str(p), "entries": names, "output": text}
    except Exception as e:
        return {"ok": False, "exit_code": 1, "error": str(e)}


def read_file(
    path: str,
    max_chars: int = MAX_TOOL_OUTPUT,
    line_from: int | None = None,
    line_to: int | None = None,
) -> dict:
    """Read a text file, optionally a 1-indexed line range.

    `line_from`/`line_to` (either alone) switch to line-range mode: the
    output is numbered ("12: <line>") and the result carries `lines`,
    `total_lines`, and the clamped `line_from`/`line_to` actually returned.
    Overlapping ranges clamp instead of erroring, so the caller can always
    re-read exactly the region a diff write reported as changed.
    """
    try:
        p = _resolve(path)
        if not p.is_file():
            return {"ok": False, "exit_code": 1, "error": f"not a file: {p}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        total = text.count("\n") + (0 if text.endswith("\n") else 1) or 1
        if line_from is None and line_to is None:
            body = text[:max_chars]
            return {
                "ok": True,
                "exit_code": 0,
                "path": str(p),
                "output": body,
                "sha256": _sha256(p),
                "bytes": p.stat().st_size,
                "total_lines": total,
            }
        lo = max(1, line_from or 1)
        hi = total if line_to is None else min(total, max(1, line_to))
        if lo > hi:
            lo, hi = hi, lo
        lines = text.splitlines()
        numbered = [f"{n}: {lines[n-1]}" for n in range(lo, hi + 1) if n <= len(lines)]
        body = "\n".join(numbered)
        if len(body) > max_chars:
            body = body[:max_chars] + f"\n... (clipped, {len(numbered)} lines in range)"
        return {
            "ok": True,
            "exit_code": 0,
            "path": str(p),
            "output": body,
            "lines": numbered,
            "total_lines": total,
            "line_from": lo,
            "line_to": hi,
            "sha256": _sha256(p),
            "bytes": p.stat().st_size,
        }
    except Exception as e:
        return {"ok": False, "exit_code": 1, "error": str(e)}


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_py(path: Path) -> tuple[bool, str]:
    """py_compile a .py file after write. Returns (verified, error_text)."""
    try:
        py_compile.compile(str(path), doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        msg = getattr(e, "msg", None) or str(e)
        return False, f"{path.name}: {msg}"
    except Exception as e:  # noqa: BLE001 - report any compile-time failure
        return False, f"{path.name}: {e}"


def write_file(
    path: str,
    content: str | None = None,
    search: str | None = None,
    replace: str | None = None,
    snapshot: str | None = None,
) -> dict:
    """Write a file, or surgically edit it.

    Manifesto Phase 2 semantics:
      - content only            -> full write (legacy, but discouraged)
      - search + replace        -> diff-based edit; `search` must appear exactly once
      - snapshot provided       -> current on-disk sha256 must match or write is rejected
    Returns ok=False with a precise reason when the edit would clobber or drift.
    """
    try:
        p = _resolve(path)

        # Snapshot drift guard (Base + Drift): reject if the file changed since we read it.
        if snapshot is not None:
            if not p.is_file():
                return {"ok": False, "exit_code": 1, "error": "snapshot given but file missing", "path": str(p)}
            cur = _file_digest(p)
            if cur != snapshot:
                return {
                    "ok": False,
                    "exit_code": 1,
                    "error": "DRIFT: file changed since snapshot (external edit). Re-read before writing.",
                    "path": str(p),
                    "sha256_now": cur,
                    "sha256_snapshot": snapshot,
                }

        if search is not None:
            # diff-based edit
            if not p.is_file():
                return {"ok": False, "exit_code": 1, "error": "search given but file missing (create with content= instead)", "path": str(p)}
            if replace is None:
                return {"ok": False, "exit_code": 1, "error": "replace missing for search-mode edit", "path": str(p)}
            old = p.read_text(encoding="utf-8", errors="replace")
            n = old.count(search)
            if n == 0:
                return {"ok": False, "exit_code": 1, "error": f"search text not found ({len(search)} chars)", "path": str(p)}
            if n > 1:
                return {"ok": False, "exit_code": 1, "error": f"search text ambiguous: found {n} occurrences (use a longer anchor)", "path": str(p)}
            new = old.replace(search, replace, 1)
            p.write_text(new, encoding="utf-8")
            prefix = old[: old.find(search)]
            changed_from = prefix.count("\n") + 1
            changed_to = changed_from + replace.count("\n")
            result: dict = {
                "ok": True,
                "exit_code": 0,
                "path": str(p),
                "mode": "diff",
                "bytes": len(new.encode("utf-8")),
                "sha256": _file_digest(p),
                "changed_from": changed_from,
                "changed_to": changed_to,
            }
            if p.suffix.lower() == ".py":
                verified, err = _verify_py(p)
                result["verified"] = verified
                if not verified:
                    result["compile_error"] = err
                    result["output"] = (
                        f"write ok, but py_compile FAILED: {err}\n"
                        f"changed lines {changed_from}-{changed_to}. "
                        f"Re-read with read_file(line_from={changed_from}, line_to={changed_to})."
                    )
            return result

        # full write (content)
        if content is None:
            return {"ok": False, "exit_code": 1, "error": "write_file needs content= or search=+replace=", "path": str(p)}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        result = {
            "ok": True,
            "exit_code": 0,
            "path": str(p),
            "mode": "full",
            "bytes": len(content.encode("utf-8")),
            "sha256": _file_digest(p),
        }
        if p.suffix.lower() == ".py":
            verified, err = _verify_py(p)
            result["verified"] = verified
            if not verified:
                result["compile_error"] = err
                result["output"] = f"write ok, but py_compile FAILED: {err}"
        return result
    except Exception as e:
        return {"ok": False, "exit_code": 1, "error": str(e)}


def search_files(pattern: str, under: str = ".") -> dict:
    """Simple substring search in text files under path."""
    try:
        root = _resolve(under)
        hits: list[str] = []
        for f in root.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in {".md", ".txt", ".py", ".yaml", ".yml", ".json", ".toml"}:
                continue
            try:
                body = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if pattern.lower() in body.lower() or pattern.lower() in f.name.lower():
                hits.append(str(f.relative_to(ROOT)))
            if len(hits) >= 50:
                break
        return {"ok": True, "exit_code": 0, "hits": hits, "output": "\n".join(hits) or "(none)"}
    except Exception as e:
        return {"ok": False, "exit_code": 1, "error": str(e)}
