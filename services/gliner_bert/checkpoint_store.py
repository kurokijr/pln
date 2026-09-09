"""Listagem e resolução de checkpoints GLiNER em disco (sem torch)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

HUB_ID = "hub"
NAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,80}$")


def checkpoint_root(env_value: Optional[str] = None) -> Path:
    return Path(env_value or os.getenv("GLINER_CHECKPOINT_ROOT", "/models/checkpoints"))


def checkpoint_exists(path: Path | str) -> bool:
    root = Path(path)
    if not root.exists():
        return False
    if root.is_file():
        return True
    if not root.is_dir():
        return False
    return any(root.glob("*.json")) or any(root.glob("*.bin")) or any(root.glob("*.safetensors"))


def list_checkpoints(root: Path | str) -> List[Dict[str, str]]:
    base = Path(root)
    if not base.is_dir():
        return []
    items: List[Dict[str, str]] = []
    for child in sorted(base.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if not NAME_RE.match(child.name):
            continue
        if checkpoint_exists(child):
            items.append({"id": child.name, "name": child.name, "path": str(child)})
    return items


def resolve_checkpoint(root: Path | str, name: str) -> Path:
    """Resolve um nome de pasta sob o root. Recusa path traversal."""
    cleaned = (name or "").strip()
    if not NAME_RE.match(cleaned):
        raise ValueError("Nome de checkpoint inválido.")
    base = Path(root).resolve()
    target = (base / cleaned).resolve()
    if target == base or base not in target.parents:
        raise ValueError("Checkpoint fora do diretório permitido.")
    if not checkpoint_exists(target):
        raise FileNotFoundError(f"Checkpoint não encontrado: {cleaned}")
    return target


def current_id(loaded_path: str, root: Path | str, hub_model: str) -> str:
    """'hub' se o path não estiver sob o diretório de checkpoints."""
    if not loaded_path or loaded_path == hub_model:
        return HUB_ID
    try:
        resolved = Path(loaded_path).resolve()
        base = Path(root).resolve()
        if resolved == base:
            return HUB_ID
        if base in resolved.parents or resolved.parent == base:
            rel = resolved.relative_to(base)
            name = rel.parts[0] if rel.parts else HUB_ID
            return name if name != "." else HUB_ID
    except (OSError, ValueError):
        pass
    return HUB_ID


def catalog(
    loaded_path: str,
    root: Path | str,
    hub_model: str,
    trained_only: bool,
) -> Dict[str, Any]:
    base = Path(root)
    return {
        "current_id": current_id(loaded_path, base, hub_model),
        "current_path": loaded_path,
        "trained_only": bool(trained_only),
        "hub": {
            "id": HUB_ID,
            "label": f"Padrão Hub ({hub_model} + BERTimbau NER)",
            "path": hub_model,
        },
        "checkpoints": list_checkpoints(base),
    }
