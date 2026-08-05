id: rem-write-file-shape
name: write_file flat args
tools: write_file
signature: arguments|unexpected keyword|bad arguments for write_file|write_file\(\{\}\)|needs content=

## Prevent
DeepSeek and Codex-style models often emit tool args wrong: nested `arguments` blob, `parameters` wrapper, or empty `{}`. Mag tools need **flat sibling keys** in the function `arguments` JSON string.

## Fix
Emit OpenAI function-call shape only:
```json
{"path": "mag/failure_kb.py", "content": "# module body..."}
```
For edits use `search` + `replace` (not full `content` overwrite). Never:
- `{"arguments": {"path": "...", "content": "..."}}` as the only key (harness unwraps this, but models still loop)
- `{"parameters": {"path": "..."}}` without flat keys
- `write_file({})` with no `path`

If stuck: `read_file` the target first, then one `write_file` with real `path` + `content` or `search`/`replace`.

## Probe
```text
python -c "from tools import dispatch; print(dispatch('write_file', {'path':'memory/working.md','content':'ok'}))"
```
