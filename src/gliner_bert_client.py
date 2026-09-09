"""Cliente HTTP do serviço gliner-bert (sem torch neste processo)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from src.config import get_config
from src.ner_backends import EntitySpan

config = get_config()


class GlinerBertUnavailable(RuntimeError):
    """Serviço GLiNER/BERTimbau desligado ou inacessível."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def health() -> Dict[str, Any]:
    """Consulta GET /health do container Torch."""
    if not config.GLINER_BERT:
        return {"available": False, "cuda_available": False, "train_available": False, "reason": "GLINER_BERT=false"}
    url = f"{config.GLINER_BERT_URL}/health"
    try:
        response = requests.get(url, timeout=min(10, config.GLINER_BERT_TIMEOUT))
        payload = response.json() if response.content else {}
        loaded = bool(payload.get("models_loaded")) and response.ok
        return {
            "available": loaded,
            "cuda_available": bool(payload.get("cuda_available")),
            "train_available": bool(payload.get("train_available", loaded)),
            "status_code": response.status_code,
            **payload,
        }
    except requests.RequestException as error:
        return {"available": False, "cuda_available": False, "train_available": False, "reason": str(error)}


def extract(texts: List[str], labels: Optional[List[str]] = None) -> List[List[EntitySpan]]:
    """POST /extract em lote. Uma lista de spans por texto."""
    if not config.GLINER_BERT:
        raise GlinerBertUnavailable("GLINER_BERT=false; o container Torch não foi habilitado.")
    url = f"{config.GLINER_BERT_URL}/extract"
    body: Dict[str, Any] = {"texts": texts}
    if labels:
        body["labels"] = labels
    try:
        response = requests.post(url, json=body, timeout=config.GLINER_BERT_TIMEOUT)
    except requests.RequestException as error:
        raise GlinerBertUnavailable(str(error)) from error
    if response.status_code >= 400:
        raise GlinerBertUnavailable(
            f"gliner-bert HTTP {response.status_code}: {response.text[:300]}",
            status_code=response.status_code,
        )
    payload = response.json() or {}
    raw_lists = payload.get("spans") or []
    results: List[List[EntitySpan]] = []
    for spans in raw_lists:
        converted: List[EntitySpan] = []
        for span in spans or []:
            converted.append(
                {
                    "text": str(span.get("text") or "").strip(),
                    "label": str(span.get("label") or "MISC"),
                    "start": int(span.get("start") or 0),
                    "end": int(span.get("end") or 0),
                    "source": str(span.get("source") or "gliner"),
                }
            )
        results.append(converted)
    while len(results) < len(texts):
        results.append([])
    return results[: len(texts)]


def start_train(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST /train (job assíncrono)."""
    if not config.GLINER_BERT:
        raise GlinerBertUnavailable("GLINER_BERT=false; o container Torch não foi habilitado.")
    url = f"{config.GLINER_BERT_URL}/train"
    try:
        response = requests.post(url, json=payload, timeout=min(60, config.GLINER_BERT_TIMEOUT))
    except requests.RequestException as error:
        raise GlinerBertUnavailable(str(error), status_code=503) from error
    try:
        body = response.json() if response.content else {}
    except ValueError:
        body = {"detail": response.text[:300]}
    if response.status_code >= 400:
        detail = body.get("detail") or body.get("error") or response.text[:300]
        raise GlinerBertUnavailable(str(detail), status_code=response.status_code)
    return body if isinstance(body, dict) else {"success": True}


def train_status() -> Dict[str, Any]:
    """GET /train/status."""
    if not config.GLINER_BERT:
        return {"state": "idle", "cuda_available": False, "reason": "GLINER_BERT=false"}
    url = f"{config.GLINER_BERT_URL}/train/status"
    try:
        response = requests.get(url, timeout=min(10, config.GLINER_BERT_TIMEOUT))
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            return {"state": "error", "message": str(payload)}
        return payload if isinstance(payload, dict) else {"state": "idle"}
    except requests.RequestException as error:
        return {"state": "error", "message": str(error)}


def list_models() -> Dict[str, Any]:
    """GET /models (Hub + checkpoints em disco)."""
    if not config.GLINER_BERT:
        return {
            "available": False,
            "current_id": "hub",
            "checkpoints": [],
            "reason": "GLINER_BERT=false",
        }
    url = f"{config.GLINER_BERT_URL}/models"
    try:
        response = requests.get(url, timeout=min(10, config.GLINER_BERT_TIMEOUT))
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            raise GlinerBertUnavailable(
                str(payload.get("detail") or payload),
                status_code=response.status_code,
            )
        if not isinstance(payload, dict):
            return {"current_id": "hub", "checkpoints": []}
        payload["available"] = True
        return payload
    except requests.RequestException as error:
        raise GlinerBertUnavailable(str(error)) from error


def reload_model(model_id: str, trained_only: Optional[bool] = None) -> Dict[str, Any]:
    """POST /reload — troca o GLiNER em memória (Hub ou pasta em disco)."""
    if not config.GLINER_BERT:
        raise GlinerBertUnavailable("GLINER_BERT=false; o container Torch não foi habilitado.")
    url = f"{config.GLINER_BERT_URL}/reload"
    body: Dict[str, Any] = {"id": (model_id or "hub").strip() or "hub"}
    if trained_only is not None:
        body["trained_only"] = trained_only
    try:
        response = requests.post(url, json=body, timeout=config.GLINER_BERT_TIMEOUT)
    except requests.RequestException as error:
        raise GlinerBertUnavailable(str(error), status_code=503) from error
    try:
        payload = response.json() if response.content else {}
    except ValueError:
        payload = {"detail": response.text[:300]}
    if response.status_code >= 400:
        detail = payload.get("detail") or payload.get("error") or response.text[:300]
        raise GlinerBertUnavailable(str(detail), status_code=response.status_code)
    return payload if isinstance(payload, dict) else {"success": True}
