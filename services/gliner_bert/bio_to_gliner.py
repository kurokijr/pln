"""Converte JSON BIO (IOB2) para o formato de treino do GLiNER (sem torch)."""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_LABEL_MAP = {
    "PESSOA": "pessoa",
    "PER": "pessoa",
    "PERSON": "pessoa",
    "ORGANIZACAO": "organização",
    "ORGANIZAÇÃO": "organização",
    "ORG": "organização",
    "ORGANIZATION": "organização",
    "LOCAL": "local",
    "LOCALIZACAO": "local",
    "LOCALIZAÇÃO": "local",
    "LOC": "local",
    "GPE": "local",
    "TEMPO": "tempo",
    "TIME": "tempo",
    "DATA": "tempo",
    "DATE": "tempo",
    "LEGISLACAO": "norma",
    "LEGISLAÇÃO": "norma",
    "JURISPRUDENCIA": "norma",
    "JURISPRUDÊNCIA": "norma",
    "FUNDAMENTO": "norma",
    "PRODUTODELEI": "norma",
    "NORMA": "norma",
    "VALOR": "valor",
    "VALUE": "valor",
    "EVENTO": "evento",
    "MISC": "misc",
    "MATERIAL": "material",
    "PROCESSO": "processo",
    "INSTITUICAO": "instituição",
    "INSTITUIÇÃO": "instituição",
}

_TAG_RE = re.compile(r"^(O|B|I)(?:[-_](.+))?$", re.IGNORECASE)


class BioConversionError(ValueError):
    """JSON BIO inválido."""


def _strip_accents_key(value: str) -> str:
    return (
        value.replace("Á", "A")
        .replace("Ã", "A")
        .replace("Â", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )


def map_label(raw: str, label_map: Optional[Dict[str, str]] = None) -> str:
    """Aplica o mapa do usuário e o mapa padrão (ORGANIZACAO → organização)."""
    text = (raw or "").strip()
    if not text:
        return "misc"
    merged = dict(DEFAULT_LABEL_MAP)
    if label_map:
        merged.update(label_map)
    for key in (text, text.upper(), text.lower(), _strip_accents_key(text.upper())):
        if key in merged:
            return merged[key]
    return text.lower()


def _parse_tag(tag: str) -> Tuple[str, Optional[str]]:
    raw = (tag or "O").strip()
    if not raw:
        return "O", None
    match = _TAG_RE.match(raw)
    if not match:
        raise BioConversionError(f"Tag BIO inválida: {tag!r} (use O, B-ROTULO ou I-ROTULO)")
    prefix = match.group(1).upper()
    label = match.group(2)
    if prefix == "O":
        return "O", None
    if not label:
        raise BioConversionError(f"Tag {tag!r} sem rótulo após B-/I-")
    return prefix, label


def bio_sentence_to_gliner(
    tokens: Sequence[str],
    ner_tags: Sequence[str],
    label_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Uma frase BIO → `{tokenized_text, ner}` com índices de token inclusivos."""
    if len(tokens) != len(ner_tags):
        raise BioConversionError(
            f"tokens ({len(tokens)}) e ner_tags ({len(ner_tags)}) devem ter o mesmo tamanho"
        )
    word_list = [str(token) for token in tokens]
    spans: List[List[Any]] = []
    start: Optional[int] = None
    current_raw: Optional[str] = None

    def flush(end_inclusive: int) -> None:
        nonlocal start, current_raw
        if start is None or current_raw is None:
            return
        spans.append([start, end_inclusive, map_label(current_raw, label_map)])
        start = None
        current_raw = None

    for index, tag in enumerate(ner_tags):
        prefix, raw_label = _parse_tag(str(tag))
        if prefix == "O":
            flush(index - 1)
            continue
        if prefix == "B":
            flush(index - 1)
            start = index
            current_raw = raw_label
            continue
        if start is None or current_raw is None or raw_label != current_raw:
            raise BioConversionError(
                f"I-{raw_label} sem B-{raw_label} precedente no token {index}"
            )

    flush(len(word_list) - 1)
    return {"tokenized_text": word_list, "ner": spans}


def _as_sentence_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise BioConversionError("O JSON deve ser um objeto ou uma lista de frases.")
    if "sentences" in payload:
        sentences = payload["sentences"]
        if not isinstance(sentences, list):
            raise BioConversionError("'sentences' deve ser uma lista.")
        return sentences
    if "tokens" in payload and "ner_tags" in payload:
        return [payload]
    raise BioConversionError("Informe 'sentences' ou uma lista de {tokens, ner_tags}.")


def convert_sentences(
    sentences: Sequence[Dict[str, Any]],
    label_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Converte uma lista de frases BIO; ignora frases sem tokens."""
    converted: List[Dict[str, Any]] = []
    for index, sentence in enumerate(sentences):
        if not isinstance(sentence, dict):
            raise BioConversionError(f"Frase {index} não é um objeto.")
        tokens = sentence.get("tokens")
        tags = sentence.get("ner_tags")
        if tokens is None or tags is None:
            raise BioConversionError(f"Frase {index} precisa de 'tokens' e 'ner_tags'.")
        if not tokens:
            continue
        converted.append(bio_sentence_to_gliner(tokens, tags, label_map))
    if not converted:
        raise BioConversionError("Nenhuma frase com tokens para treinar.")
    return converted


def split_train_val(
    examples: List[Dict[str, Any]],
    val_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separa validação; com poucas frases, a validação copia o treino."""
    if len(examples) < 10:
        return examples, list(examples)
    ratio = min(0.3, max(0.0, float(val_ratio)))
    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)
    val_count = max(1, int(len(shuffled) * ratio))
    return shuffled[val_count:], shuffled[:val_count]


def convert_bio_json(
    payload: Any,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    """Devolve (treino, validação, label_map efetivo)."""
    label_map: Dict[str, str] = {}
    validation_raw: Optional[List[Dict[str, Any]]] = None
    if isinstance(payload, dict):
        raw_map = payload.get("label_map") or {}
        if raw_map and not isinstance(raw_map, dict):
            raise BioConversionError("'label_map' deve ser um objeto string → string.")
        label_map = {str(key): str(value) for key, value in (raw_map or {}).items()}
        if payload.get("validation") is not None:
            validation_raw = _as_sentence_list(payload["validation"])

    train_examples = convert_sentences(_as_sentence_list(payload), label_map)
    if validation_raw is not None:
        val_examples = convert_sentences(validation_raw, label_map)
    else:
        train_examples, val_examples = split_train_val(
            train_examples, val_ratio=val_ratio, seed=seed
        )
    return train_examples, val_examples, label_map
