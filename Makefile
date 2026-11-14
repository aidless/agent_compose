# --- acceptance_backfill (EVAL_ACCEPTANCE_STANDARD.md P4) ---
# 证据来源: tests/ + README.md L142（41 / 41 pass）
# 原命令 `python3 -m pytest tests -q` 本机 rc=2：5 个模块 ModuleNotFoundError:
# agent_compose（src-layout，未 pip install 时缺 PYTHONPATH=src）。
# 另一处：pyproject addopts 已含 -q，再传 -q 合成 -qq，pytest 9 会吞掉
# 「N passed」那行，看不出真结果 —— 故只保留 addopts 里的 -q。
.PHONY: eval

eval:
	PYTHONPATH=src python3 -m pytest tests
