"""API FastAPI: NER BERTimbau + GLiNER, treino opcional via JSON BIO."""

from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from bio_to_gliner import BioConversionError
from checkpoint_store import (
    HUB_ID,
    catalog as checkpoint_catalog,
    checkpoint_exists,
    checkpoint_root,
    resolve_checkpoint,
)
from span_merge import merge_span_sources, normalize_label
from train_job import cuda_available, snapshot as train_snapshot, start_train

BERTIMBAU_MODEL = os.getenv(
    "BERTIMBAU_NER_MODEL",
    "pierreguillou/ner-bert-base-cased-pt-lenerbr",
)
HUB_MODEL = os.getenv("GLINER_HUB_MODEL", "urchade/gliner_multi-v2.1")
GLINER_MODEL = os.getenv("GLINER_MODEL", HUB_MODEL)
DEFAULT_LABELS = [
    item.strip()
    for item in os.getenv(
        "GLINER_LABELS",
        "pessoa,organização,local,material,processo,norma,instituição",
    ).split(",")
    if item.strip()
]
GLINER_THRESHOLD = float(os.getenv("GLINER_THRESHOLD", "0.4"))
GLINER_TRAINED_ONLY = os.getenv("GLINER_TRAINED_ONLY", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_bert_pipeline = None
_gliner_model = None
_models_error = ""
_loaded_gliner_path = GLINER_MODEL
_runtime_trained_only = GLINER_TRAINED_ONLY and checkpoint_exists(GLINER_MODEL)
_reload_lock = threading.Lock()
_reload_busy = False
CHECKPOINT_ROOT = checkpoint_root()


def _load_bert_pipeline():
    from transformers import pipeline

    return pipeline(
        "ner",
        model=BERTIMBAU_MODEL,
        aggregation_strategy="simple",
        device=-1 if not cuda_available() else 0,
    )


def _load_gliner(path: str):
    from gliner import GLiNER

    return GLiNER.from_pretrained(path)


def _load_models() -> None:
    global _bert_pipeline, _gliner_model, _models_error, _loaded_gliner_path, _runtime_trained_only
    trained_only = GLINER_TRAINED_ONLY and checkpoint_exists(GLINER_MODEL)
    _runtime_trained_only = trained_only
    if not trained_only:
        try:
            _bert_pipeline = _load_bert_pipeline()
        except Exception as error:
            _models_error = f"BERTimbau: {error}"
            raise
    else:
        _bert_pipeline = None

    try:
        _gliner_model = _load_gliner(GLINER_MODEL)
        _loaded_gliner_path = GLINER_MODEL
    except Exception as error:
        _models_error = f"GLiNER: {error}"
        raise
    _models_error = ""


def _swap_inference(gliner_path: str, trained_only: bool) -> None:
    """Carrega o GLiNER (e o NER extra se preciso) e só então troca as referências."""
    global _bert_pipeline, _gliner_model, _models_error, _loaded_gliner_path, _runtime_trained_only
    new_gliner = _load_gliner(gliner_path)
    new_bert = None
    if not trained_only:
        new_bert = _bert_pipeline or _load_bert_pipeline()
    _gliner_model = new_gliner
    _loaded_gliner_path = gliner_path
    _runtime_trained_only = trained_only
    _bert_pipeline = None if trained_only else new_bert
    _models_error = ""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_models()
    yield


app = FastAPI(title="GLiNER + BERTimbau NER", lifespan=lifespan)


class ExtractRequest(BaseModel):
    texts: List[str] = Field(default_factory=list)
    labels: Optional[List[str]] = None


class ReloadRequest(BaseModel):
    id: str = Field(..., description="hub ou nome da pasta em /models/checkpoints")
    trained_only: Optional[bool] = None


def _bertimbau_spans(text: str) -> list:
    content = text or ""
    if not content or _bert_pipeline is None:
        return []
    try:
        raw = _bert_pipeline(content[:8000])
    except Exception:
        return []
    spans = []
    for item in raw:
        start = int(item.get("start") or 0)
        end = int(item.get("end") or 0)
        surface = content[start:end] if end > start else str(item.get("word") or "").replace("##", "")
        spans.append(
            {
                "text": surface.strip(),
                "label": normalize_label(str(item.get("entity_group") or item.get("entity") or "")),
                "start": start,
                "end": end if end > start else start + len(surface),
                "source": "bertimbau",
                "score": float(item.get("score") or 0.0),
            }
        )
    return spans


def _gliner_spans(text: str, labels: List[str]) -> list:
    if not text or _gliner_model is None or not labels:
        return []
    try:
        raw = _gliner_model.predict_entities(text[:8000], labels, threshold=GLINER_THRESHOLD)
    except Exception:
        return []
    spans = []
    for item in raw:
        spans.append(
            {
                "text": str(item.get("text") or "").strip(),
                "label": normalize_label(str(item.get("label") or "")),
                "start": int(item.get("start") or 0),
                "end": int(item.get("end") or 0),
                "source": "gliner",
                "score": float(item.get("score") or 0.0),
            }
        )
    return spans


def _gliner_ready() -> bool:
    return _gliner_model is not None


@app.get("/health")
def health():
    trained_only = _runtime_trained_only
    loaded = _gliner_ready() and (trained_only or _bert_pipeline is not None)
    training = train_snapshot()
    payload = {
        "status": "ok" if loaded else "loading",
        "models_loaded": loaded,
        "bertimbau_model": None if trained_only else BERTIMBAU_MODEL,
        "gliner_model": _loaded_gliner_path,
        "current_id": checkpoint_catalog(
            _loaded_gliner_path, CHECKPOINT_ROOT, HUB_MODEL, trained_only
        )["current_id"],
        "labels": DEFAULT_LABELS,
        "cuda_available": cuda_available(),
        "train_available": True,
        "device": "cuda" if cuda_available() else "cpu",
        "trained_only": trained_only,
        "reload_busy": _reload_busy,
        "training": {
            "state": training.get("state"),
            "job_id": training.get("job_id"),
        },
    }
    if _models_error:
        payload["error"] = _models_error
        payload["status"] = "error"
    return payload


@app.post("/extract")
def extract(body: ExtractRequest):
    if not _gliner_ready():
        raise HTTPException(status_code=503, detail="Modelos ainda não carregados")
    if _bert_pipeline is None and not _runtime_trained_only:
        raise HTTPException(status_code=503, detail="Modelos ainda não carregados")
    labels = body.labels or DEFAULT_LABELS
    results = []
    for text in body.texts:
        content = text if isinstance(text, str) else str(text or "")
        gliner = _gliner_spans(content, labels)
        if _bert_pipeline is None:
            results.append(gliner)
        else:
            results.append(merge_span_sources(_bertimbau_spans(content), gliner))
    return {"spans": results, "labels": labels, "gliner_model": _loaded_gliner_path}


@app.get("/train/status")
def train_status():
    return train_snapshot()


@app.post("/train")
async def train(request: Request):
    try:
        body = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail="JSON inválido") from error
    try:
        result = start_train(body)
    except BioConversionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        message = str(error)
        code = 409 if "andamento" in message.lower() else 503
        raise HTTPException(status_code=code, detail=message) from error
    return {"success": True, **result}


@app.get("/models")
def list_models():
    return checkpoint_catalog(
        _loaded_gliner_path,
        CHECKPOINT_ROOT,
        HUB_MODEL,
        _runtime_trained_only,
    )


@app.post("/reload")
def reload_model(body: ReloadRequest):
    global _reload_busy
    model_id = (body.id or "").strip() or HUB_ID
    training = train_snapshot()
    if training.get("state") == "running":
        raise HTTPException(
            status_code=409,
            detail="Há um treino em andamento. Espere terminar antes de trocar o modelo.",
        )
    if model_id == HUB_ID:
        target_path = HUB_MODEL
        trained_only = False if body.trained_only is None else bool(body.trained_only)
    else:
        try:
            target_path = str(resolve_checkpoint(CHECKPOINT_ROOT, model_id))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        trained_only = True if body.trained_only is None else bool(body.trained_only)

    if not _reload_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Já existe um recarregamento em andamento.")
    _reload_busy = True
    try:
        _swap_inference(target_path, trained_only)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar o modelo: {error}") from error
    finally:
        _reload_busy = False
        _reload_lock.release()

    payload = checkpoint_catalog(
        _loaded_gliner_path,
        CHECKPOINT_ROOT,
        HUB_MODEL,
        _runtime_trained_only,
    )
    return {"success": True, **payload}
