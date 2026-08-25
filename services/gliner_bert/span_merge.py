"""Fusão de spans BERTimbau + GLiNER (sem torch — testável no CI)."""

from __future__ import annotations

from typing import Dict, List, TypedDict

CLASSIC_LABELS = {"PER", "ORG", "LOC"}

LABEL_MAP = {
    "PESSOA": "PER",
    "PERSON": "PER",
    "PER": "PER",
    "pessoa": "PER",
    "ORGANIZACAO": "ORG",
    "ORGANIZAÇÃO": "ORG",
    "ORGANIZATION": "ORG",
    "ORG": "ORG",
    "organização": "ORG",
    "organizacao": "ORG",
    "LOCALIDADE": "LOC",
    "LOCAL": "LOC",
    "LOC": "LOC",
    "GPE": "LOC",
    "PLACE": "LOC",
    "local": "LOC",
    "MISC": "MISC",
    "TEMPO": "MISC",
    "TIME": "MISC",
    "LEGISLACAO": "NORMA",
    "LEGISLAÇÃO": "NORMA",
    "JURISPRUDENCIA": "NORMA",
    "JURISPRUDÊNCIA": "NORMA",
    "norma": "NORMA",
    "NORMA": "NORMA",
    "material": "MATERIAL",
    "MATERIAL": "MATERIAL",
    "processo": "PROCESSO",
    "PROCESSO": "PROCESSO",
    "instituição": "INSTITUICAO",
    "instituicao": "INSTITUICAO",
    "INSTITUICAO": "INSTITUICAO",
    "instituição": "INSTITUICAO",
}


class Span(TypedDict, total=False):
    text: str
    label: str
    start: int
    end: int
    source: str
    score: float


def normalize_label(label: str) -> str:
    """Mapeia rótulos PT/EN para PER/ORG/LOC ou tipos abertos do GLiNER."""
    if not label:
        return "MISC"
    raw = label.strip()
    mapped = LABEL_MAP.get(raw) or LABEL_MAP.get(raw.upper()) or LABEL_MAP.get(raw.lower())
    if mapped:
        return mapped
    return raw.upper().replace(" ", "_")


def _overlaps(left: Span, right: Span) -> bool:
    return not (left["end"] <= right["start"] or left["start"] >= right["end"])


def merge_span_sources(
    bertimbau_spans: List[Span],
    gliner_spans: List[Span],
) -> List[Span]:
    """BERTimbau vence em PER/ORG/LOC sobrepostos; GLiNER preenche o restante."""
    classic: List[Span] = []
    extras: List[Span] = []
    for span in bertimbau_spans:
        label = normalize_label(span.get("label", ""))
        item: Span = {
            "text": (span.get("text") or "").strip(),
            "label": label,
            "start": int(span.get("start") or 0),
            "end": int(span.get("end") or 0),
            "source": span.get("source") or "bertimbau",
            "score": float(span.get("score") or 0.0),
        }
        if not item["text"] or item["end"] <= item["start"]:
            continue
        if label in CLASSIC_LABELS:
            classic.append(item)
        else:
            extras.append(item)

    occupied = list(classic)
    for span in gliner_spans:
        label = normalize_label(span.get("label", ""))
        item: Span = {
            "text": (span.get("text") or "").strip(),
            "label": label,
            "start": int(span.get("start") or 0),
            "end": int(span.get("end") or 0),
            "source": span.get("source") or "gliner",
            "score": float(span.get("score") or 0.0),
        }
        if not item["text"] or item["end"] <= item["start"]:
            continue
        if any(_overlaps(item, current) for current in occupied):
            continue
        if label in CLASSIC_LABELS:
            classic.append(item)
        else:
            extras.append(item)
        occupied.append(item)

    merged = classic + extras
    merged.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
    return merged
