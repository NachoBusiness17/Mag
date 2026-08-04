from . import code_execution, filesystem, shell

TOOL_MAP = {
    "list_dir": lambda **kw: filesystem.list_dir(**kw),
    "read_file": lambda **kw: filesystem.read_file(**kw),
    "write_file": lambda **kw: filesystem.write_file(**kw),
    "search_files": lambda **kw: filesystem.search_files(**kw),
    "run_shell": lambda **kw: shell.run_shell(**kw),
    "run_python": lambda **kw: code_execution.run_python(**kw),
}


def _normalize_args(name: str, args: dict | None) -> dict | None:
    """Defense against the recurring single-`arguments`-blob shape collapse.

    Models sometimes emit the whole call as one nested dict under the key
    `arguments` (or `params`/`kwargs`) instead of flat named parameters.
    Unwrap that single-key shape so `write_file` binds correctly instead of
    raising a cryptic TypeError that the collapse detector then has to catch
    after 5 identical failures. Returns None on unknown tool.
    """
    args = dict(args or {})
    if name not in TOOL_MAP:
        return None
    # Single-key nested blob: {"arguments": {...}} -> {...}
    # Also unwrap when the value is a JSON *string* (harness captures the
    # parameter value as raw text, so a model emitting one `arguments` param
    # yields {"arguments": '{"path": ...}'} — a string, not a dict).
    for key in ("arguments", "params", "kwargs"):
        if len(args) == 1 and key in args:
            val = args[key]
            if isinstance(val, dict):
                return dict(val)
            if isinstance(val, str):
                try:
                    import json

                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        return parsed
                except (ValueError, TypeError):
                    pass
    return args


# Real callables for signature introspection — the TOOL_MAP lambdas hide
# signatures behind **kw, which would make error messages useless.
_FN = {
    "list_dir": filesystem.list_dir,
    "read_file": filesystem.read_file,
    "write_file": filesystem.write_file,
    "search_files": filesystem.search_files,
    "run_shell": shell.run_shell,
    "run_python": code_execution.run_python,
}


def _expected_params(name: str) -> str:
    import inspect

    fn = _FN.get(name) or TOOL_MAP[name]
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return "(unknown signature)"
    parts = []
    for p in sig.parameters.values():
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
            default = "" if p.default is inspect.Parameter.empty else f"={p.default!r}"
            parts.append(f"{p.name}{default}")
        elif p.kind == p.VAR_KEYWORD:
            parts.append(f"**{p.name}")
    return ", ".join(parts) or "(no params)"


def dispatch(name: str, args: dict | None = None) -> dict:
    if name not in TOOL_MAP:
        return {"ok": False, "exit_code": 127, "error": f"unknown tool: {name}", "tools": list(TOOL_MAP)}
    args = _normalize_args(name, args)
    try:
        return TOOL_MAP[name](**args)
    except TypeError as e:
        # Convert the cryptic binding error into an actionable shape error so
        # the model recovers on the FIRST attempt instead of looping until the
        # collapse detector fires (bug #2 in the 2026-08-03 12h sovereign run).
        return {
            "ok": False,
            "exit_code": 2,
            "error": (
                f"bad arguments for {name}: {e}. "
                f"Expected flat named parameters: {_expected_params(name)}. "
                "Emit ONE <parameter name='X'> element per argument as SIBLINGS — "
                "never nest them under a single 'arguments' blob."
            ),
            "expected_params": _expected_params(name),
            "received_args": sorted(args),
        }


__all__ = ["TOOL_MAP", "dispatch"]
