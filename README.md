# 多智能体经营决策平台

> 将结构化经营数据、外部情报和内部知识组织为带证据引用的经营诊断与行动建议。

多智能体经营决策平台面向企业经营分析场景：主 Agent 根据问题拆解任务，按依赖关系调度外部情报、嵌入式语义问数、内部 Hybrid RAG 与结论级证据审查专家，最终输出可追溯的诊断、待验证项和 Markdown/PDF 报告。

问数能力已内置在本仓库：LangGraph 子图负责三路 Schema 检索、SQL 生成、预检、一次自纠错和只读执行；多智能体层负责跨源协作、上下文预算、证据链与报告交付。

[界面预览](#界面预览) · [核心流程](#核心使用流程) · [系统架构](#系统架构) · [技术栈](#技术栈与实现范围) · [评测](#评测与可观测性) · [快速启动](#快速启动) · [技术文档](docs/README.md)

## 界面预览

![多智能体经营决策平台：区域收入下滑诊断与证据链](docs/showcase/dashboard-preview.png)

界面展示任务输入、专家调用、执行轨迹、证据审查结果和报告产物。示例使用“华南区域收入下降”的通用经营问题，不依赖特定行业的数据模型。

| 前端模块 | 作用 |
| --- | --- |
| [任务输入](frontend/src/components/MissionComposer.tsx) | 提交经营问题、使用预设任务并启动主 Agent |
| [多智能体路由](frontend/src/components/AgentTopology.tsx) | 展示主 Agent 与四类专家的职责边界 |
| [会话与轨迹](frontend/src/components/ConversationThread.tsx) | 展示工具/专家事件、最终结论及 Markdown/PDF 文件 |
| [会话控制](frontend/src/hooks/useDeepAgentSession.ts) | 管理 WebSocket、上传、取消与会话状态 |

## 核心使用流程

| 步骤 | 用户操作 | 系统执行 | 可见产物 |
| --- | --- | --- | --- |
| 1. 提出问题 | 输入区域、客户、收入、利润或效率相关问题 | 主 Agent 识别是否需要跨源取证 | 任务与执行轨迹 |
| 2. 并行取证 | 可上传内部资料，也可选择只使用部分数据源 | `TaskGroup` 并行调度外部情报、经营问数和内部知识检索 | 结构化专家结果、`evidence_id` |
| 3. 问数核验 | 提问指标、维度或趋势事实 | LangGraph 进行 Schema 三路检索、SQL 预检、有限纠错和只读执行 | 数据结果、SQL 审计摘要、时间与口径 |
| 4. 审查结论 | 要求诊断或报告 | 证据审查专家检查引用、原文定位、数值和支持关系 | `direct / partial / conflicting / insufficient` |
| 5. 交付结果 | 请求汇总或导出 | 主 Agent 生成经营诊断、待验证项和行动建议 | 对话结论、Markdown/PDF 报告 |

## 为什么这样设计

经营分析的难点不只是“找到数字”，而是区分已验证事实、外部信号与待验证推断。本项目将原始材料外置保存，要求结论引用本轮真实登记的证据，而不是把长文本或模型猜测直接包装成答案。

```text
业务问题 ──→ 任务拆解 ──→ 并行取证 ──→ evidence_id
                                  │
            ┌─────────────────────┼─────────────────────┐
            ↓                     ↓                     ↓
       外部公开信息         只读经营问数            内部知识材料
            └─────────────────────┴─────────────────────┘
                                  ↓
                    结论级证据审查与不确定性标注
                                  ↓
                    经营诊断、行动建议、报告交付
```

- **结论可追溯**：工具结果以 `evidence_id` 登记，结论必须指向本轮真实证据。
- **因果不越界**：共现信息不能直接表述为因果；证据不足时强制降级为推断或待验证项。
- **上下文可控**：原始网页、SSE 事件和文档分块进入会话 artifact，模型只接收结构化高信号摘要。
- **问数可治理**：数据库账户应是只读账户；应用层使用 `sqlglot` 拒绝多语句、写操作和文件读写 SQL，再用 `EXPLAIN` 预检。

## 系统架构

```mermaid
flowchart TD
    U[企业经营问题 / 上传资料] --> M[DeepAgents 主 Agent]
    M --> P[任务依赖规划与上下文预算]
    P --> X[TaskGroup 并行取证]
    X --> E[外部情报专家<br/>Tavily]
    X --> A[经营问数专家<br/>本地 LangGraph 子图]
    X --> K[内部知识专家<br/>Hybrid RAG]
    A --> Q[Qdrant 字段/指标召回]
    A --> S[Elasticsearch 字段值检索]
    A --> D[MySQL 只读执行]
    Q --> G[Schema 依赖扩展 / SQL 生成]
    S --> G
    G --> V[sqlglot + EXPLAIN + 一次纠错]
    V --> D
    E --> R[Evidence Registry]
    K --> R
    D --> R
    R --> C[证据审查专家]
    C --> O[诊断、行动建议、Markdown / PDF]
    P --> T[trace.jsonl / artifacts]
```

## 技术栈与实现范围

| 层 | 技术 | 在项目中的用途 |
| --- | --- | --- |
| 多智能体编排 | DeepAgents、LangGraph、`asyncio.TaskGroup` | 主 Agent、专家路由、无依赖取证并发与问数子图 |
| 经营问数 | Qdrant、Elasticsearch、MySQL、SQLAlchemy Async、sqlglot | 字段/指标 Dense 召回、字段值检索、Schema 扩展、SQL 预检与只读执行 |
| 内部知识 RAG | SQLite FTS5、Embedding、RRF | 中文 n-gram 词法检索、语义检索、可引用分块与会话隔离 |
| 证据与上下文 | Evidence Registry、JSONL Trace、artifact offloading | 引用登记、结论级验证、预算、审计与轨迹评测 |
| 后端与交互 | FastAPI、Pydantic、WebSocket、React、TypeScript、Ant Design | 任务 API、实时事件、文件上传/下载与工作台 |
| 外部信息 | Tavily | 公开信息、行业动态、政策规则与竞争信息检索 |

### 关键代码导航

| 想看什么 | 从这里开始 |
| --- | --- |
| 主 Agent、会话隔离与流式监控 | [app/agent/main_agent.py](app/agent/main_agent.py) |
| 并行专家取证与依赖约束 | [app/orchestration/parallel_research.py](app/orchestration/parallel_research.py) |
| 内置问数 LangGraph 子图 | [app/analytics/agent.py](app/analytics/agent.py) |
| 连续追问结构化状态 | [app/analytics/conversation.py](app/analytics/conversation.py) |
| SQL 只读校验 | [app/analytics/agent.py](app/analytics/agent.py) |
| Hybrid RAG 与 RRF | [app/rag/hybrid_store.py](app/rag/hybrid_store.py) |
| 结论级证据校验 | [app/tools/evidence_tools.py](app/tools/evidence_tools.py) |
| 上下文预算、artifact 与 trace | [app/context_engineering/runtime.py](app/context_engineering/runtime.py) |
| FastAPI 与 WebSocket | [app/api/server.py](app/api/server.py)、[app/api/monitor.py](app/api/monitor.py) |

## 内置企业经营智能问数

```text
连续追问状态
     ↓
Qdrant 字段/指标 Dense 召回 ─┐
Elasticsearch 字段值检索 ────┼→ Schema 依赖扩展 → SQL 生成
Cross-Encoder 重排（可选） ─┘                         ↓
                                      sqlglot 只读检查 → EXPLAIN
                                                        ↓
                                           一次纠错 → 有上限只读执行
```

问数子图运行在当前进程，不再调用独立 HTTP 问数服务。配置 MySQL、Qdrant、Elasticsearch 与 Embedding 后即可启用；完整的元数据与索引契约见 [嵌入式问数部署说明](docs/analytics_setup.md)。

## Hybrid RAG 与附件隔离

```text
PDF / DOCX / Markdown / TXT
        ↓ 文档解析、重叠分块、来源元数据
Embedding 语义召回 ─┐
FTS5 / BM25 词法召回 ├─ RRF 融合 ─→ 可引用证据分块
                     ┘
```

中文材料在索引与查询两端都使用单字、双字 n-gram；FTS5 候选按 BM25 升序选取，再与语义候选做 RRF 融合。Embedding 模型和维度被记录到索引元数据，变更后会拒绝混用旧向量。上传资料写入独立的会话级索引，不会被其他会话检索。

建立全局知识库：

```bash
uv run python -m app.rag.indexer docs/knowledge_base
```

## 评测与可观测性

项目将“是否调用了 Agent”转化为可验证的运行轨迹。每轮运行生成 `trace.jsonl`，记录专家调用、预算拒绝、证据登记和结论级审查事件；完整原始工具结果保存在会话 `artifacts/`，避免挤占模型上下文。

```bash
uv run python -m app.evals.runner --trace output/session_<session_id>/trace.jsonl --cases tests/fixtures/eval_cases.jsonl --output artifacts/eval-result.json
```

[评测口径](docs/evaluation.md)记录了 MultiHop-RAG、AVeriTeC、并行延迟与上下文 Token 对比的复现要求。轨迹评测验证协作和安全契约；公开 Benchmark 仍需同时提交预测结果、配置与官方 scorer 才构成完整可复现证据。

### 已验证范围

| 验证项 | 当前结果 | 边界 |
| --- | --- | --- |
| Python 回归测试 | 8 项通过 | 覆盖路径隔离、RAG 空文件清理、结构化截断、SQL 写操作拒绝、证据与预算规则 |
| 问数子图装配 | LangGraph 可编译 | 未连接真实 MySQL/Qdrant/Elasticsearch 数据基础设施 |
| 依赖锁定 | `uv lock --check` 通过 | 不替代部署环境的连接与权限验证 |
| 展示界面 | README 预览图已更新 | 当前为可复现的界面展示，不替代完整前端端到端验收 |

## 快速启动

### 1. 安装与配置

```powershell
uv sync
Copy-Item .env.example .env
```

在 `.env` 中配置模型与可选外部情报；如需启用内置问数，还需配置：

```dotenv
ANALYTICS_METADATA_DATABASE_URL=mysql+asyncmy://analytics_reader:password@localhost:3306/analytics_meta
ANALYTICS_WAREHOUSE_DATABASE_URL=mysql+asyncmy://analytics_reader:password@localhost:3306/analytics_dw
ANALYTICS_QDRANT_URL=http://localhost:6333
ANALYTICS_ELASTICSEARCH_URL=http://localhost:9200
ANALYTICS_EMBEDDING_MODEL=text-embedding-v4
```

### 2. 启动服务

```powershell
uv run uvicorn app.api.server:app --host 0.0.0.0 --port 8000 --reload
```

```powershell
Set-Location frontend
pnpm install
pnpm dev
```

### 3. 尝试一个任务

```text
分析本月华南区域收入下降的可能原因：先查询收入、客户数与利润率，再检索近期外部变化和内部业务资料；输出证据链、可能原因、待验证项及行动建议，并生成 Markdown 报告。
```

## 本地验证

```powershell
uv run python -m unittest tests/test_platform_safety.py tests/test_context_engineering.py
uv lock --check
```

前端依赖首次安装后，如 pnpm 提示 `esbuild` 的构建脚本未获批准，先运行：

```powershell
pnpm approve-builds
pnpm run build
```

## 项目来源与授权

本项目的早期多智能体研究原型参考了 [didilili/deepsearch-agents](https://github.com/didilili/deepsearch-agents)。当前仓库已围绕企业经营决策场景重构专家协作边界、内置语义问数、自建 Hybrid RAG、结论级证据校验、上下文预算与轨迹评测。

发布前请继续核对保留代码的来源与授权范围；在确认所有保留实现的版权归属前，不应擅自声明新的开源许可证。
