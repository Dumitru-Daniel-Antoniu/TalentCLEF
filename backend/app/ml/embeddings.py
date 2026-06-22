"""Embedding utilities.

Minimal loader that prefers a packaged trained model (jobbert_backend.zip).
It uses HuggingFace `transformers` + `torch` to load models from the
extracted directory. If a packaged model is not found, it falls back to the
public HF model `sentence-transformers/all-MiniLM-L6-v2` via `transformers`.

We intentionally avoid adding `sentence-transformers` as a hard dependency
for the backend; if it happens to be available in the environment the code
will try to use it for packaged models marked as SentenceTransformer, but
the primary loading path is HF+torch.
"""
from typing import List, Optional
import os
import threading
import logging
import zipfile
import hashlib
from pathlib import Path

import numpy as np
import json

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_TYPE: Optional[str] = None
_LOCK = threading.Lock()

# Default public model (loaded via transformers + torch)
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _load_tokenizer_with_fix(name_or_path: str, local: bool = True):
    """Load a tokenizer trying `fix_mistral_regex=True` when available.

    Falls back to calling without the flag if the transformers version
    doesn't accept the parameter, and returns None on failure.
    """
    try:
        from transformers import AutoTokenizer
    except Exception:
        return None

    try:
        if local:
            try:
                return AutoTokenizer.from_pretrained(name_or_path, local_files_only=True, fix_mistral_regex=True)
            except TypeError:
                return AutoTokenizer.from_pretrained(name_or_path, local_files_only=True)
        else:
            try:
                return AutoTokenizer.from_pretrained(name_or_path, fix_mistral_regex=True)
            except TypeError:
                return AutoTokenizer.from_pretrained(name_or_path)
    except Exception:
        return None


def _md5_of_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_valid_extraction(path: Path) -> bool:
    if not path.is_dir():
        return False
    markers = ("model.pt", "pytorch_model.bin", "model.safetensors", "tf_model.h5")
    return any(
        (path / marker).exists() or next(path.rglob(marker), None) is not None
        for marker in markers
    )


def _write_extraction_manifest(manifest_path: Path, archive_path: Path, destination: Path) -> None:
    stat = archive_path.stat()
    payload = {
        "archive_size": stat.st_size,
        "archive_mtime_ns": stat.st_mtime_ns,
        "directory": destination.name,
    }
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")


def _extract_archive(archive_path: Path, dest_root: Path) -> Path:
    dest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = dest_root / ".jobbert_extraction.json"
    archive_stat = archive_path.stat()

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cached = dest_root / manifest["directory"]
        if (
            manifest.get("archive_size") == archive_stat.st_size
            and manifest.get("archive_mtime_ns") == archive_stat.st_mtime_ns
            and _is_valid_extraction(cached)
        ):
            logger.info("Reusing extracted model at %s", cached)
            return cached
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass

    # Older extractions predate the manifest. Reuse one only when it is newer
    # than the archive and contains complete model artifacts.
    existing = sorted(dest_root.glob("jobbert_*"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for candidate in existing:
        if candidate.stat().st_mtime_ns >= archive_stat.st_mtime_ns and _is_valid_extraction(candidate):
            _write_extraction_manifest(manifest_path, archive_path, candidate)
            logger.info("Reusing extracted model at %s", candidate)
            return candidate

    md5 = _md5_of_file(archive_path)
    dest = dest_root / f"jobbert_{md5}"
    if _is_valid_extraction(dest):
        _write_extraction_manifest(manifest_path, archive_path, dest)
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, 'r') as z:
        z.extractall(dest)
    _write_extraction_manifest(manifest_path, archive_path, dest)
    return dest


def _try_load_packaged_model() -> bool:
    """Look for a packaged model archive and attempt to load it.

    Returns True on success and sets the module-level _MODEL/_MODEL_TYPE.
    """
    global _MODEL, _MODEL_TYPE
    backend_root = Path(__file__).resolve().parents[2]
    workspace_root = backend_root.parents[0]

    candidates = []
    env_path = os.environ.get("JOBBERT_MODEL_ZIP")
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend([
        backend_root / "jobbert_backend.zip",
        workspace_root / "jobbert_backend.zip",
        Path.cwd() / "jobbert_backend.zip",
    ])

    archive = None
    for c in candidates:
        if c and c.exists():
            archive = c
            break

    if not archive:
        logger.info("No packaged model archive found; will use default model")
        return False

    logger.info("Found model archive at %s; preparing model directory...", archive)
    models_dir = backend_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    try:
        extracted = _extract_archive(archive, models_dir)
    except Exception as e:
        logger.exception("Failed to extract archive: %s", e)
        return False

    # Look for candidate subdirectories that contain HF model artifacts
    def _find_candidate_dirs(root: Path):
        candidates = []
        # Common HF artifact filenames
        hf_markers = ["config.json", "pytorch_model.bin", "model.safetensors", "tf_model.h5"]
        for marker in hf_markers:
            for p in root.rglob(marker):
                if p and p.parent:
                    candidates.append(p.parent)
        # Also consider the extracted root itself
        candidates.insert(0, root)
        # Deduplicate while preserving order
        seen = set()
        out = []
        for c in candidates:
            try:
                s = str(c.resolve())
            except Exception:
                s = str(c)
            if s not in seen:
                seen.add(s)
                out.append(c)
        return out

    candidate_dirs = _find_candidate_dirs(extracted)

    # Preferred: load with HuggingFace transformers + torch from a candidate folder
    for candidate in candidate_dirs:
        # If the package contains a PyTorch state dict `model.pt`, try loading it
        model_pt = Path(candidate) / "model.pt"
        cfg_json = Path(candidate) / "config.json"
        if model_pt.exists():
            try:
                import torch
                from transformers import AutoTokenizer, BertConfig, BertModel

                logger.info("Found model.pt at %s; attempting to construct model from state_dict", model_pt)

                state = torch.load(str(model_pt), map_location='cpu')
                if not isinstance(state, dict):
                    raise RuntimeError('model.pt is not a state_dict')

                # Derive shape-based config values from the checkpoint
                def _get_shape(key):
                    v = state.get(key)
                    return v.shape if v is not None else None

                vocab_shape = _get_shape('encoder.embeddings.word_embeddings.weight')
                pos_shape = _get_shape('encoder.embeddings.position_embeddings.weight')
                type_shape = _get_shape('encoder.embeddings.token_type_embeddings.weight')
                hidden_size = vocab_shape[1] if vocab_shape is not None else None

                # infer intermediate size and number of layers
                inter_shape = _get_shape('encoder.encoder.layer.0.intermediate.dense.weight')
                intermediate_size = inter_shape[0] if inter_shape is not None else None

                # count layers
                max_layer = -1
                for k in state.keys():
                    if k.startswith('encoder.encoder.layer.'):
                        parts = k.split('.')
                        try:
                            idx = int(parts[3])
                            if idx > max_layer:
                                max_layer = idx
                        except Exception:
                            pass
                num_layers = max_layer + 1 if max_layer >= 0 else None

                # choose attention heads that divide hidden_size
                def _choose_heads(hs):
                    for h in (32, 16, 12, 8, 6, 4, 2, 1):
                        if hs % h == 0:
                            return h
                    return 1

                if hidden_size is None:
                    raise RuntimeError('Could not infer hidden size from checkpoint')

                num_attention_heads = _choose_heads(hidden_size)

                # Build a BertConfig matching shapes
                cfg = BertConfig(
                    vocab_size=vocab_shape[0] if vocab_shape is not None else 30522,
                    hidden_size=hidden_size,
                    num_hidden_layers=num_layers or 12,
                    num_attention_heads=num_attention_heads,
                    intermediate_size=intermediate_size or (hidden_size * 4),
                    max_position_embeddings=pos_shape[0] if pos_shape is not None else 512,
                    type_vocab_size=type_shape[0] if type_shape is not None else 2,
                )

                # Instantiate a fresh model and load mapped state dict
                model = BertModel(cfg)

                # Try to load tokenizer from packaged folder, else fallback to base_name
                base_name = None
                if cfg_json.exists():
                    try:
                        with open(cfg_json, 'r', encoding='utf-8') as fh:
                            meta = json.load(fh)
                        base_name = meta.get('model_name')
                    except Exception:
                        base_name = None

                # Try to load tokenizer from packaged folder using the safe loader
                tokenizer = _load_tokenizer_with_fix(str(candidate), local=True)
                if tokenizer is None:
                    if base_name:
                        tokenizer = _load_tokenizer_with_fix(base_name, local=False)
                    if tokenizer is None:
                        tokenizer = _load_tokenizer_with_fix(DEFAULT_MODEL_NAME, local=False)
                    if tokenizer is None:
                        raise RuntimeError("Unable to load tokenizer for packaged model")

                # Remap keys by stripping leading 'encoder.' prefix
                new_state = {}
                for k, v in state.items():
                    new_k = k
                    if new_k.startswith('encoder.'):
                        new_k = new_k[len('encoder.') :]
                    new_state[new_k] = v

                try:
                    model.load_state_dict(new_state, strict=False)
                except Exception:
                    logger.exception('Failed to load state_dict into constructed BertModel')

                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                model.to(device)
                model.eval()
                _MODEL = {"model": model, "tokenizer": tokenizer, "device": device, "path": str(candidate)}
                _MODEL_TYPE = "hf"
                logger.info("Loaded packaged model from state_dict at %s", candidate)
                return True
            except Exception as e:
                logger.exception("Custom state_dict load failed for candidate %s: %s", candidate, e)

        try:
            from transformers import AutoModel, AutoTokenizer
            import torch

            logger.info("Attempting to load packaged model with HuggingFace from %s", candidate)
            # load tokenizer using safe helper to apply `fix_mistral_regex` when available
            tokenizer = _load_tokenizer_with_fix(str(candidate), local=True)
            if tokenizer is None:
                # fallback to default tokenizer if packaged tokenizer is problematic
                tokenizer = _load_tokenizer_with_fix(DEFAULT_MODEL_NAME, local=False)
            model = AutoModel.from_pretrained(str(candidate), local_files_only=True)
            model.eval()
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            _MODEL = {"model": model, "tokenizer": tokenizer, "device": device, "path": str(candidate)}
            _MODEL_TYPE = "hf"
            logger.info("Loaded packaged HuggingFace model from %s", candidate)
            return True
        except Exception as e:
            logger.exception("HuggingFace load failed for candidate %s: %s", candidate, e)

    # Optional: if sentence-transformers is present, try that next
    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Attempting to load packaged model with SentenceTransformer from %s", extracted)
        st = SentenceTransformer(str(extracted))
        _MODEL = st
        _MODEL_TYPE = "sentence_transformer"
        logger.info("Loaded packaged SentenceTransformer model")
        return True
    except Exception as e:
        logger.info("SentenceTransformer not available or failed: %s", e)

    return False


def _ensure_model():
    """Ensure _MODEL is loaded; prefer packaged model, else load default via HF."""
    global _MODEL, _MODEL_TYPE
    if _MODEL is not None:
        return
    with _LOCK:
        if _MODEL is not None:
            return
        ok = _try_load_packaged_model()
        if ok:
            return

        # Fallback: load default model via transformers + torch
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch

            logger.info("Loading default HF model %s", DEFAULT_MODEL_NAME)
            tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL_NAME)
            model = AutoModel.from_pretrained(DEFAULT_MODEL_NAME)
            model.eval()
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            _MODEL = {"model": model, "tokenizer": tokenizer, "device": device}
            _MODEL_TYPE = "hf"
            logger.info("Loaded default HF model")
        except Exception:
            logger.exception("Failed to load default HF model %s", DEFAULT_MODEL_NAME)


def mean_pooling_hf(last_hidden_state, attention_mask):
    import torch
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = torch.sum(last_hidden_state * mask, 1)
    summed_mask = torch.clamp(mask.sum(1), min=1e-9)
    return summed / summed_mask


def get_embedding(text: str) -> np.ndarray:
    """Return a single numpy embedding for the provided text."""
    _ensure_model()
    if _MODEL_TYPE == "sentence_transformer":
        emb = _MODEL.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return np.array(emb)

    if _MODEL_TYPE == "hf":
        import torch

        tokenizer = _MODEL["tokenizer"]
        model = _MODEL["model"]
        device = _MODEL["device"]
        inputs = tokenizer(text, truncation=True, padding=True, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model(**inputs)
        emb = mean_pooling_hf(out.last_hidden_state, inputs["attention_mask"])  # (1, D)
        emb = emb.cpu().numpy()[0]
        emb = emb / (np.linalg.norm(emb) + 1e-12)
        return emb

    raise RuntimeError("No model loaded for embeddings")


def embed_texts(texts: List[str]) -> np.ndarray:
    """Return embeddings for a list of texts as a numpy array.

    Uses HF batching when available.
    """
    _ensure_model()
    if _MODEL_TYPE == "sentence_transformer":
        embs = _MODEL.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return np.array(embs)

    if _MODEL_TYPE == "hf":
        import torch
        tokenizer = _MODEL["tokenizer"]
        model = _MODEL["model"]
        device = _MODEL["device"]
        batch_size = 16
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = tokenizer(batch, truncation=True, padding=True, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                out = model(**inputs)
            embs = mean_pooling_hf(out.last_hidden_state, inputs["attention_mask"])  # (B, D)
            embs = embs.cpu().numpy()
            norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-12
            embs = embs / norms
            all_embs.append(embs)
        return np.vstack(all_embs)

    raise RuntimeError("No model loaded for embeddings")


def get_model_info() -> dict:
    """Return basic model information: whether loaded, model type, and embedding dim (if available)."""
    _ensure_model()
    info = {"loaded": _MODEL is not None, "model_type": _MODEL_TYPE}
    if not _MODEL:
        return info

    # Try to infer embedding dimension by computing a single embedding
    try:
        emb = get_embedding("test")
        info["dim"] = int(len(emb))
    except Exception:
        # Best-effort: try to read from model config
        try:
            if _MODEL_TYPE == "hf" and isinstance(_MODEL, dict):
                m = _MODEL.get("model")
                cfg = getattr(m, "config", None)
                if cfg and hasattr(cfg, "hidden_size"):
                    info["dim"] = int(cfg.hidden_size)
        except Exception:
            pass

    return info

