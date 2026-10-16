# Evaluation Protocol

本页记录简历中涉及的评测口径、基线与复现要求。结果与轨迹评测分开：前者衡量任务质量，后者验证一次运行是否遵守专家协作、预算与证据契约。

## Reported results

| 场景 | Baseline | Method | Metric | Reported result |
| --- | --- | --- | --- | --- |
| MultiHop-RAG | Dense retrieval | Hybrid retrieval + RRF | Hits@10 | 71.8% → 83.6% |
| AVeriTeC | Basic pipeline | Claim-evidence verification | AVeriTeC Score | 0.41 → 0.59 |
| Cross-source research | Serial research | TaskGroup parallel research | Mean latency | -35.4% |
| Context management | Raw tool context | Artifact offloading + structured summary | Input tokens | -38.0% |

## Benchmark sources and scorers

| Benchmark | Official dataset / task definition | Official evaluation entry | How this project uses it |
| --- | --- | --- | --- |
| MultiHop-RAG | [Dataset repository](https://github.com/yixuantt/MultiHop-RAG) · [paper](https://arxiv.org/abs/2401.15391) | [`retrieval_evaluate.py`](https://github.com/yixuantt/MultiHop-RAG/blob/main/retrieval_evaluate.py) | Compare dense retrieval with Hybrid RAG + RRF using Hits@10. Keep the query set, corpus version and top-k fixed across variants. |
| AVeriTeC | [Dataset repository](https://github.com/MichSchli/AVeriTeC) · [paper](https://arxiv.org/abs/2305.13117) | [`eval.py`](https://github.com/MichSchli/AVeriTeC/blob/main/AVeriTeC-score/eval.py) | Evaluate claim-level verdicts and evidence sufficiency. Preserve the official output schema before scoring. |

The benchmark links make the task definitions and official scoring procedures inspectable; they do **not** by themselves prove the reported numbers above. The raw prediction files, run manifests and scorer outputs for those numbers are not committed yet, so the table should be treated as a recorded experiment result rather than independently reproducible evidence.

## Reproduction contract

每一次可公开对比必须提交以下信息，不能只保留汇总数字：

- 数据集名称、版本、样本数、切分与外部知识使用规则；
- 模型、Embedding 模型、重排模型、提示词版本与随机种子；
- baseline 的完整定义，以及并行实验使用相同请求、相同模型和相同重试策略的证据；
- 官方 scorer 或可执行评分脚本、原始预测结果与汇总结果路径；
- 对失败、超时与无答案样本的处理规则。

当前仓库已提供运行时结构评测：

```bash
uv run python -m app.evals.runner --trace output/session_<session_id>/trace.jsonl --cases tests/fixtures/eval_cases.jsonl --output artifacts/eval-result.json
```

该命令验证专家覆盖、预算拒绝、证据登记及结论审查，不会替代 MultiHop-RAG 或 AVeriTeC 的官方 scorer。将公开 Benchmark 的预测文件、配置和 scorer 纳入 `artifacts/evaluation/` 后，才可把上表结果视为可由仓库独立复跑的证据。
