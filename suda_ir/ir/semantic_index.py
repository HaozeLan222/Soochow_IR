from __future__ import annotations

from pathlib import Path

import numpy as np

from suda_ir.ir.index import SearchResult
from suda_ir.models import TeacherDoc


class SemanticDependencyError(RuntimeError):
    """Raised when the optional semantic retrieval dependency is unavailable."""


class SemanticIndex:
    def __init__(
        self,
        docs: list[TeacherDoc],
        *,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        cache_path: str | Path | None = None,
        backend: str = "sentence-transformers",
        batch_size: int = 32,
        hashing_dim: int = 512,
        local_files_only: bool = False,
    ) -> None:
        self.docs = docs
        self.model_name = model_name
        self.cache_path = Path(cache_path) if cache_path else None
        self.backend = backend
        self.batch_size = batch_size
        self.hashing_dim = hashing_dim
        self.local_files_only = local_files_only
        self.doc_texts = [build_semantic_text(doc) for doc in docs]
        self._model = None
        self.doc_embeddings = self._load_or_build_embeddings()

    def search(
        self,
        query: str,
        top_k: int = 10,
        *,
        allowed_doc_indices: set[int] | None = None,
    ) -> list[SearchResult]:
        query = query.strip()
        if not query or len(self.docs) == 0:
            return []

        query_embedding = self._encode([query])[0]
        scores = self.doc_embeddings @ query_embedding
        if allowed_doc_indices is not None:
            mask = np.full(scores.shape, -np.inf, dtype=np.float32)
            for index in allowed_doc_indices:
                if 0 <= index < len(scores):
                    mask[index] = scores[index]
            scores = mask

        candidate_indices = np.argsort(-scores)[:top_k]
        results: list[SearchResult] = []
        for index in candidate_indices:
            score = float(scores[index])
            if not np.isfinite(score):
                continue
            results.append(SearchResult(doc=self.docs[int(index)], score=score, matched_terms=[]))
        return results

    def _load_or_build_embeddings(self) -> np.ndarray:
        doc_ids = [doc.doc_id for doc in self.docs]
        if self.cache_path and self.cache_path.exists():
            cached = np.load(self.cache_path, allow_pickle=False)
            cached_ids = [str(value) for value in cached["doc_ids"].tolist()]
            cached_model = str(cached["model_name"].tolist())
            cached_backend = str(cached["backend"].tolist())
            if cached_ids == doc_ids and cached_model == self.model_name and cached_backend == self.backend:
                return cached["embeddings"].astype(np.float32)

        embeddings = self._encode(self.doc_texts)
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                self.cache_path,
                doc_ids=np.array(doc_ids),
                model_name=np.array(self.model_name),
                backend=np.array(self.backend),
                embeddings=embeddings.astype(np.float32),
            )
        return embeddings

    def _encode(self, texts: list[str]) -> np.ndarray:
        if self.backend == "hashing":
            return self._encode_hashing(texts)
        if self.backend != "sentence-transformers":
            raise ValueError(f"Unsupported semantic backend: {self.backend}")
        return self._encode_sentence_transformers(texts)

    def _encode_sentence_transformers(self, texts: list[str]) -> np.ndarray:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise SemanticDependencyError(
                "sentence-transformers is not installed. Install optional semantic dependencies first."
            ) from exc

        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name, local_files_only=self.local_files_only)
            except Exception as exc:
                raise SemanticDependencyError(f"Failed to load semantic model {self.model_name!r}: {exc}") from exc

        embeddings = self._model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.astype(np.float32)

    def _encode_hashing(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.hashing_dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for gram in char_ngrams(text):
                index = stable_hash(gram) % self.hashing_dim
                matrix[row, index] += 1.0
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


def build_semantic_text(doc: TeacherDoc) -> str:
    parts = [
        ("姓名", doc.name),
        ("学院", doc.college),
        ("职称", doc.title),
        ("研究方向", doc.research),
        ("论文成果", doc.papers),
        ("个人简介", doc.profile),
    ]
    text = "\n".join(f"{label}：{truncate(value)}" for label, value in parts if value)
    if text:
        return text
    return truncate(doc.content)


def truncate(value: str, limit: int = 700) -> str:
    value = " ".join((value or "").split())
    return value[:limit]


def char_ngrams(text: str) -> list[str]:
    text = "".join((text or "").lower().split())
    if not text:
        return []
    grams: list[str] = []
    for n in (2, 3, 4):
        if len(text) < n:
            continue
        grams.extend(text[index : index + n] for index in range(len(text) - n + 1))
    if not grams:
        grams.append(text)
    return grams


def stable_hash(text: str) -> int:
    value = 2166136261
    for char in text:
        value ^= ord(char)
        value = (value * 16777619) & 0xFFFFFFFF
    return value
