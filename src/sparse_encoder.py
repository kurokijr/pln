"""Encoder esparso BM25-like para busca léxica no Qdrant.

Gera vetores esparsos de frequência de termos (TF). O IDF é aplicado
pelo Qdrant quando a collection usa Modifier.IDF.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from qdrant_client.models import SparseVector

TOKEN_RE = re.compile(r"[a-záàâãéêíóôõúüç0-9]+", re.IGNORECASE)

PT_STOPWORDS = {
    "a", "ao", "aos", "as", "ate", "até", "com", "como", "da", "das", "de",
    "dela", "dele", "depois", "do", "dos", "e", "em", "entre", "era", "essa",
    "esse", "esta", "está", "este", "eu", "foi", "ha", "há", "isso", "isto",
    "ja", "já", "mais", "mas", "me", "mesmo", "meu", "minha", "muito", "na",
    "nao", "não", "nas", "nem", "no", "nos", "nossa", "o", "os", "ou", "para",
    "pela", "pelo", "por", "qual", "quando", "que", "quem", "se", "sem",
    "ser", "seu", "sua", "so", "só", "tambem", "também", "te", "tem", "ter",
    "um", "uma", "voce", "você",
}


def tokenize(text: str) -> List[str]:
    """Tokeniza texto em termos minúsculos, sem stopwords curtas."""
    if not text or not isinstance(text, str):
        return []
    tokens = TOKEN_RE.findall(text.lower())
    return [token for token in tokens if len(token) > 1 and token not in PT_STOPWORDS]


def token_index(token: str) -> int:
    """Índice estável uint32 para o termo (compatível com Qdrant)."""
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


def text_to_sparse_vector(text: str) -> "SparseVector":
    """Converte texto em SparseVector de frequências de termo."""
    from qdrant_client.models import SparseVector

    counts = Counter(tokenize(text))
    if not counts:
        return SparseVector(indices=[0], values=[0.0])

    merged = {}
    for token, frequency in counts.items():
        index = token_index(token)
        merged[index] = merged.get(index, 0.0) + float(frequency)

    indices = sorted(merged.keys())
    values = [merged[index] for index in indices]
    return SparseVector(indices=indices, values=values)
