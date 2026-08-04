from .registry import inventory, model_for, model_present, ollama_tags, require_model

# Back-compat name used by older imports
def _models_map():
    from .registry import _load_local_models

    return _load_local_models()


MODELS = property  # placeholder avoided — use inventory()

__all__ = [
    "model_for",
    "require_model",
    "inventory",
    "ollama_tags",
    "model_present",
]
