# 多智能体经营决策平台

面向企业经营分析场景，融合结构化业务数据、外部情报、内部知识与用户附件，通过多智能体协作完成跨源取证、归因分析、证据审查与报告生成，输出带来源引用的经营诊断与行动建议。

平台不重复实现 Text-to-SQL。它通过受控 HTTP 合约接入独立的「企业经营智能问数 Agent」，消费经过 Schema 检索、SQL 校验与只读执行后的经营事实；本仓库聚焦多智能体协作、跨源证据链与可追溯报告。

## 运行示例

![多智能体经营决策平台的经营分析工作台](docs/showcase/dashboard-preview.png)

界面会展示专家调用、证据登记、预算事件与 Markdown/PDF 报告产物。预览任务使用通用的“区域收入下降”问题，不依赖特定行业的数据模型。

## 核心能力

- **外部情报专家**：检索行业动态、竞争信息、政策规则、公开信息及其他外部事件，保留链接与发布时间。
- **经营问数专家**：调用独立分析服务，取得已校验的指标、时间范围、执行状态与审计摘要；本项目不连接业务库、不生成 SQL。
- **内部知识专家**：通过自建 Hybrid RAG 检索 SOP、业务复盘、制度文档、产品或服务资料与会话附件。
- **证据审查专家**：校验来源完整度、真实证据编号、引文定位、关键数值与支持关系；证据不足的因果判断会降级为推断。

## 系统架构

```text
企业经营问题
        ↓
主 Agent：任务拆解、依赖识别与预算控制
        ↓
┌─────────── TaskGroup 并行取证 ────────────┐
外部情报专家        经营问数专家        内部知识专家
└──────────────────────────────────────────┘
        ↓ evidence_id + 结构化摘要
证据审查专家：完整度 → 结论级支持关系
        ↓
经营诊断、待验证项、行动建议、Markdown / PDF
```

## Context Engineering 与预算调度

无依赖的外部情报、经营分析和内部知识检索由 `asyncio.TaskGroup` 并发执行；证据审查在取证完成后才运行。每个专家调用前，程序会检查调用次数、上下文预算和任务时限。

完整网页、SSE 事件和文档分块外置到 `output/session_<id>/artifacts/`，主 Agent 只接收受上限控制的结构化摘要与 `evidence_id`。每轮生成 `trace.jsonl`，记录专家调用、预算拒绝、证据登记与结论审查事件。

```dotenv
AGENT_MAX_EXPERT_CALLS=8
AGENT_MAX_CONTEXT_TOKENS=12000
AGENT_MAX_WALL_TIME_SECONDS=180
```

Token 是本地保守估算，用于控制上下文膨胀，不作为供应商精确计费数据。

## 结论级证据校验

`evaluate_evidence` 检查引用字段是否完整；`verify_claim_support` 进一步确认候选结论引用的是本轮真实登记的证据、引文可定位、关键数值可核对。支持关系分为 `direct`、`partial`、`conflicting` 与 `insufficient`。

`direct` 仅表示原文引用与数值可定位，不代表相关性已经证明因果。因果结论必须有实验、准实验或其他额外证据，否则平台要求降级为待验证推断。

## Hybrid RAG

```text
PDF / DOCX / Markdown / TXT
        ↓ 分块与元数据保留
Embedding 语义召回 ─┐
FTS5 / BM25 词法召回 ├─ RRF 融合 ─→ 可引用证据分块
                     ┘
```

知识库由应用自行维护，不依赖第三方 RAG 平台。中文文本在索引和查询两端均生成单字、双字 n-gram；语义与词法结果按排名进入 RRF，避免错误归一化 FTS5 的 BM25 原始分数。Embedding 模型和维度会写入索引元数据，不一致时要求重建。

建立全局知识库：

```bash
uv run python -m app.rag.indexer docs/knowledge_base
```

上传文件会建立会话级索引，只能由当前会话检索。

## Evaluation

评测口径、基线和复现要求见 [docs/evaluation.md](docs/evaluation.md)。仓库内置的轨迹评测会检查所需专家是否实际调用、是否发生预算拒绝、是否登记可引用证据，以及是否完成结论级审查：

```bash
uv run python -m app.evals.runner --trace output/session_<session_id>/trace.jsonl --cases tests/fixtures/eval_cases.jsonl --output artifacts/eval-result.json
```

## 与企业经营智能问数 Agent 的边界

| 能力 | 企业经营智能问数 Agent | 多智能体经营决策平台 |
| --- | --- | --- |
| 目标 | 回答指标、维度与趋势事实 | 回答可能原因、行动建议与证据是否充分 |
| 数据访问 | Schema 检索、SQL 生成/校验、只读执行 | 仅调用分析服务，不连接业务库、不执行 SQL |
| 核心技术 | LangGraph、检索、SQL 安全 | DeepAgents、Hybrid RAG、证据校验、上下文预算、轨迹评测 |
| 产物 | 可审计的数据回答 | 跨源证据链、经营诊断、行动清单、Markdown/PDF |

默认接入接口：

```text
POST {ANALYTICS_API_URL}/api/query
```

```json
{"query": "分析本月华南区域收入、客户数和利润率的变化", "session_id": "当前会话 ID"}
```

设置 `ANALYTICS_PROTOCOL=json` 时，适配器期望 `/api/analytics/query` 返回 `data`、`execution_status`、`metric_definition`、`time_range`、`sql_audit` 与 `limitations`。

## Domain Profile

行业术语被隔离在 [app/config/domain_profile.yml](app/config/domain_profile.yml)。当前默认 Profile 为 `enterprise_operations`，定义“业务指标”“分析维度”“外部情报”“内部知识”和报告章节。替换 Profile 与上游数据源后，可适配制造、SaaS、金融服务或零售等不同经营场景，核心编排、检索和证据链无需重写。

## Quick Start

```bash
uv sync
copy .env.example .env
uv run uvicorn app.api.server:app --host 0.0.0.0 --port 8000 --reload
```

前端：

```bash
cd frontend
pnpm install
pnpm dev
```

示例任务：

```text
分析本月华南区域收入下降的可能原因：先查询收入、客户数与利润率等经营指标，再检索近期外部变化和内部业务资料；输出证据链、可能原因、待验证项及行动建议，并生成 Markdown 报告。
```

## Tests

```bash
uv run python -m unittest tests/test_platform_safety.py tests/test_context_engineering.py
```

## Provenance

本项目的早期多智能体研究原型参考了 [didilili/deepsearch-agents](https://github.com/didilili/deepsearch-agents)。当前仓库围绕企业经营决策场景重构了专家协作边界、通用分析服务适配、自建 Hybrid RAG、结论级证据校验、上下文预算与轨迹评测。

发布前请继续核对保留代码的来源与授权范围；在确认所有保留实现的版权归属前，不应擅自声明新的开源许可证。
