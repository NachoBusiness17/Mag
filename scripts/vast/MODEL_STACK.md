# Model stack — Quadro RTX 8000 48 GB (Mag blast)

Turing 48 GB: great for **one hot mid/large quant**, not for stacking three 30B models.

## Recommended (default template): `rtx8000_48`

| Mag role | Model | ~VRAM | Why |
|----------|--------|-------|-----|
| **worker** (dig / research-pack) | `qwen2.5:32b` | ~18–22 GB | Best balance quality×speed×ctx headroom for blast |
| **clerk / router** | `gemma:2b` | ~2 GB or CPU | Scut, ask, synthesize — keep tiny |
| **embed** | `nomic-embed-text` | ~0.3–1 GB | Retrieval / future rag |
| **critic** (optional) | same as worker **or** unload | — | Don’t keep two 32B hot |

**lanes map (Vast-backed):**

```yaml
local_models:
  clerk: gemma:2b
  router: gemma:2b
  worker: qwen2.5:32b
  critic: qwen2.5:32b
  biographer: qwen2.5:32b
  embed: nomic-embed-text

load_policy:
  mode: sequential
  prefer_keep_worker_hot: true   # plant is always-on GPU — keep worker hot
```

### Alternatives if pull fails

| Fallback worker | When |
|-----------------|------|
| `qwen2.5:14b` | Bandwidth / disk tight |
| `llama3.1:8b` | Smoke only |
| `gemma2:27b` | Prefer Google family |

### Optional coder digs

- `qwen2.5-coder:32b` — swap worker for code-heavy weeks; still one-at-a-time on 48 GB.

## Power mode: single 70B (`tight70`)

| Role | Model | Notes |
|------|--------|------|
| worker | `llama3.3:70b` (Ollama default quant ≈ Q4) | ~40–45 GB — **tight** |
| clerk | `gemma:2b` | Prefer CPU if VRAM pressure |
| embed | offload / CPU | Don’t fight 70B for VRAM |

Use when: long-form judgment digs, few concurrent jobs.  
Avoid when: blast multi-ticket + long context (KV cache will OOM or thrash).

**Safer 70B:** if Ollama exposes Q3 variants or you use Modelfile with lower quant — more room for context.

## Do **not** put on this card (for Mag)

| Skip | Why |
|------|-----|
| Multiple 32B+ hot | VRAM thrash |
| 72B Q4 full + long ctx | Often >48 GB with KV |
| Vision-heavy stacks | Different template |
| Training full SFT | Wrong product — inference plant |

## Grok Build stays home

- **Grok TUI** = L2 judgment, multi-file design, promote philosophy  
- **Vast worker** = pack digs, improve blast, local ask when OLLAMA_HOST set  
- Do not try to run Grok Build *on* Vast

## Speed expectations (order of magnitude)

| Model | Dig usefulness | Tok/s rough (Turing 48G) |
|-------|----------------|---------------------------|
| 32B Q4 | Primary | usable interactive |
| 70B Q4 | High quality, slower | ok for unattended blast |
| 8B | smoke only | fast, weak digs |

## Env for template

```text
MAG_STACK=rtx8000_48
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_KEEP_ALIVE=30m
```

Switch stack without new image: set `MAG_STACK=tight70` on instance env and re-run onstart (or pull manually).
