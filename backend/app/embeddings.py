import hashlib
import re

import numpy as np

from .config import Settings


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = list(words)
    out.extend(f"{a}_{b}" for a, b in zip(words, words[1:], strict=False))
    return out


class Embedder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.dim = settings.embedding_dim
        self.client = None
        if settings.openai_api_key:
            from openai import OpenAI

            self.client = OpenAI(api_key=settings.openai_api_key)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def embed(self, text: str) -> list[float]:
        if self.client is not None:
            resp = self.client.embeddings.create(model=self.settings.embedding_model, input=text)
            return resp.data[0].embedding
        return self._hash_embed(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.client is not None:
            resp = self.client.embeddings.create(model=self.settings.embedding_model, input=texts)
            return [d.embedding for d in resp.data]
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _tokens(text):
            digest = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm == 0:
            norm = 1.0
        return (vec / norm).tolist()
