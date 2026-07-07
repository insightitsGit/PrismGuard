from __future__ import annotations

from pathlib import Path


def load_training_tokenizer(base_model: str):
    """Load tokenizer for train/export; avoids HF hub chat-template 404 on some checkpoints."""
    from transformers import AutoTokenizer

    path = Path(base_model)
    if path.is_dir():
        return AutoTokenizer.from_pretrained(str(path), local_files_only=True)

    try:
        return AutoTokenizer.from_pretrained(base_model, local_files_only=True)
    except (OSError, ValueError):
        pass

    try:
        from huggingface_hub import snapshot_download

        local_path = snapshot_download(base_model)
        return AutoTokenizer.from_pretrained(local_path, local_files_only=True)
    except Exception:
        return AutoTokenizer.from_pretrained(base_model)


def load_training_model(base_model: str, *, num_labels: int = 2):
    from pathlib import Path

    from transformers import AutoConfig, AutoModelForSequenceClassification

    path = Path(base_model)
    model_id = str(path) if path.is_dir() else base_model
    try:
        config = AutoConfig.from_pretrained(model_id, num_labels=num_labels)
        return AutoModelForSequenceClassification.from_pretrained(model_id, config=config)
    except Exception:
        return AutoModelForSequenceClassification.from_pretrained(model_id, num_labels=num_labels)
