# AGENTS.md — [anonymized repository]

> **本文件用途**：Agent Agent 在 `agent_compose/` 工作时的单一来源项目 manifest。
> **优先级**：本文件 < 用户级 AGENTS.md (`[user]/.zcode/AGENTS.md`)。冲突时遵循上级。
> **维护者**：项目作者。修改前先告知用户。

---

## 0. 项目定义

**AgentCompose** 是一个**研究型 benchmark 项目**，目标：量化 LLM Agent 在工具调用中的**组合泛化能力**。

- **核心交付**：可复现的 benchmark + 论文（COLM 2026 / ICLR 2027 / TMLR）
- **状态**：Alpha（MVP 阶段，2026-07 启动）
- **独立 git 仓**：✅（与 genesis-master 完全隔离）

## 1. 项目结构

```
agent_compose/
├── tools/          # 10 个工具的 JSON schema（必填）
├── templates/      # 10 个任务模板（必填）
├── generator/      # 任务生成器
├── data/           # 生成的 1300 任务
├── env/            # JSON API simulator
├── agents/         # baseline agents
├── methods/        # 我们提的方法（chain-aware FT）
├── eval/           # 评估 + 统计检验
├── results/        # 实验输出（gitignore raw/）
├── figures/        # 论文图
├── paper/          # LaTeX 论文
├── scripts/        # entry points
├── tests/          # pytest
├── pyproject.toml
├── AGENTS.md       # 本文件
└── README.md
```

## 2. 工作约定

### 2.1 Python 风格
- Python 3.9+（与 genesis-master 保持一致）
- 100 字符行长（black/ruff 配置）
- 类型注解 + docstring（英文）
- pydantic 用于 schema 验证
- 使用 `pathlib.Path`，不用 `os.path`

### 2.2 数据格式
- 所有数据集用 JSONL（一行一个 JSON）
- 工具 schema 用 JSON Schema 标准
- 实验结果用 JSON（结构化）+ Markdown（人类可读总结）

### 2.3 Git
- 主分支：`main`
- 提交规范：参考 Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- 每次 commit 必须能跑通 `pytest`
- **不要提交**：API keys、原始结果日志、大型 JSONL

### 2.4 复现性
- 所有实验必须固定 random seed（`numpy`, `random`, `torch` 三方都要设）
- 实验环境用 `requirements.txt` + `pyproject.toml` 锁定
- 数据生成脚本必须 deterministic（给定 seed → 同样输出）

### 2.5 API 成本控制
- **开发阶段**：用 JSON API simulator（自己写的），不调真实 LLM
- **正式实验**：用 GPT-4 / Claude API，跑预算 $50 上限
- 每次 LLM 调用记录 token 数 + cost

## 3. Agent 行为规则

### 3.1 子 agent 限制
- **已知问题**：Agent 子 agent (`Agent` 工具) 在本环境下 model provider 不可用
- **应对**：所有任务由主 agent 直接执行，或拆成独立小任务用 `Bash`/`WebFetch` 串行做
- **不要**：等待子 agent 自动完成（会一直失败）

### 3.2 Skills 使用
- **可用**：用户级 18 个 skill（`ablation-design`、`statistical-analysis`、`uncertainty-quantification` 等）
- **重点用**：
  - `ablation-design`：写论文 ablation 章节时
  - `statistical-analysis`：显著性检验（Wilcoxon, paired t）
  - `reproducibility`：写 reproducibility checklist 时
  - `academic-writing`：写论文时（IMRaD, hedging）
- **项目级**：`tmlr-submission` skill（如果投稿 TMLR）

### 3.3 网络操作
- WebSearch 在本环境**不可用**
- WebFetch 部分站点超时，但 arXiv / GitHub raw / OpenReview 通常可用
- 不要 `git clone` 外部仓库（除非用户明确）

### 3.4 危险操作
- ❌ 不要 `rm -rf` 已生成的数据（先确认）
- ❌ 不要改写已写的论文段落（除非明确要求）
- ❌ 不要自动 commit（除非用户明确说 "commit"）
- ❌ 不要自动 push
- ❌ 不要跑会消耗 API 成本的实验（除非预算已批）

## 4. 当前阶段：MVP（2026.7.23 - 8.6）

### 进行中
- [x] 项目脚手架（pyproject.toml, .gitignore, README, AGENTS.md）
- [ ] 10 工具 JSON schema
- [ ] 10 任务模板
- [ ] 任务生成器
- [ ] JSON API simulator
- [ ] 3 个 baseline agent（ReAct, GPT-4 FC, Claude FC）
- [ ] 评估指标 + Wilcoxon 检验
- [ ] MVP 实验（小规模）

### 下一阶段（Phase 2, 2026.8.7 - 8.31）
- 5+ agent 完整评估
- 错误分析
- chain-aware fine-tuning 方法
- 消融实验
- 完整论文初稿

## 5. 与 genesis-master 的关系

- **完全独立**：`agent_compose/` 不引用 genesis-master 任何代码或数据
- **可以借鉴**：genesis-master 的工程化经验（如 pytest 模式、CI 配置）
- **不要混淆**：两个项目不要相互 import，不要写"自动同步"脚本

## 6. 用户的核心偏好（项目级补充）

- 中文交流，英文写作（论文、注释、API 错误保留英文）
- 简洁优先：能 3 句说清不写 5 句
- 不夸大：负结果也报
- 关注可复现性：实验脚本 + 论文 + 数据三位一体
- 引用代码用 `file_path:line_number` 格式
- 不可逆操作（删数据、覆盖文件）必须先确认

## 7. 元信息

- 文件版本：v0.1
- 编制日期：2026-07-23
- 编制人：Agent（基于用户级 AGENTS.md 派生）
- 反馈：发现冲突或补充，请告知用户更新本文件
