"""Belgelere ait doğrulanmış, kısa olgusal cevaplar için merkezi registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StructuredFact:
    source_token: str
    question_tokens: tuple[str, ...]
    answer: str


STRUCTURED_FACTS = (
    StructuredFact(
        source_token="melville_moby_dick",
        question_tokens=("ana karakter", "bas karakter", "baslica karakter"),
        answer=(
            "Moby-Dick romanının başlıca karakteri Kaptan Ahab’dır. "
            "Ahab, Moby Dick adlı beyaz balinadan intikam almaya takıntılı bir balina avcısıdır."
        ),
    ),
)
