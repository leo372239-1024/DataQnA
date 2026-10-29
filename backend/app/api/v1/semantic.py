"""语义层 API：指标/维度注册表只读查询。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep
from app.core.errors import NotFoundError
from app.schemas.common import Page
from app.schemas.semantic import DimensionOut, LineageNode, MetricDetailOut, MetricOut

router = APIRouter(prefix="/semantic", tags=["semantic"])


@router.get("/metrics", response_model=Page[MetricOut])
async def list_metrics(
    container: ContainerDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    type: str | None = Query(default=None),
) -> Page[MetricOut]:
    metrics = container.registry.metrics
    if type:
        metrics = [m for m in metrics if m.type == type]
    metrics = sorted(metrics, key=lambda m: m.id)
    total = len(metrics)
    start = (page - 1) * page_size
    items = [MetricOut.from_def(m) for m in metrics[start : start + page_size]]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/dimensions", response_model=Page[DimensionOut])
async def list_dimensions(
    container: ContainerDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> Page[DimensionOut]:
    dims = sorted(container.registry.dimensions, key=lambda d: d.id)
    total = len(dims)
    start = (page - 1) * page_size
    items = [DimensionOut.from_def(d) for d in dims[start : start + page_size]]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/metrics/{metric_id}", response_model=MetricDetailOut)
async def get_metric(metric_id: str, container: ContainerDep) -> MetricDetailOut:
    try:
        m = container.registry.get_metric(metric_id)
    except KeyError as e:
        raise NotFoundError(str(e)) from e
    lineage: list[LineageNode] = []
    if m.is_ratio:
        for ref_id in (m.numerator, m.denominator):
            if ref_id:
                try:
                    ref = container.registry.get_metric(ref_id)
                    lineage.append(LineageNode(
                        metric_id=ref.id, name_cn=ref.name_cn, version=ref.version))
                except KeyError:
                    pass
    return MetricDetailOut(
        **MetricOut.from_def(m).model_dump(),
        expression=m.expression,
        numerator=m.numerator,
        denominator=m.denominator,
        source_tables=m.source_tables,
        default_time_col=m.default_time_col,
        lineage=lineage,
    )
