"""Cliente HTTP do gliner-bert: mocks, sem torch."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from src.gliner_bert_client import GlinerBertUnavailable, extract, health, list_models, reload_model, start_train


def test_health_flag_false_returns_unavailable():
    with patch("src.gliner_bert_client.config") as config:
        config.GLINER_BERT = False
        payload = health()
    assert payload["available"] is False
    assert payload["cuda_available"] is False
    assert payload["train_available"] is False
    assert "GLINER_BERT=false" in payload["reason"]


def test_extract_flag_false_raises():
    with patch("src.gliner_bert_client.config") as config:
        config.GLINER_BERT = False
        with pytest.raises(GlinerBertUnavailable):
            extract(["texto"])


def test_health_ok_when_models_loaded():
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.content = b'{"status":"ok"}'
    response.json.return_value = {"status": "ok", "models_loaded": True}
    with (
        patch("src.gliner_bert_client.config") as config,
        patch("src.gliner_bert_client.requests.get", return_value=response) as get,
    ):
        config.GLINER_BERT = True
        config.GLINER_BERT_URL = "http://gliner-bert:8080"
        config.GLINER_BERT_TIMEOUT = 120
        payload = health()
    get.assert_called_once()
    assert payload["available"] is True
    assert payload["models_loaded"] is True


def test_health_down_container():
    with (
        patch("src.gliner_bert_client.config") as config,
        patch(
            "src.gliner_bert_client.requests.get",
            side_effect=requests.ConnectionError("down"),
        ),
    ):
        config.GLINER_BERT = True
        config.GLINER_BERT_URL = "http://gliner-bert:8080"
        config.GLINER_BERT_TIMEOUT = 120
        payload = health()
    assert payload["available"] is False
    assert "down" in payload["reason"]


def test_extract_converts_batch_spans():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "spans": [
            [
                {
                    "text": "Tribunal de Contas",
                    "label": "ORG",
                    "start": 2,
                    "end": 20,
                    "source": "bertimbau",
                    "score": 0.9,
                }
            ],
            [
                {
                    "text": "extrusão",
                    "label": "MATERIAL",
                    "start": 10,
                    "end": 18,
                    "source": "gliner",
                    "score": 0.7,
                }
            ],
        ]
    }
    with (
        patch("src.gliner_bert_client.config") as config,
        patch("src.gliner_bert_client.requests.post", return_value=response),
    ):
        config.GLINER_BERT = True
        config.GLINER_BERT_URL = "http://gliner-bert:8080"
        config.GLINER_BERT_TIMEOUT = 120
        result = extract(["a", "b"], labels=["organização", "material"])
    assert len(result) == 2
    assert result[0][0]["text"] == "Tribunal de Contas"
    assert result[0][0]["source"] == "bertimbau"
    assert result[1][0]["label"] == "MATERIAL"


def test_start_train_flag_false_raises():
    with patch("src.gliner_bert_client.config") as config:
        config.GLINER_BERT = False
        with pytest.raises(GlinerBertUnavailable):
            start_train({"sentences": []})


def test_start_train_posts_json_and_returns_job():
    response = Mock()
    response.status_code = 200
    response.content = b'{"success":true}'
    response.json.return_value = {
        "success": True,
        "state": "running",
        "job_id": "abc123",
        "message": "iniciando",
    }
    with (
        patch("src.gliner_bert_client.config") as config,
        patch("src.gliner_bert_client.requests.post", return_value=response) as post,
    ):
        config.GLINER_BERT = True
        config.GLINER_BERT_URL = "http://gliner-bert:8080"
        config.GLINER_BERT_TIMEOUT = 120
        result = start_train({"sentences": [{"tokens": ["A"], "ner_tags": ["O"]}]})
    post.assert_called_once()
    assert result["state"] == "running"
    assert result["job_id"] == "abc123"


def test_list_models_flag_false():
    with patch("src.gliner_bert_client.config") as config:
        config.GLINER_BERT = False
        payload = list_models()
    assert payload["available"] is False
    assert payload["checkpoints"] == []


def test_list_models_ok():
    response = Mock()
    response.status_code = 200
    response.content = b"{}"
    response.json.return_value = {
        "current_id": "hub",
        "checkpoints": [{"id": "gliner-bertimbau-pt", "name": "gliner-bertimbau-pt"}],
        "hub": {"id": "hub", "label": "Padrão Hub"},
    }
    with (
        patch("src.gliner_bert_client.config") as config,
        patch("src.gliner_bert_client.requests.get", return_value=response) as get,
    ):
        config.GLINER_BERT = True
        config.GLINER_BERT_URL = "http://gliner-bert:8080"
        config.GLINER_BERT_TIMEOUT = 120
        payload = list_models()
    get.assert_called_once()
    assert payload["available"] is True
    assert payload["checkpoints"][0]["id"] == "gliner-bertimbau-pt"


def test_reload_posts_id():
    response = Mock()
    response.status_code = 200
    response.content = b"{}"
    response.json.return_value = {"success": True, "current_id": "gliner-bertimbau-pt"}
    with (
        patch("src.gliner_bert_client.config") as config,
        patch("src.gliner_bert_client.requests.post", return_value=response) as post,
    ):
        config.GLINER_BERT = True
        config.GLINER_BERT_URL = "http://gliner-bert:8080"
        config.GLINER_BERT_TIMEOUT = 120
        result = reload_model("gliner-bertimbau-pt")
    post.assert_called_once()
    assert post.call_args.kwargs["json"]["id"] == "gliner-bertimbau-pt"
    assert result["current_id"] == "gliner-bertimbau-pt"


def test_reload_flag_false_raises():
    with patch("src.gliner_bert_client.config") as config:
        config.GLINER_BERT = False
        with pytest.raises(GlinerBertUnavailable):
            reload_model("hub")
