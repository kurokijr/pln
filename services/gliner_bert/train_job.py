"""Job de treino GLiNER com encoder BERTimbau (CPU ou CUDA)."""

from __future__ import annotations

import os
import re
import threading
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from bio_to_gliner import BioConversionError, convert_bio_json

ENCODER_NAME = os.getenv(
    "GLINER_ENCODER",
    "neuralmind/bert-base-portuguese-cased",
)
CHECKPOINT_ROOT = os.getenv("GLINER_CHECKPOINT_ROOT", "/models/checkpoints")
DEFAULT_OUTPUT_NAME = "gliner-bertimbau-pt"
DEFAULT_MAX_STEPS = int(os.getenv("GLINER_TRAIN_MAX_STEPS", "200"))
MAX_STEPS_CAP = 20000
_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")

_lock = threading.Lock()
_job: Dict[str, Any] = {
    "state": "idle",
    "job_id": None,
    "step": 0,
    "max_steps": 0,
    "message": "Nenhum treino em andamento.",
    "output_dir": None,
    "error": None,
    "cuda_required": False,
}


def cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def snapshot() -> Dict[str, Any]:
    with _lock:
        return deepcopy(_job)


def _sanitize_name(name: str) -> str:
    cleaned = _NAME_RE.sub("-", (name or "").strip())[:80].strip(".-")
    return cleaned or DEFAULT_OUTPUT_NAME


def _set(**fields: Any) -> None:
    with _lock:
        _job.update(fields)


def _run_training(
    job_id: str,
    train_data: list,
    val_data: list,
    output_dir: str,
    max_steps: int,
) -> None:
    try:
        _set(state="running", message="Carregando encoder BERTimbau e cabeça GLiNER...")
        try:
            from gliner import GLiNER
            from gliner.config import GLiNERConfig
        except ImportError:
            from gliner import GLiNER, GLiNERConfig  # type: ignore

        config = GLiNERConfig(
            model_name=ENCODER_NAME,
            hidden_size=768,
            max_width=12,
            max_len=384,
            fine_tune=True,
            span_mode="markerV0",
        )
        model = GLiNER(config)
        device = "GPU" if cuda_available() else "CPU"
        _set(message=f"Treinando {max_steps} passos no encoder {ENCODER_NAME} ({device})...")
        batch_size = 4 if cuda_available() else 1
        kwargs: Dict[str, Any] = {
            "train_dataset": train_data,
            "output_dir": output_dir,
            "max_steps": max_steps,
            "per_device_train_batch_size": batch_size,
            "learning_rate": 1e-5,
            "others_lr": 5e-5,
            "save_total_limit": 1,
        }
        if val_data:
            kwargs["eval_dataset"] = val_data
        if cuda_available():
            try:
                import torch

                if torch.cuda.is_bf16_supported():
                    kwargs["bf16"] = True
            except Exception:
                pass
        else:
            kwargs["use_cpu"] = True
            kwargs["bf16"] = False
            kwargs["fp16"] = False
        try:
            trainer = model.train_model(**kwargs)
        except TypeError:
            kwargs.pop("use_cpu", None)
            kwargs.pop("bf16", None)
            kwargs.pop("fp16", None)
            trainer = model.train_model(**kwargs)
        if trainer is not None and hasattr(trainer, "save_model"):
            trainer.save_model()
        elif hasattr(model, "save_pretrained"):
            model.save_pretrained(output_dir)
        _set(
            state="done",
            step=max_steps,
            message=f"Checkpoint gravado em {output_dir}",
            output_dir=output_dir,
            error=None,
        )
    except Exception as error:
        _set(
            state="error",
            message=str(error),
            error=str(error),
        )
        print(f"❌ Treino GLiNER falhou (job {job_id}): {error}")


def start_train(payload: Any) -> Dict[str, Any]:
    """Valida o JSON BIO e dispara o treino em background. Um job por vez."""
    if not isinstance(payload, (dict, list)):
        raise BioConversionError("Body JSON inválido.")

    options = payload if isinstance(payload, dict) else {}
    max_steps = int(options.get("max_steps") or DEFAULT_MAX_STEPS)
    max_steps = max(1, min(max_steps, MAX_STEPS_CAP))
    output_name = _sanitize_name(str(options.get("output_name") or DEFAULT_OUTPUT_NAME))
    output_dir = str(Path(CHECKPOINT_ROOT) / output_name)

    train_data, val_data, _label_map = convert_bio_json(payload)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    with _lock:
        if _job["state"] == "running":
            raise RuntimeError("Já existe um treino em andamento.")
        job_id = uuid.uuid4().hex[:12]
        _job.update(
            {
                "state": "running",
                "job_id": job_id,
                "step": 0,
                "max_steps": max_steps,
                "message": (
                    f"Convertidas {len(train_data)} frases de treino; "
                    f"iniciando em {'GPU' if cuda_available() else 'CPU'}..."
                ),
                "output_dir": output_dir,
                "error": None,
                "train_size": len(train_data),
                "val_size": len(val_data),
            }
        )

    thread = threading.Thread(
        target=_run_training,
        args=(job_id, train_data, val_data, output_dir, max_steps),
        daemon=True,
        name=f"gliner-train-{job_id}",
    )
    thread.start()
    return snapshot()
