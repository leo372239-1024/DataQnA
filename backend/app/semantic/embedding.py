"""确定性本地 embedding：字符 n-gram + hashing trick。

无外部依赖、完全离线、可复现。对中文别名/能力描述的字符级语义重合有基本召回能力。
MVP 用于实体链接与工具路由的向量召回；后续可替换为真实 embedding 模型（接口不变）。
"""
from __future__ import annotations

import hashlib

DIM = 256


def _ngrams(text: str) -> set[str]:
    t = text.lower()
    tokens: set[str] = set()
    for n in (1, 2, 3):
        for i in range(len(t) - n + 1):
            tokens.add(t[i : i + n])
    if not tokens:
        tokens.add(t)
    return tokens


def embed(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    for tok in _ngrams(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % dim] += 1.0
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec] if norm else vec


def cosine(a: list[float], b: list[float]) -> float:
    # 假设已归一化，直接点积
    return sum(x * y for x, y in zip(a, b, strict=False))


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
