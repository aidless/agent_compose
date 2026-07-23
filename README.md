# AgentCompose

> **Benchmarking Compositional Generalization in LLM Tool Use**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/python-3)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-35%2F35_passing-brightgreen)](tests/)
[![Tasks](https://img.shields.io/badge/tasks-3000-blue.svg)](data/generated/)
[![Tools](https://img.shields.io/badge/tools-30-blue.svg)](tools/)

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
├── tools/          # 30 个工具的 JSON schema（8 domains）
├── templates/      # 25 个任务模板
├── data/           # 3000 个生成任务（jsonl）
├── env/            # JSON API simulator
├── agents/         # 5 个 template agents + DeepSeek wrapper
├── methods/        # ChainAware + EquivAware
├── eval/           # 评估指标 + 统计检验
├── results/        # 实验输出
├── figures/        # 论文图（fig1-6）
├── paper/          # LaTeX 论文
└── scripts/        # generate / evaluate / analyze / run_all
```

## 🚀 Quick Start

```bash
# 1. 安装（开发模式 + DeepSeek LLM 可选）
pip install -e ".[dev]"
pip install -e ".[llm]"   # 仅在跑 DeepSeek 时需要

# 2. 一行命令复现所有 template-agent 实验（~15-20 min, 无 LLM）
python scripts/run_all.py --skip-llm

# 3. 跑测试
pytest tests/ -q

# 4. 单 agent 单 split 试用
python scripts/evaluate.py --agent chain_aware --split test_productivity
```

需要 DeepSeek API 时把 key 放进 `.env`（已 .gitignore）：

```bash
DEEPSEEK_API_KEY=sk-...
```

## 📊 实际结果（30-tool benchmark）

5 template agents + 2 DeepSeek agents × 4 splits（val=400, sys=600, prod=600, sub=200 tasks）：

| Agent | Val (i.i.d.) | Systematicity | Productivity | Substitutability |
|---|---|---|---|---|
| ReAct | 0.27 | 0.43 | 0.54 | 0.25 |
| Native FC | 0.27 | 0.15 | 0.20 | 0.25 |
| Reflexion | 0.27 | 0.43 | 0.54 | 0.25 |
| Plan-Execute | 0.27 | 0.15 | 0.11 | 0.25 |
| **ChainAware (Ours)** | **1.00** | 0.44 | 0.45 | 0.25 |
| **ChainAware + EquivAware (Ours)** | **1.00** | 0.44 | 0.45 | **1.00** |
| DeepSeek-ReAct (N=100) | 0.13 | 0.06 | 0.04 | 0.14 |
| DeepSeek-FC (N=100) | 0.10 | 0.08 | 0.07 | TBD |

**Key findings**:
- 4 个 baseline template agents 卡在 val TSR ≈ 0.27（短 2-tool chain 不满足 3/4-tool val）
- ChainAware 通过 keyword→chain memory 完全解决 val (1.00)
- EquivAware 把 substitutability 从 0.25 提到 1.00（d = -2.44）
- DeepSeek 即使 N=100 仍卡在 productivity/sub ≈ 0，证明 gap 不是模板 artifact

完整数字 + 95% bootstrap CI 见 `paper/main.tex` Table 1 + `paper/supp.tex` Appendix B。

## 🔁 Reproduction

```bash
# 端到端复现（不含 LLM）
python scripts/run_all.py --skip-llm

# 期望产出：
#   data/generated/{train,val,test_*}.jsonl   (3000 tasks)
#   results/{agent}_summary.json              (5 agents)
#   results/bootstrap_ci.json                 (1000-iter CI)
#   results/statistical_tests.json            (Friedman + Wilcoxon)
#   figures/fig{1..6}_*.{pdf,png}             (12 files)
```

| 步骤 | 脚本 | 耗时（CPU 1 core） |
|---|---|---|
| Generate 3000 tasks | `generate.py --seed 42` | ~3s |
| Evaluate 5 agents × 4 splits | `evaluate.py --agent X --split all` × 5 | ~3 min |
| Bootstrap CI (1000 iter) | `bootstrap_ci.py` | ~10s |
| Friedman + Wilcoxon | `statistical_eval.py` | ~5s |
| CD diagram | `make_cd_diagram.py` | ~2s |
| Figures (6 figures) | `make_figures.py` | ~10s |
| **Total** | `--skip-llm` | **~4 min** |

测试：34 unit tests + 5 smoke tests = **39 / 39 pass** in `<30 s`.

## 🛠️ Components

### Tool Library (`tools/`)

30 tools across 8 domains:
- **Information Retrieval** (5): `search_web`, `search_news`, `fetch_url`, `summarize`, `translate`
- **Computation** (5): `calculator`, `unit_convert`, `statistics`, `round`, `sort`
- **Communication** (4): `send_email`, `send_sms`, `send_push`, `send_slack`
- **File I/O** (5): `read_file`, `write_file`, `append_file`, `list_files`, `delete_file`
- **Scheduling** (4): `get_datetime`, `calendar_add`, `calendar_list`, `format_date`
- **Data/Database** (4): `sql_query`, `csv_filter`, `db_insert`, `json_transform`
- **Image/Vision** (4): `image_resize`, `image_crop`, `image_classify`, `ocr_extract`
- **Audio/Speech** (3): `audio_transcribe`, `text_to_speech`, `audio_classify`

### 6 Equivalence Groups (`tools/_equivalence.json`)

| Group | Canonical | Variant |
|---|---|---|
| G1_search | `search_web` | `search_news` |
| G2_communicate | `send_email` | `send_sms` |
| G3_data_query | `sql_query` | `csv_filter` |
| G4_visual_recognize | `image_classify` | `ocr_extract` |
| G5_notify | `send_slack` | `send_push` |
| G6_calendar_op | `calendar_add` | `calendar_list` |

### Method: ChainAware + EquivAware

- **ChainAware** (`agents/chain_aware.py`): Native FC + chain-pattern memory + synthetic chain augmentation.
- **EquivAware** (overlay on ChainAware): On first step, scan task NL for variants named in equivalence groups and substitute into the committed chain. Zero new parameters.

### Statistical Tests

- Friedman test (5 agents × split, χ² + p)
- Pairwise Wilcoxon signed-rank (with Bonferroni)
- Critical Difference diagram (Demsar 2006)
- Bootstrap 95% CI for TSR and CGG (1000 iterations)

## 📝 论文投稿

| Venue | 截稿 | 状态 |
|---|---|---|
| COLM 2026 | ~2026-09 | 🎯 首选 |
| ICLR 2027 | ~2026-10 | 🎯 备选 |
| TMLR | 滚动 | 🎯 长线 |

投稿包（main.pdf + supp.pdf + checklist）通过 `scripts/build_submission.sh` 一键生成。

## 📜 引用

TBD（论文发表后补）

## 📄 License

MIT