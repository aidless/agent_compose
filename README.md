# AgentCompose

> **Benchmarking Compositional Generalization in LLM Tool Use**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

## 🎯 研究问题

LLM Agent 在工具调用时，**能否泛化到训练时从未见过的新工具组合**？

这是 Agent 走向真实生产场景的关键瓶颈：
- 真实场景下用户会不断**新增工具**
- 工作流会**重新排列**已有工具
- 功能等价的工具会有**不同的 schema**

现有 benchmark（ToolBench / AgentBench / BFCL / AppWorld 等）**都没有刻意隔离"组合"维度**，因此无法回答上述问题。

## 🔬 三种组合泛化能力

| 维度 | 英文 | 含义 |
|---|---|---|
| **系统性** | Systematicity | 见过原子 A, B, C，能否组合出 A→B→C？ |
| **生产性** | Productivity | 能否造出训练时从未共现的工具链？ |
| **替换性** | Substitutability | 功能等价的工具 X 换成 Y，能否识别？ |

## 📦 内容

```
agent_compose/
├── tools/          # 10 个工具的 JSON schema
├── templates/      # 10 个任务模板
├── data/           # 1300 个任务（生成后）
├── env/            # JSON API simulator
├── agents/         # baseline agents (ReAct, Reflexion, ...)
├── methods/        # chain-aware fine-tuning 方法
├── eval/           # 评估指标 + 统计检验
├── results/        # 实验输出
├── figures/        # 论文图
└── paper/          # LaTeX 论文
```

## 🚀 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# 生成 1300 任务
python scripts/generate.py

# 跑 baseline agent
python scripts/evaluate.py --agent react --split test_productivity

# 分析结果
python scripts/analyze.py --results results/react_productivity.json
```

## 📊 预期结果（基于文献推断）

| Agent | i.i.d. Test | Systematicity | Productivity | Substitutability |
|---|---|---|---|---|
| GPT-4 Native FC | ~78% | ~52% | ~34% | ~60% |
| Claude Native FC | ~80% | ~55% | ~38% | ~62% |
| ReAct | ~65% | ~42% | ~28% | ~50% |
| Reflexion | ~70% | ~48% | ~32% | ~55% |
| Toolformer (FT) | ~62% | ~45% | ~30% | ~48% |

→ **Compositional Generalization Gap ≈ 40+ points**

## 📝 论文投稿目标

| Venue | 截稿 | 状态 |
|---|---|---|
| COLM 2026 | ~2026-09 | 🎯 首选 |
| ICLR 2027 | ~2026-10 | 🎯 备选 |
| TMLR | 滚动 | 🎯 长线 |

## 📜 引用

TBD（论文发表后补）

## 📄 License

MIT
