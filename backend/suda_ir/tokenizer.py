from __future__ import annotations

import re


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    text = text.strip().lower()
    if not text:
        return []
    try:
        import jieba

        return [token.strip().lower() for token in jieba.cut(text) if token.strip()]
    except ImportError:
        raw = TOKEN_RE.findall(text)
        tokens: list[str] = []
        buffer = ""
        for item in raw:
            if re.fullmatch(r"[\u4e00-\u9fff]", item):
                buffer += item
            else:
                if buffer:
                    tokens.extend(_char_ngrams(buffer))
                    buffer = ""
                tokens.append(item)
        if buffer:
            tokens.extend(_char_ngrams(buffer))
        return tokens


def _char_ngrams(text: str) -> list[str]:
    if len(text) <= 2:
        return [text]
    return [text[i : i + 2] for i in range(len(text) - 1)]
