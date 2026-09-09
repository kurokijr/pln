"""Listagem de checkpoints GLiNER (sem torch)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load():
    path = Path(__file__).resolve().parents[1] / "services" / "gliner_bert" / "checkpoint_store.py"
    spec = importlib.util.spec_from_file_location("checkpoint_store", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


store = _load()


def test_list_skips_empty_dirs_and_finds_json(tmp_path):
    empty = tmp_path / "vazio"
    empty.mkdir()
    ready = tmp_path / "gliner-bertimbau-pt"
    ready.mkdir()
    (ready / "config.json").write_text("{}", encoding="utf-8")
    items = store.list_checkpoints(tmp_path)
    assert [item["id"] for item in items] == ["gliner-bertimbau-pt"]
    assert items[0]["path"].endswith("gliner-bertimbau-pt")


def test_resolve_rejects_traversal(tmp_path):
    with pytest.raises(ValueError):
        store.resolve_checkpoint(tmp_path, "..")
    with pytest.raises(ValueError):
        store.resolve_checkpoint(tmp_path, "../etc")
    with pytest.raises(FileNotFoundError):
        store.resolve_checkpoint(tmp_path, "nao-existe")


def test_resolve_and_current_id(tmp_path):
    ready = tmp_path / "meu-modelo"
    ready.mkdir()
    (ready / "pytorch_model.bin").write_bytes(b"x")
    resolved = store.resolve_checkpoint(tmp_path, "meu-modelo")
    assert resolved == ready.resolve()
    hub = "urchade/gliner_multi-v2.1"
    assert store.current_id(hub, tmp_path, hub) == store.HUB_ID
    assert store.current_id(str(resolved), tmp_path, hub) == "meu-modelo"


def test_catalog_includes_hub_and_checkpoints(tmp_path):
    ready = tmp_path / "treino-a"
    ready.mkdir()
    (ready / "model.safetensors").write_bytes(b"x")
    payload = store.catalog(
        str(ready),
        tmp_path,
        "urchade/gliner_multi-v2.1",
        trained_only=True,
    )
    assert payload["current_id"] == "treino-a"
    assert payload["trained_only"] is True
    assert payload["hub"]["id"] == "hub"
    assert payload["checkpoints"][0]["id"] == "treino-a"
