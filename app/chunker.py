"""Belge metnini deterministik ve örtüşen parçalara böler."""

from __future__ import annotations


import re


def _split_by_sections(text: str) -> list[str]:
    """Başlıklar (#) ve paragraf çift satır sonlarına göre metni doğal bölümlere ayırır."""
    lines = text.splitlines()
    sections: list[str] = []
    current_section: list[str] = []

    for line in lines:
        is_header = line.strip().startswith(("#", "==", "--"))
        if is_header and current_section:
            sec_text = "\n".join(current_section).strip()
            if sec_text:
                sections.append(sec_text)
            current_section = [line]
        else:
            current_section.append(line)

    if current_section:
        sec_text = "\n".join(current_section).strip()
        if sec_text:
            sections.append(sec_text)
    return sections


def _best_boundary(text: str, start: int, limit: int) -> int:
    """Sınırın gerisindeki en anlamlı kırılma noktasını bulur."""
    if limit >= len(text):
        return len(text)

    window = text[start:limit]
    candidates = (
        window.rfind("\n\n"),
        window.rfind("\n"),
        max(window.rfind(". "), window.rfind("? "), window.rfind("! ")),
        window.rfind(" "),
    )
    boundary = max(candidates)
    if boundary < int(len(window) * 0.55):
        return limit
    return start + boundary + 1


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Metni başlık ve paragraf bütünlüğünü koruyarak parçalara böler."""
    if chunk_size <= 0:
        raise ValueError("chunk_size pozitif olmalıdır.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 0 ile chunk_size - 1 arasında olmalıdır.")

    normalized = text.strip()
    if not normalized:
        return []

    sections = _split_by_sections(normalized)
    chunks: list[str] = []

    current_chunk = ""
    for sec in sections:
        if len(sec) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            start = 0
            sec_length = len(sec)
            while start < sec_length:
                end = _best_boundary(sec, start, min(start + chunk_size, sec_length))
                if end <= start:
                    end = min(start + chunk_size, sec_length)
                sub_chunk = sec[start:end].strip()
                if sub_chunk:
                    chunks.append(sub_chunk)
                if end >= sec_length:
                    break
                next_start = max(end - overlap, start + 1)
                while next_start < sec_length and sec[next_start].isspace():
                    next_start += 1
                start = next_start
        else:
            # Başlıkla başlayan bölümleri birbirine karıştırma; bu semantic
            # chunking'in temel garantisidir. Başlıksız ardışık metinler yine
            # aynı chunk içinde birleştirilebilir.
            starts_with_header = sec.lstrip().startswith(("#", "==", "--"))
            if starts_with_header and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sec
            elif len(current_chunk) + len(sec) + 2 <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{sec}" if current_chunk else sec
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sec

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
