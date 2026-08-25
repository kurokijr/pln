from src.entity_study_service import (
    analyze_chunks,
    clamp_neighbor_top,
    extractor_from_span_lists,
    map_category,
    ngram_size_of,
    _top_neighbors,
)
from src.ner_backends import EntitySpan


def mock_ner(text: str) -> list[EntitySpan]:
    spans: list[EntitySpan] = []
    needle = "Tribunal de Contas"
    start = text.find(needle)
    if start >= 0:
        spans.append(
            {
                "text": needle,
                "label": "ORG",
                "start": start,
                "end": start + len(needle),
                "source": "spacy",
            }
        )
    return spans


def test_map_category_codigo():
    assert map_category("CODIGO") == "código"
    assert map_category("SIGLA") == "sigla"
    assert map_category("PER") == "nome próprio"
    assert map_category("ORG") == "nome próprio"
    assert map_category("LOC") == "nome próprio"
    assert map_category("MISC") == "lexical"
    assert map_category("TFIDF", 1) == "lexical"
    assert map_category("TFIDF", 3) == "frase exata"


def test_ngram_size_of():
    assert ngram_size_of("PC") == 1
    assert ngram_size_of("locação de veículos") >= 2


def test_analyze_chunks_ranks_named_entity_and_code():
    chunks = [
        {
            "point_id": "point-a",
            "file_name": "edital.pdf",
            "content": (
                "O Tribunal de Contas analisou o edital PC 1/2018 "
                "sobre locação de veículos."
            ),
        },
        {
            "point_id": "point-b",
            "file_name": "parecer.pdf",
            "content": (
                "Despesas apresentadas em duplicidade no mesmo órgão. "
                "O Tribunal de Contas reiterou a vedação."
            ),
        },
        {
            "point_id": "point-c",
            "file_name": "manual.pdf",
            "content": "Regras gerais para aluguel de automóveis na administração.",
        },
    ]

    result = analyze_chunks(chunks, top_n=20, extract_entities_fn=mock_ner)
    draft = result["golden_set_draft"]
    queries = [item["query"] for item in draft]
    categories = {item["query"]: item["category"] for item in draft}

    assert result["chunks_analyzed"] == 3
    assert any("Tribunal de Contas" in query for query in queries)
    org_item = next(item for item in draft if "Tribunal de Contas" in item["query"])
    assert org_item["category"] == "nome próprio"
    assert org_item["label"] == "ORG"
    assert "point-a" in org_item["candidate_points"]
    assert org_item["source"] in {"ner+tfidf", "spacy", "regex"}

    codigo = next((item for item in draft if item["category"] == "código"), None)
    assert codigo is not None
    assert "1/2018" in codigo["query"]

    assert "ORG" in result["entities"]
    assert any(row["text"] == "Tribunal de Contas" for row in result["entities"]["ORG"])
    assert result["study_groups"]
    assert categories.get("Tribunal de Contas") == "nome próprio"


def test_analyze_chunks_empty():
    result = analyze_chunks([], top_n=10, extract_entities_fn=mock_ner)
    assert result["chunks_analyzed"] == 0
    assert result["golden_set_draft"] == []


def test_top_neighbors_skips_stopwords():
    corpus = [
        ["a", "extrusão", "de", "plástico", "ocorre"],
        ["estudo", "de", "extrusão", "de", "metal"],
        ["revisão", "sobre", "extrusão", "de", "polímeros"],
        ["the", "extrusão", "of", "plástico"],
    ]
    before, after = _top_neighbors(corpus, "extrusão", limit=2)
    assert len(before) <= 2
    assert len(after) <= 2
    before5, after5 = _top_neighbors(corpus, "extrusão")
    assert len(before5) <= 5
    assert len(after5) <= 5
    assert "de" not in after
    assert "sobre" not in before
    assert "the" not in before
    assert "of" not in after
    assert "plástico" in after
    assert "estudo" in before or "revisão" in before


def test_clamp_neighbor_top():
    assert clamp_neighbor_top(None) == 5
    assert clamp_neighbor_top("8") == 8
    assert clamp_neighbor_top(0) == 1
    assert clamp_neighbor_top(99) == 30


def test_tfidf_terms_include_neighbor_context():
    chunks = [
        {
            "point_id": "p1",
            "file_name": "a.pdf",
            "content": "A extrusão do plástico ocorre na indústria. A extrusão de metal também.",
        },
        {
            "point_id": "p2",
            "file_name": "b.pdf",
            "content": "Estudo de extrusão de polímeros na escola politécnica.",
        },
        {
            "point_id": "p3",
            "file_name": "c.pdf",
            "content": "Revisão bibliográfica sobre extrusão de plástico.",
        },
    ]
    result = analyze_chunks(
        chunks, top_n=20, extract_entities_fn=lambda _text: [], neighbor_top=8
    )
    row = next(item for item in result["tfidf_terms"] if item["text"] == "extrusão")
    assert result["neighbor_top"] == 8
    assert "do" not in row["before"]
    assert "de" not in row["after"]
    assert "a" not in row["before"]
    assert "plástico" in row["after"] or "metal" in row["after"] or "polímeros" in row["after"]
    assert len(row["before"]) <= 8
    assert len(row["after"]) <= 8


def test_extractor_from_span_lists_feeds_analyze_chunks():
    chunks = [
        {
            "point_id": "g1",
            "file_name": "polimeros.pdf",
            "content": "A extrusão de plástico ocorre na indústria.",
        },
        {
            "point_id": "g2",
            "file_name": "tcu.pdf",
            "content": "O Tribunal de Contas analisou o processo.",
        },
    ]
    span_lists = [
        [
            {
                "text": "extrusão",
                "label": "PROCESSO",
                "start": 2,
                "end": 10,
                "source": "gliner",
            }
        ],
        [
            {
                "text": "Tribunal de Contas",
                "label": "ORG",
                "start": 2,
                "end": 20,
                "source": "bertimbau",
            }
        ],
    ]
    result = analyze_chunks(
        chunks,
        top_n=20,
        extract_entities_fn=extractor_from_span_lists(span_lists),
        backend="gliner_bert",
    )
    assert result["backend"] == "gliner_bert"
    assert result["chunks_analyzed"] == 2
    assert any(row["text"] == "extrusão" for row in result["entities"]["PROCESSO"])
    assert any(row["text"] == "Tribunal de Contas" for row in result["entities"]["ORG"])
    org_item = next(item for item in result["golden_set_draft"] if "Tribunal de Contas" in item["query"])
    assert org_item["category"] == "nome próprio"
