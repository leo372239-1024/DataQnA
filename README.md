# DataQnA — 企业数据采集与分析智能体（ChatBI）

> 自然语言问数 → 指标语义层 → DSL 编译器 → 只读 SQL（RLS）→ 可解释呈现。
> 生产级 MVP：完整业务闭环、确定性优先、量化可评测。

[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange)](./LICENSE)

> **许可声明**：本项目采用 **PolyForm Noncommercial 1.0.0**，**仅限非商业用途**（个人学习、研究、实验、教学、公益与政府机构）。
> **任何商业使用均需事先取得著作权人的书面授权。** 详见 [LICENSE](./LICENSE)。

## 1. 项目定位

DataQnA 是一套面向企业的 **ChatBI 智能体**，让业务人员用自然语言查询经营数据，
并得到**带口径、带血缘、可解释**的答案。核心设计原则是**确定性优先**：

> LLM 只负责「理解意图」与「组织编排」，**永不拼接 SQL**。
> SQL 由语义层注册表 + DSL 编译器确定性地生成，杜绝幻觉 SQL。

## 2. 核心链路

```
自然语言问数
   │  ① 意图识别（确定性分类器：指标/维度/时间/对比/归因）
   ▼
IntentFrame
   │  ② 指标语义层（Metric/Dimension Registry，YAML 真相源，口径/血缘/版本）
   ▼
QueryDSL（Pydantic 强类型）
   │  ③ DSL 编译器（8 步固定顺序 → 参数化方言 SQL + RLS + 分区裁剪）
   ▼
方言 SQL（参数绑定，只读连接）
   │  ④ 查询网关（analytics_ro 只读 + 事务级 tenant_id + EXPLAIN 成本 + 结果缓存）
   ▼
可解释呈现（数值/表格/图表 + 口径徽章 + SQL + 血缘 + 归因瀑布图）
```

四道校验贯穿编译前后：**静态 → 语义 → 成本 → 结果**。

## 3. 技术栈

| 层 | 选型 |
|---|---|
| 后端 | FastAPI + uv + SQLAlchemy 2.0(async) + Alembic |
| 数据库 | PostgreSQL 16 + pgvector（RLS 租户隔离） |
| 缓存 | Redis（结果缓存，语义版本 + 角色哈希键） |
| 编排 | LangGraph（DAG 并行 + 单写者 + replan-gate + 上下文压缩） |
| 前端 | React 18 + TypeScript + Ant Design + Zustand + TanStack Query + ECharts + Zod |

## 4. 目录结构

```
DataQnA3/
├── backend/
│   ├── app/
│   │   ├── agent/         # 意图分类 / planner / orchestrator（编排内核）
│   │   ├── semantic/      # 指标/维度语义层（Registry + 链接器 + 时间解析）
│   │   ├── dsl/           # QueryDSL 模型 + 编译器 + 四道校验
│   │   ├── query/         # 查询网关（只读执行 + 成本 + 缓存）
│   │   ├── routing/       # 三层资产路由（skill/tool 管理与权限交集）
│   │   ├── memory/        # 反思模块（三层记忆 + 9 类失败码）
│   │   ├── guardrails/    # 注入防御 / 越权防护 / 提示词护栏 / 审计
│   │   ├── observability/ # span/trace 可观测
│   │   ├── api/v1/        # REST + SSE 端点
│   │   └── seed/          # 种子（建表 + 灌数 + 指标真相源）
│   ├── evals/             # 黄金集/路由/红队/反思/长时程评测 + 基线 + 亮点报告
│   ├── scripts/           # gen_gold.py / smoke.py
│   └── tests/unit/        # 单元测试（71 例）
├── frontend/
│   └── src/
│       ├── api/           # Zod wire contract（单一真相源）+ fetch/SSE 客户端
│       ├── hooks/         # useQuestionStream（SSE 状态机）等
│       ├── features/      # ask / semantic / trace / assets / evals 页面
│       └── components/    # AnswerPanel / SqlViewer / TraceTimeline / EChart 等
├── deploy/
│   ├── docker-compose.yml # 一键启动（postgres + redis + api + frontend）
│   └── initdb/            # 初始化（扩展 + analytics_ro 角色）
└── docs/                  # 需求原始记录与补充文档
```

## 5. 快速开始

### 方式 A：Docker 一键启动（推荐）

```bash
cd deploy
docker compose up -d --build
# 首次启动 api 容器会自动建表 + 灌种子数据（幂等）
# 访问 http://localhost:5173
```

- api 容器启动时自动执行 `python -m app.seed`（建表 + 灌 13.6 万订单 + 加载 21 指标/8 维度真相源），随后启动 uvicorn。
- 宿主机端口映射：postgres `5432`、redis `6379`、api `8010→8000`、frontend `5173→80`。

### 方式 B：本地开发

```bash
# 1. 起依赖栈
cd deploy && docker compose up -d postgres redis

# 2. 后端（首次需灌种子）
cd backend
uv sync
uv run python -m app.seed
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010

# 3. 前端
cd frontend
pnpm install
VITE_API_PROXY_TARGET=http://127.0.0.1:8010 pnpm dev
# 访问 http://localhost:5173
```

### 端到端冒烟

```bash
cd backend
uv run python scripts/smoke.py   # L1-L5 五个等级端到端，5/5 PASS
```

## 6. 五大技术亮点（量化达标）

> 完整报告见 `backend/evals/HIGHLIGHTS_REPORT.md`。基线存档 `backend/evals/baselines/*.json`。

| 亮点 | 套件 | 改进轴 | 基线 | 改进后 | 提升 |
|---|---|---|---|---|---|
| H1 长时程任务分解/编排/执行 | longtask | 端到端中位延迟（并行 vs 串行） | 329.27 ms | 177.88 ms | **−46.0%** |
| H2 多 Agent 协作 | longtask | 重复派生动作数（单写者） | — | 0 | 达标（恒 0） |
| H3 超多 Skill 管理与路由 | routing | route_accuracy@1 | 66.7% | 100% | **+33.3pp** |
| H4 超多 MCP/工具管理与路由 | routing | route_accuracy@1（含 tool） | 66.7% | 100% | **+33.3pp** |
| H5 反思模块（经验积累/自改进） | reflection | 重试成功率 | 10.0% | 100% | **+90.0pp** |

安全治理（X1 横切）红队：**block_rate 100%**（10/10 拦截）。

## 7. 评测体系

- **黄金集** `evals/gold/*.yaml`：130 题，L1-L5 分层，EX 执行准确率 = **1.0**。
- 跑分入口：`uv run python -m app.evals.runner --suite <suite> --baseline on|off`
  - `gold`（EX）· `routing`（A/B）· `redteam`（安全）· `reflection`（A/B）· `longtask`（A/B）
- 评测连接池预热 + 每轮冷缓存 + 5 轮取中位，消除缓存/冷启动噪声。

## 8. 安全治理（X1 横切）

- **注入防御**：确定性提示词护栏（指令注入 / 破坏性 / SQL 注入关键词）+ 参数绑定 + 只读角色。
- **越权防护**：`analytics_ro` 只读连接 + 事务级 `set_config('app.tenant_id')` + 表级 RLS。
- **权限交集**：路由 Stage 0 结构性剔除越权资产（confused deputy 防线，绝不静默降级）。
- **审计**：每次提问/执行记录 `AuditEntry`（租户/操作者/trace/结果码）。

## 9. API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/meta` | 语义层/资产元信息 |
| POST | `/api/v1/questions` | 提交问数（返回 question_id） |
| GET | `/api/v1/questions/{id}/stream` | SSE 流式执行（status/subgoal/answer/done） |
| GET | `/api/v1/answers/{id}` | 查询答案 |
| GET | `/api/v1/semantic/metrics` / `dimensions` | 语义层浏览 |
| GET | `/api/v1/assets` | 资产（skill/tool）浏览 |
| GET | `/api/v1/traces/{trace_id}` | 执行追踪 span 时间线 |
| POST | `/api/v1/evals/run` | 触发评测跑分 |

## 10. 质量门

- 后端：`ruff check app tests scripts` 全绿、`mypy app`（strict）81 文件零告警、`pytest tests/unit` 71 通过。
- 前端：`pnpm lint`（0 error 0 warning）、`pnpm typecheck`、`pnpm test`（10 通过）、`pnpm build` 全绿。

## 11. 关键约定

- **率值陷阱**：ratio 指标只存分子/分母，强制 `SUM(num)/SUM(den)`，禁止对率值再聚合。
- **确定性**：时间锚定快照日 `2026-09-30`；离线 stub LLM 保证评测可复现。
- **前端契约**：`frontend/src/api/schemas.ts` 的 Zod schema 是 wire contract 单一真相源，后端 SSE 边界翻译与其对齐。
- **涨红跌绿**：金融配色遵循中国市场约定。

## 12. 许可证

本项目采用 **[PolyForm Noncommercial License 1.0.0](./LICENSE)**。

| 允许（非商业用途） | 禁止（需另行授权） |
|---|---|
| 个人学习、研究、实验、测试 | 任何商业目的使用 |
| 修改、衍生新作品 | 集成进商业产品或对外商业服务 |
| 以相同条款再分发副本 | 转授权（sublicense）或转让许可 |
| 教学、公益、政府机构使用 | 移除 Required Notice 后分发 |

**商业授权**：如需商业使用，请通过 GitHub Issue 联系著作权人获取书面授权。

> 说明：因本许可对使用领域（field of use）设限，本项目属于 **source-available（源码公开）**，
> 不符合 OSI 开源定义，故请勿表述为「OSI 开源」。

---

Copyright (c) 2026 leo372239-1024. All rights reserved except as expressly licensed above.
