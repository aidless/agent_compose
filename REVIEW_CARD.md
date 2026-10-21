# REVIEW CARD — agent_compose（2026-09-04）

## 题目
AgentCompose: Quantifying Compositional Generalization in LLM Tool Use

## 裁决：5/10（Borderline 大修）→ 可救
- A 证据 6：摘要"成功率 at or below baseline, max 0.452"为假——重算 statistical_tests.json 确认 ReAct productivity=0.5417 > val 0.2675，CGG 为负，"striking gap"是低基线伪影。
- B 兴趣 5；C 清晰 6。
- D：无（有 run_all.py 复现模板）。

## Major
1. 摘要结论被重算推翻（ReAct > val，"striking gap"伪影）。
2. "Fine-Tuning"实为 keyword→chain 查表（无参数训练）。
3. 4 模板 agent val 全=0.2675 相同。
- Minor：占位 [anonymized URL]；COLM 版式。

## TODO
改摘要结论（ReAct 非低基线）；明示查表非训练；解释 val 恒定。

## 备注
证据完全复现表1（含 d=-2.44）与 Friedman；唯一有可执行复现脚本的篇目——值得返修。