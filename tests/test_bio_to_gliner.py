"""Conversão BIO → GLiNER (sem torch)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load():
    path = Path(__file__).resolve().parents[1] / "services" / "gliner_bert" / "bio_to_gliner.py"
    spec = importlib.util.spec_from_file_location("bio_to_gliner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


bio = _load()


def test_bio_sentence_inclusive_span_and_label_map():
    result = bio.bio_sentence_to_gliner(
        ["O", "Tribunal", "de", "Contas", "analisou"],
        ["O", "B-ORGANIZACAO", "I-ORGANIZACAO", "I-ORGANIZACAO", "O"],
    )
    assert result["tokenized_text"][1:4] == ["Tribunal", "de", "Contas"]
    assert result["ner"] == [[1, 3, "organização"]]


def test_rejects_i_without_b():
    with pytest.raises(bio.BioConversionError, match="sem B-"):
        bio.bio_sentence_to_gliner(["de", "Contas"], ["I-ORG", "I-ORG"])


def test_rejects_mismatched_lengths():
    with pytest.raises(bio.BioConversionError, match="mesmo tamanho"):
        bio.bio_sentence_to_gliner(["O", "TCU"], ["O"])


def test_convert_bio_json_list_and_custom_map():
    payload = {
        "label_map": {"ORG": "órgão"},
        "sentences": [
            {"tokens": ["A", "Petrobras"], "ner_tags": ["O", "B-ORG"]},
            {"tokens": ["Maria", "saiu"], "ner_tags": ["B-PESSOA", "O"]},
        ],
    }
    train, val, label_map = bio.convert_bio_json(payload, val_ratio=0.0)
    assert label_map["ORG"] == "órgão"
    all_examples = train + val
    org = next(item for item in all_examples if item["ner"] and item["ner"][0][2] == "órgão")
    assert org["ner"][0][:2] == [1, 1]
    person = next(item for item in all_examples if item["ner"] and item["ner"][0][2] == "pessoa")
    assert person["tokenized_text"][0] == "Maria"


def test_explicit_validation_split():
    payload = {
        "sentences": [
            {"tokens": ["A", "lei"], "ner_tags": ["O", "O"]},
        ],
        "validation": [
            {"tokens": ["B", "decreto"], "ner_tags": ["O", "B-NORMA"]},
        ],
    }
    train, val, _ = bio.convert_bio_json(payload)
    assert len(train) == 1
    assert val[0]["ner"] == [[1, 1, "norma"]]
