"""Estudo TF-IDF + NER: candidatos ao golden set (item 29) e study_group (item 30)."""

from __future__ import annotations

import math
import os
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

from src.ner_backends import (
    EntitySpan,
    extract_all_entities,
    get_entity_extractor,
    normalize_key,
)
from src.sparse_encoder import PT_STOPWORDS, TOKEN_RE

DEFAULT_MAX_CHUNKS = 2000
DEFAULT_TOP_N = 50
MAX_CANDIDATE_POINTS = 20
CONTEXT_NEIGHBORS = 5
CONTEXT_NEIGHBORS_MAX = 30

CONTEXT_STOPWORDS = PT_STOPWORDS | {
    "the", "of", "and", "in", "to", "for", "with", "on", "at", "by", "from",
    "an", "or", "as", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "it", "its", "we", "our", "they",
    "their", "not", "but", "if", "then", "than", "so", "such", "via", "etc",
    "sobre", "sob", "desde", "durante", "contra", "após", "antes", "ainda",
    "através", "conforme", "segundo", "mediante", "perante", "após",
    "dum", "duma", "num", "numa", "pelos", "pelas", "pra", "pro",
    "este", "esta", "estes", "estas", "esses", "essas", "aquele", "aquela",
    "aqueles", "aquelas", "ele", "ela", "eles", "elas", "nós", "vos",
    "seu", "sua", "seus", "suas", "meus", "minhas", "teu", "tua",
    "todo", "toda", "todos", "todas", "outro", "outra", "outros", "outras",
    "cada", "qualquer", "apenas", "somente", "já", "também", "pouco",
    "menos", "bem", "mal", "onde", "quando", "porque", "pois", "assim",
}

TYPE_WEIGHTS = {
    "CODIGO": 3.0,
    "SIGLA": 2.8,
    "PER": 2.5,
    "ORG": 2.5,
    "INSTITUICAO": 2.4,
    "LOC": 2.0,
    "NORMA": 2.2,
    "MATERIAL": 1.8,
    "PROCESSO": 1.8,
    "MISC": 1.5,
    "TFIDF": 1.0,
}

LABEL_GROUPS = (
    "PER",
    "ORG",
    "LOC",
    "MISC",
    "CODIGO",
    "SIGLA",
    "MATERIAL",
    "PROCESSO",
    "NORMA",
    "INSTITUICAO",
    "TFIDF",
)


def map_category(label: str, ngram_size: int = 1) -> str:
    """Mapeia o rótulo NER/regex para as categorias do item 29.29."""
    if label == "CODIGO":
        return "código"
    if label == "SIGLA":
        return "sigla"
    if label in {"PER", "ORG", "LOC", "INSTITUICAO"}:
        return "nome próprio"
    if label == "NORMA":
        return "código"
    if ngram_size > 1:
        return "frase exata"
    return "lexical"


def ngram_size_of(text: str) -> int:
    return max(1, len(TOKEN_RE.findall(text.lower())))


def _tokenize_for_tfidf(text: str) -> List[str]:
    return TOKEN_RE.findall((text or "").lower())


def _sklearn_idf(n_docs: int, df: int) -> float:
    return math.log((1.0 + n_docs) / (1.0 + df)) + 1.0


def _source_label(has_ner: bool, has_tfidf: bool, ner_source: str) -> str:
    if has_ner and has_tfidf:
        return "ner+tfidf"
    if has_ner:
        return ner_source
    return "tfidf"


def clamp_neighbor_top(value: Any, default: int = CONTEXT_NEIGHBORS) -> int:
    """Limita o top de vizinhos Antes/Depois (1–30)."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, CONTEXT_NEIGHBORS_MAX))


def analyze_chunks(
    chunks: List[Dict[str, Any]],
    top_n: int = DEFAULT_TOP_N,
    extract_entities_fn: Optional[Callable[[str], List[EntitySpan]]] = None,
    backend: Optional[str] = None,
    neighbor_top: int = CONTEXT_NEIGHBORS,
) -> Dict[str, Any]:
    """Funde TF-IDF e NER sobre chunks já lidos (sem Qdrant)."""
    top_n = max(1, min(int(top_n), 200))
    neighbor_top = clamp_neighbor_top(neighbor_top)
    texts = [str(chunk.get("content") or "") for chunk in chunks]
    n_docs = len(texts)

    tfidf_by_doc, global_idf = _fit_tfidf(texts)
    ner_extractor = extract_entities_fn or get_entity_extractor()

    aggregated: Dict[str, Dict[str, Any]] = {}
    for index, chunk in enumerate(chunks):
        point_id = str(chunk.get("point_id") or "")
        file_name = str(chunk.get("file_name") or "")
        text = texts[index]
        row_tfidf = tfidf_by_doc[index] if index < len(tfidf_by_doc) else {}

        spans = extract_all_entities(text, ner_extractor=ner_extractor)
        seen_keys = set()
        for span in spans:
            key = normalize_key(span["text"])
            if not key:
                continue
            seen_keys.add(key)
            tfidf_max = _lookup_tfidf(key, span["text"], row_tfidf)
            _accumulate(
                aggregated,
                key=key,
                display=span["text"].strip(),
                label=span["label"],
                ner_source=span["source"],
                has_ner=True,
                tfidf_max=tfidf_max,
                point_id=point_id,
                file_name=file_name,
            )

        ranked_terms = sorted(row_tfidf.items(), key=lambda item: item[1], reverse=True)
        added_tfidf = 0
        for term, value in ranked_terms:
            if added_tfidf >= 8:
                break
            if ngram_size_of(term) > 1:
                continue
            key = normalize_key(term)
            if not key or key in seen_keys:
                continue
            if key in CONTEXT_STOPWORDS or len(key) < 3:
                continue
            _accumulate(
                aggregated,
                key=key,
                display=term,
                label="TFIDF",
                ner_source="tfidf",
                has_ner=False,
                tfidf_max=value,
                point_id=point_id,
                file_name=file_name,
            )
            added_tfidf += 1

    ranked = []
    for item in aggregated.values():
        df = len(item["point_ids"])
        idf = global_idf.get(item["key"], _sklearn_idf(n_docs, df))
        weight = TYPE_WEIGHTS.get(item["label"], 1.0)
        score = float(item["tfidf_max"]) * float(idf) * weight
        ngrams = ngram_size_of(item["display"])
        ranked.append(
            {
                "text": item["display"],
                "label": item["label"],
                "category": map_category(item["label"], ngrams),
                "score": round(score, 4),
                "tfidf_max": round(float(item["tfidf_max"]), 4),
                "idf": round(float(idf), 4),
                "df": df,
                "source": _source_label(item["has_ner"], item["has_tfidf"], item["ner_source"]),
                "candidate_points": item["point_ids"][:MAX_CANDIDATE_POINTS],
                "file_names": sorted(item["file_names"])[:10],
            }
        )

    ranked.sort(key=lambda row: row["score"], reverse=True)
    ner_first = [row for row in ranked if row["label"] != "TFIDF"]
    tfidf_fill = [row for row in ranked if row["label"] == "TFIDF"]
    top_entities = (ner_first + tfidf_fill)[:top_n]
    golden_set_draft = []
    for offset, entity in enumerate(top_entities, start=1):
        golden_set_draft.append(
            {
                "query_id": f"auto-{offset:03d}",
                "category": entity["category"],
                "query": entity["text"],
                "candidate_points": entity["candidate_points"],
                "source": entity["source"],
                "label": entity["label"],
                "score": entity["score"],
            }
        )

    entities_by_label = {label: [] for label in LABEL_GROUPS}
    for entity in ranked:
        label = entity["label"] if entity["label"] in entities_by_label else "MISC"
        if len(entities_by_label[label]) < top_n:
            entities_by_label[label].append(entity)

    tfidf_terms = [row for row in ranked if row["label"] == "TFIDF"][:top_n]
    tokenized_corpus = [_content_tokens(text) for text in texts]
    for row in tfidf_terms:
        before, after = _top_neighbors(
            tokenized_corpus, row["text"], limit=neighbor_top
        )
        row["before"] = before
        row["after"] = after
    study_groups = _suggest_study_groups(ranked)

    return {
        "chunks_analyzed": n_docs,
        "backend": (backend or os.getenv("NER_BACKEND", "spacy").strip().lower() or "spacy"),
        "neighbor_top": neighbor_top,
        "entities": entities_by_label,
        "tfidf_terms": tfidf_terms,
        "golden_set_draft": golden_set_draft,
        "study_groups": study_groups,
    }


def run_entity_study(
    vector_store: Any,
    collection_name: str,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    top_n: int = DEFAULT_TOP_N,
    neighbor_top: int = CONTEXT_NEIGHBORS,
    extract_entities_fn: Optional[Callable[[str], List[EntitySpan]]] = None,
) -> Dict[str, Any]:
    """Lê chunks no Qdrant (somente payload) e devolve o relatório de estudo."""
    max_chunks = max(1, min(int(max_chunks), DEFAULT_MAX_CHUNKS))
    chunks = vector_store.scroll_chunk_payloads(collection_name, max_chunks=max_chunks)
    result = analyze_chunks(
        chunks,
        top_n=top_n,
        extract_entities_fn=extract_entities_fn,
        neighbor_top=neighbor_top,
    )
    result["collection_name"] = collection_name
    return result


def extractor_from_span_lists(
    span_lists: List[List[EntitySpan]],
) -> Callable[[str], List[EntitySpan]]:
    """Devolve um extrator que consome listas de spans já extraídas em lote."""
    cursor = {"index": 0}

    def extract(_text: str) -> List[EntitySpan]:
        index = cursor["index"]
        cursor["index"] += 1
        if index >= len(span_lists):
            return []
        return span_lists[index]

    return extract


def run_gliner_entity_study(
    vector_store: Any,
    collection_name: str,
    max_chunks: int = 200,
    top_n: int = DEFAULT_TOP_N,
    neighbor_top: int = CONTEXT_NEIGHBORS,
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Estudo TF-IDF local + NER remoto (GLiNER/BERTimbau)."""
    from src.gliner_bert_client import extract as gliner_extract

    max_chunks = max(1, min(int(max_chunks), DEFAULT_MAX_CHUNKS))
    chunks = vector_store.scroll_chunk_payloads(collection_name, max_chunks=max_chunks)
    texts = [str(chunk.get("content") or "") for chunk in chunks]
    span_lists = gliner_extract(texts, labels=labels) if texts else []
    result = analyze_chunks(
        chunks,
        top_n=top_n,
        extract_entities_fn=extractor_from_span_lists(span_lists),
        backend="gliner_bert",
        neighbor_top=neighbor_top,
    )
    result["collection_name"] = collection_name
    return result


def _fit_tfidf(texts: List[str]) -> tuple[List[Dict[str, float]], Dict[str, float]]:
    if not texts:
        return [], {}

    from sklearn.feature_extraction.text import TfidfVectorizer

    max_df: float | int = 0.9 if len(texts) >= 5 else 1.0
    vectorizer = TfidfVectorizer(
        tokenizer=_tokenize_for_tfidf,
        preprocessor=lambda value: value or "",
        token_pattern=None,
        ngram_range=(1, 3),
        min_df=1,
        max_df=max_df,
        stop_words=sorted(PT_STOPWORDS),
        lowercase=False,
    )
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return [{} for _ in texts], {}

    names = vectorizer.get_feature_names_out()
    idf_map = {
        str(name): float(vectorizer.idf_[index]) for index, name in enumerate(names)
    }
    rows: List[Dict[str, float]] = []
    for row_index in range(matrix.shape[0]):
        row = matrix.getrow(row_index)
        values: Dict[str, float] = {}
        for col_index, value in zip(row.indices, row.data):
            values[str(names[col_index])] = float(value)
        rows.append(values)
    return rows, idf_map


def _is_content_token(token: str) -> bool:
    return bool(token) and len(token) > 1 and token not in CONTEXT_STOPWORDS


def _content_tokens(text: str) -> List[str]:
    return TOKEN_RE.findall((text or "").lower())


def _top_neighbors(
    tokenized_corpus: List[List[str]],
    term: str,
    limit: int = CONTEXT_NEIGHBORS,
) -> tuple[List[str], List[str]]:
    """Top tokens imediatos à esquerda e à direita, sem stopwords simples."""
    key = normalize_key(term)
    if not key:
        return [], []
    before: Counter[str] = Counter()
    after: Counter[str] = Counter()
    for tokens in tokenized_corpus:
        for index, token in enumerate(tokens):
            if normalize_key(token) != key:
                continue
            left = index - 1
            while left >= 0:
                neighbor = tokens[left]
                if _is_content_token(neighbor) and normalize_key(neighbor) != key:
                    before[neighbor] += 1
                    break
                left -= 1
            right = index + 1
            while right < len(tokens):
                neighbor = tokens[right]
                if _is_content_token(neighbor) and normalize_key(neighbor) != key:
                    after[neighbor] += 1
                    break
                right += 1
    return (
        [token for token, _count in before.most_common(limit)],
        [token for token, _count in after.most_common(limit)],
    )


def _lookup_tfidf(key: str, display: str, row_tfidf: Dict[str, float]) -> float:
    if key in row_tfidf:
        return row_tfidf[key]
    lowered = display.lower().strip()
    if lowered in row_tfidf:
        return row_tfidf[lowered]
    tokens = TOKEN_RE.findall(key)
    scores = [row_tfidf[token] for token in tokens if token in row_tfidf]
    return max(scores) if scores else 0.0


def _accumulate(
    aggregated: Dict[str, Dict[str, Any]],
    key: str,
    display: str,
    label: str,
    ner_source: str,
    has_ner: bool,
    tfidf_max: float,
    point_id: str,
    file_name: str,
) -> None:
    current = aggregated.get(key)
    if current is None:
        aggregated[key] = {
            "key": key,
            "display": display,
            "label": label,
            "ner_source": ner_source,
            "has_ner": has_ner,
            "has_tfidf": tfidf_max > 0,
            "tfidf_max": tfidf_max,
            "point_ids": [point_id] if point_id else [],
            "file_names": {file_name} if file_name else set(),
        }
        return

    if has_ner and not current["has_ner"]:
        current["label"] = label
        current["display"] = display
        current["ner_source"] = ner_source
    elif has_ner and TYPE_WEIGHTS.get(label, 1.0) > TYPE_WEIGHTS.get(current["label"], 1.0):
        current["label"] = label
        current["display"] = display
        current["ner_source"] = ner_source
    current["has_ner"] = current["has_ner"] or has_ner
    current["has_tfidf"] = current["has_tfidf"] or tfidf_max > 0
    current["tfidf_max"] = max(current["tfidf_max"], tfidf_max)
    if point_id and point_id not in current["point_ids"]:
        current["point_ids"].append(point_id)
    if file_name:
        current["file_names"].add(file_name)


def _suggest_study_groups(ranked: List[Dict[str, Any]], limit: int = 15) -> List[Dict[str, Any]]:
    """Entidades que atravessam documentos: sugestão de study_group (item 30)."""
    groups = []
    for entity in ranked:
        if entity["label"] == "TFIDF":
            continue
        file_count = len(entity.get("file_names") or [])
        if file_count < 1:
            continue
        groups.append(
            {
                "study_group": entity["text"],
                "label": entity["label"],
                "category": entity["category"],
                "document_count": file_count,
                "chunk_count": entity["df"],
                "score": entity["score"],
            }
        )
        if len(groups) >= limit:
            break
    return groups
