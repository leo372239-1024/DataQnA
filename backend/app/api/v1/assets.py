"""资产 API：列出 skill/tool（按调用者角色裁剪可见性）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep, PrincipalDep
from app.schemas.asset import AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetOut])
async def list_assets(container: ContainerDep, principal: PrincipalDep) -> list[AssetOut]:
    roles = set(principal.roles)
    visible = []
    for a in container.assets.assets:
        if a.deprecated:
            continue
        if not a.permissions or set(a.permissions) <= roles:
            visible.append(AssetOut.from_asset(a))
    return sorted(visible, key=lambda a: (a.kind, a.id))
