"""Fusão BERTimbau + GLiNER (funções puras, sem torch)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_span_merge():
    path = Path(__file__).resolve().parents[1] / "services" / "gliner_bert" / "span_merge.py"
    spec = importlib.util.spec_from_file_location("span_merge", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


span_merge = _load_span_merge()


def test_normalize_label_classic_and_open():
    assert span_merge.normalize_label("pessoa") == "PER"
    assert span_merge.normalize_label("organização") == "ORG"
    assert span_merge.normalize_label("local") == "LOC"
    assert span_merge.normalize_label("material") == "MATERIAL"
    assert span_merge.normalize_label("LEGISLACAO") == "NORMA"
    assert span_merge.normalize_label("instituição") == "INSTITUICAO"


def test_bertimbau_wins_on_overlapping_classic_span():
    bert = [
        {
            "text": "Tribunal de Contas",
            "label": "ORG",
            "start": 2,
            "end": 20,
            "source": "bertimbau",
            "score": 0.99,
        }
    ]
    gliner = [
        {
            "text": "Tribunal de Contas da União",
            "label": "organização",
            "start": 2,
            "end": 29,
            "source": "gliner",
            "score": 0.8,
        },
        {
            "text": "extrusão",
            "label": "material",
            "start": 40,
            "end": 48,
            "source": "gliner",
            "score": 0.7,
        },
    ]
    merged = span_merge.merge_span_sources(bert, gliner)
    labels = {(item["text"], item["label"], item["source"]) for item in merged}
    assert ("Tribunal de Contas", "ORG", "bertimbau") in labels
    assert ("extrusão", "MATERIAL", "gliner") in labels
    assert not any(item["text"] == "Tribunal de Contas da União" for item in merged)


def test_gliner_fills_classic_span_when_bertimbau_misses():
    merged = span_merge.merge_span_sources(
        [],
        [
            {
                "text": "Brasília",
                "label": "local",
                "start": 0,
                "end": 8,
                "source": "gliner",
                "score": 0.9,
            }
        ],
    )
    assert len(merged) == 1
    assert merged[0]["label"] == "LOC"
    assert merged[0]["source"] == "gliner"
