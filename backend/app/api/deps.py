"""API 依赖注入：容器单例 + 认证主体。

主体（Principal）在 MVP 阶段由请求体/头派生；生产环境替换为 JWT principal
（见 spec/api-conventions.md Auth：绝不信任客户端声明的角色）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, Header

from app.core.container import Container, get_container


@dataclass
class Principal:
    tenant_id: str
    user_id: str
    roles: list[str] = field(default_factory=list)


def container_dep() -> Container:
    return get_container()


ContainerDep = Annotated[Container, Depends(container_dep)]


def get_principal(
    container: ContainerDep,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")] = "",
    x_user_id: Annotated[str, Header(alias="X-User-Id")] = "",
    x_roles: Annotated[str, Header(alias="X-Roles")] = "",
) -> Principal:
    """从认证头派生主体。头缺失时回退默认 dev 主体（仅 MVP）。"""
    tenant_id = x_tenant_id.strip() or "t1"
    user_id = x_user_id.strip() or "demo"
    roles = [r.strip() for r in x_roles.split(",") if r.strip()] or ["analyst"]
    return Principal(tenant_id=tenant_id, user_id=user_id, roles=roles)


PrincipalDep = Annotated[Principal, Depends(get_principal)]
