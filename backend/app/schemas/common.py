"""通用响应模型：分页。"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
