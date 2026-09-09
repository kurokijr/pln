from src.ner_backends import extract_gliner_entities, extract_regex_entities, get_entity_extractor, normalize_key


def test_lei_numero():
    spans = extract_regex_entities("Aplicar a Lei 8.666 nas licitações.")
    texts = [span["text"] for span in spans]
    assert any("8.666" in text for text in texts)
    assert all(span["label"] == "CODIGO" for span in spans if "8.666" in span["text"])


def test_lei_com_ano():
    spans = extract_regex_entities("A Lei nº 14.133/2021 revogou a anterior.")
    assert any("14.133/2021" in span["text"] for span in spans)


def test_pc_licitacao():
    spans = extract_regex_entities("O edital PC 1/2018 trata de locação de veículos.")
    match = next(span for span in spans if span["label"] == "CODIGO")
    assert "1/2018" in match["text"]


def test_cnpj():
    spans = extract_regex_entities("Fornecedor inscrito no 12.345.678/0001-99.")
    assert any(span["label"] == "CODIGO" and "12.345.678/0001-99" in span["text"] for span in spans)


def test_processo_administrativo():
    spans = extract_regex_entities("Autos 001.234/2024 em tramitação.")
    assert any("001.234/2024" in span["text"] for span in spans)


def test_sigla_tcu():
    spans = extract_regex_entities("O TCU analisou as contas do órgão.")
    assert any(span["text"] == "TCU" and span["label"] == "SIGLA" for span in spans)


def test_sigla_stopword_art_ignored():
    spans = extract_regex_entities("Conforme ART 5 do regulamento.")
    assert not any(span["text"] == "ART" for span in spans)


def test_normalize_key_strips_accents():
    assert normalize_key("Tribunal de Contas") == "tribunal de contas"
    assert normalize_key("Órgão") == "orgao"


def test_gliner_stub_raises():
    try:
        extract_gliner_entities("texto")
        assert False, "deveria levantar NotImplementedError"
    except NotImplementedError as error:
        assert "GLiNER" in str(error)


def test_invalid_backend_raises(monkeypatch):
    monkeypatch.setenv("NER_BACKEND", "bertimbau")
    try:
        get_entity_extractor()
        assert False, "deveria levantar ValueError"
    except ValueError as error:
        assert "bertimbau" in str(error)
