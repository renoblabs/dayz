"""Chunking — splits cleaned text into searchable units.

Different content types use different splitters:
- Markdown: chunk by section headers (h2/h3), preserve code blocks contiguous
- Enforce/C source: chunk by top-level declaration (class, function)
- Generic: paragraph-boundary fallback

Token counts via tiktoken (cl100k_base — Claude/GPT compatible).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")

DEFAULT_TARGET_TOKENS = 600
DEFAULT_OVERLAP_TOKENS = 60
HARD_MAX_TOKENS = 1200


@dataclass(slots=True)
class ChunkOut:
    text: str
    metadata: dict


def count_tokens(text: str) -> int:
    return len(_ENC.encode(text, disallowed_special=()))


def _split_oversized(text: str, max_tokens: int = HARD_MAX_TOKENS) -> list[str]:
    """Last-resort split for chunks that exceed the hard ceiling."""
    if count_tokens(text) <= max_tokens:
        return [text]
    # Split at paragraph boundaries first
    paras = re.split(r"\n\s*\n", text)
    out: list[str] = []
    buf = ""
    for p in paras:
        candidate = (buf + "\n\n" + p) if buf else p
        if count_tokens(candidate) <= max_tokens:
            buf = candidate
        else:
            if buf:
                out.append(buf)
            if count_tokens(p) <= max_tokens:
                buf = p
            else:
                # Single-paragraph too large — split by sentences
                for sent in re.split(r"(?<=[.!?])\s+", p):
                    if buf and count_tokens(buf + " " + sent) > max_tokens:
                        out.append(buf)
                        buf = sent
                    else:
                        buf = (buf + " " + sent) if buf else sent
    if buf:
        out.append(buf)
    return out


def chunk_markdown(text: str, base_metadata: dict) -> list[ChunkOut]:
    """Split markdown by h2/h3 boundaries, preserve fenced code blocks contiguous."""
    if not text.strip():
        return []

    # Split on header lines but keep them attached to the section that follows
    lines = text.splitlines(keepends=True)
    sections: list[tuple[str, str]] = []  # (heading, body)
    current_heading = base_metadata.get("title", "")
    current_buf: list[str] = []
    in_fence = False

    for line in lines:
        # Track fenced code blocks so we don't split inside them
        if line.lstrip().startswith("```"):
            in_fence = not in_fence

        is_header = (not in_fence) and re.match(r"^(#{2,3})\s+", line)
        if is_header and current_buf:
            sections.append((current_heading, "".join(current_buf)))
            current_heading = line.strip().lstrip("#").strip()
            current_buf = [line]
        else:
            current_buf.append(line)

    if current_buf:
        sections.append((current_heading, "".join(current_buf)))

    out: list[ChunkOut] = []
    for idx, (heading, body) in enumerate(sections):
        # If section is huge, sub-split
        for sub in _split_oversized(body, HARD_MAX_TOKENS):
            meta = dict(base_metadata)
            meta.update({
                "section": heading,
                "section_index": idx,
                "format": "markdown",
                "token_count": count_tokens(sub),
            })
            out.append(ChunkOut(text=sub, metadata=meta))
    return out


# Match top-level Enforce/C++ declarations (class, function, modded class).
# Doesn't try to handle nested blocks — top-level only is fine for chunk boundaries.
_DECL_RE = re.compile(
    r"^(?:modded\s+)?(?:class|void|int|bool|float|string|vector|array|ref)\s+\w+",
    re.MULTILINE,
)


def chunk_enforce_source(text: str, base_metadata: dict) -> list[ChunkOut]:
    """Split Enforce/.c source by top-level declaration boundaries."""
    if not text.strip():
        return []

    matches = list(_DECL_RE.finditer(text))
    if len(matches) <= 1:
        # No or one declaration — treat as one chunk (with oversized fallback)
        return [
            ChunkOut(
                text=sub,
                metadata={**base_metadata, "format": "enforce", "token_count": count_tokens(sub)},
            )
            for sub in _split_oversized(text)
        ]

    out: list[ChunkOut] = []
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end]
        decl_line = body.splitlines()[0] if body else ""
        for sub in _split_oversized(body):
            meta = dict(base_metadata)
            meta.update({
                "decl": decl_line.strip()[:120],
                "decl_index": idx,
                "format": "enforce",
                "token_count": count_tokens(sub),
            })
            out.append(ChunkOut(text=sub, metadata=meta))
    return out


def chunk_source(
    cleaned_text: str,
    source_metadata: dict,
    file_suffix: str | None = None,
) -> list[ChunkOut]:
    """Dispatch to the right chunker based on file type."""
    base = dict(source_metadata)
    if file_suffix in (".c", ".cpp", ".h", ".hpp"):
        return chunk_enforce_source(cleaned_text, base)
    if file_suffix == ".md" or "markdown" in (source_metadata.get("format") or ""):
        return chunk_markdown(cleaned_text, base)
    # Default: treat as markdown-ish; fall back to oversize splitter
    return chunk_markdown(cleaned_text, base)
