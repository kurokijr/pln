"""Backends de NER para o estudo de entidades (itens 29 e 30).

spaCy 3.7+ com pt_core_news_md é o motor padrão (CPU, português).
GLiNER fica como gancho (NER_BACKEND=gliner) para uma versão futura.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Callable, List, Protocol, TypedDict

SPACY_MODEL = os.getenv("SPACY_MODEL", "pt_core_news_md")

# Palavras de 2–6 letras em maiúsculas que não são siglas úteis.
SIGLA_STOP = {
    "DE", "DA", "DO", "EM", "NO", "NA", "OS", "AS", "UM", "AO", "SE", "OU",
    "POR", "COM", "PARA", "THE", "AND", "OR", "TO", "OF", "IN", "ON",
    "PDF", "DOC", "TXT", "HTTP", "HTTPS", "WWW", "HTML", "JSON", "XML",
    "ART", "INC", "PAR", "CAP", "SEC", "ITEM", "ANEXO",
}

LEI_RE = re.compile(
    r"\bLei\s+(?:n[ºo°.]?\s*)?\d{1,5}(?:\.\d{3})*(?:/\d{2,4})?\b",
    re.IGNORECASE,
)
NORMA_RE = re.compile(
    r"\b(?:Decreto|Portaria|Instru[cç][aã]o\s+Normativa|\bIN\b)\s+"
    r"(?:n[ºo°.]?\s*)?\d{1,5}(?:\.\d{3})*(?:/\d{2,4})?\b",
    re.IGNORECASE,
)
LICITACAO_RE = re.compile(
    r"\b(?:PC|PE|TP|Preg[aã]o(?:\s+Eletr[oô]nico)?|Concorr[eê]ncia|Dispensa)"
    r"\s*(?:n[ºo°.]?\s*)?\d{1,5}\s*/\s*\d{2,4}\b",
    re.IGNORECASE,
)
CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
PROCESSO_RE = re.compile(
    r"\b(?:\d{3,7}\.\d{3}/\d{4}|\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b"
)
SIGLA_RE = re.compile(r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]{3,6}\b")

_NLP = None


class EntitySpan(TypedDict):
    text: str
    label: str
    start: int
    end: int
    source: str


class EntityExtractor(Protocol):
    def __call__(self, text: str) -> List[EntitySpan]:
        ...


def normalize_key(text: str) -> str:
    """Chave de comparação: minúsculas, sem acento, espaços colapsados."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in nfkd if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def extract_regex_entities(text: str) -> List[EntitySpan]:
    """Extrai códigos, normas, processos, CNPJ e siglas por regex."""
    if not text or not isinstance(text, str):
        return []

    spans: List[EntitySpan] = []
    for pattern in (LEI_RE, NORMA_RE, LICITACAO_RE, CNPJ_RE, PROCESSO_RE):
        for match in pattern.finditer(text):
            spans.append(
                {
                    "text": match.group(0).strip(),
                    "label": "CODIGO",
                    "start": match.start(),
                    "end": match.end(),
                    "source": "regex",
                }
            )

    occupied = {(span["start"], span["end"]) for span in spans}
    for match in SIGLA_RE.finditer(text):
        token = match.group(0)
        if token in SIGLA_STOP:
            continue
        interval = (match.start(), match.end())
        if any(not (interval[1] <= start or interval[0] >= end) for start, end in occupied):
            continue
        spans.append(
            {
                "text": token,
                "label": "SIGLA",
                "start": match.start(),
                "end": match.end(),
                "source": "regex",
            }
        )
    return _dedupe_spans(spans)


def _load_spacy():
    """Carrega pt_core_news_md (download lazy se o modelo não estiver instalado)."""
    global _NLP
    if _NLP is not None:
        return _NLP

    import spacy

    disable = ["parser", "lemmatizer", "morphologizer", "senter"]
    try:
        _NLP = spacy.load(SPACY_MODEL, disable=disable)
    except OSError:
        from spacy.cli import download

        download(SPACY_MODEL)
        _NLP = spacy.load(SPACY_MODEL, disable=disable)
    return _NLP


def extract_spacy_entities(text: str) -> List[EntitySpan]:
    """NER spaCy: PER, ORG, LOC, MISC."""
    if not text or not isinstance(text, str):
        return []
    nlp = _load_spacy()
    doc = nlp(text[:100000])
    spans: List[EntitySpan] = []
    for ent in doc.ents:
        label = ent.label_.upper()
        if label not in {"PER", "ORG", "LOC", "MISC"}:
            continue
        spans.append(
            {
                "text": ent.text.strip(),
                "label": label,
                "start": ent.start_char,
                "end": ent.end_char,
                "source": "spacy",
            }
        )
    return _dedupe_spans(spans)


def extract_gliner_entities(text: str) -> List[EntitySpan]:
    """Gancho para GLiNER — não implementado nesta versão."""
    raise NotImplementedError(
        "Motor GLiNER ainda não está nesta versão. Use NER_BACKEND=spacy."
    )


def get_entity_extractor() -> Callable[[str], List[EntitySpan]]:
    """Retorna o extrator configurado em NER_BACKEND (padrão: spacy)."""
    backend = os.getenv("NER_BACKEND", "spacy").strip().lower()
    if backend == "gliner":
        return extract_gliner_entities
    if backend and backend != "spacy":
        raise ValueError(f"NER_BACKEND inválido: {backend}. Use spacy ou gliner.")
    return extract_spacy_entities


def extract_all_entities(
    text: str,
    ner_extractor: Callable[[str], List[EntitySpan]] | None = None,
) -> List[EntitySpan]:
    """Une regex (códigos/siglas) com o backend NER. Regex vence em sobreposição."""
    regex_spans = extract_regex_entities(text)
    extractor = ner_extractor if ner_extractor is not None else get_entity_extractor()
    ner_spans = extractor(text)
    occupied = [(span["start"], span["end"]) for span in regex_spans]
    merged = list(regex_spans)
    for span in ner_spans:
        interval = (span["start"], span["end"])
        overlaps = any(
            not (interval[1] <= start or interval[0] >= end) for start, end in occupied
        )
        if overlaps:
            continue
        merged.append(span)
    return _dedupe_spans(merged)


def _dedupe_spans(spans: List[EntitySpan]) -> List[EntitySpan]:
    """Remove duplicatas pela chave normalizada, preferindo o span mais longo."""
    best: dict[str, EntitySpan] = {}
    for span in sorted(spans, key=lambda item: len(item["text"]), reverse=True):
        key = normalize_key(span["text"])
        if not key or len(key) < 2:
            continue
        if key not in best:
            best[key] = span
    return list(best.values())
