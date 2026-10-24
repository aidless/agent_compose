"""ChainAware agent: enhances NativeFC with explicit chain-pattern memory.

Idea: rather than relying purely on natural-language heuristics, the agent
maintains a learned mapping from NL keywords to tool chains (built from training
tasks). At inference, it picks the chain whose keyword signature most closely
matches the new task's NL.

This is a lightweight "fine-tuning" surrogate that doesn't require actual LLM
fine-tuning — it implements the same inductive bias (expose the model to more
unseen chains during training) with a heuristic key-value lookup.

For real chain-aware fine-tuning of an LLM, see `methods/chain_aware_ft.py`.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from agent_compose.agents.base import Agent, AgentStep
from agent_compose.agents.native_fc import NativeFCAgent
from agent_compose.env.simulator import ExecutionTrace, ToolCall
from agent_compose.generator.tasks import Task
from agent_compose.tools import ToolLibrary


class ChainAwareAgent(Agent):
    """NativeFC + chain-pattern memory learned from training tasks."""

    name = "ChainAware-template"

    def __init__(
        self,
        tool_library: ToolLibrary,
        max_steps: int = 8,
        use_oracle: bool = False,
        use_generic_inference: bool = False,
        use_equiv_detector: bool = True,
        n_synthetic_chains: int = 50,
    ) -> None:
        super().__init__(tool_library, max_steps)
        self.use_generic_inference = use_generic_inference
        self.use_equiv_detector = use_equiv_detector
        self.inner = NativeFCAgent(
            tool_library,
            max_steps,
            use_oracle=use_oracle,
            use_generic_inference=use_generic_inference,
        )
        # chain_patterns: maps keyword-set -> most common tool chain
        self.chain_patterns: dict[frozenset[str], list[str]] = {}
        self.chain_counter: Counter[tuple[str, ...]] = Counter()
        # Synthetic unseen chains for productivity-like training
        self.n_synthetic = n_synthetic_chains
        self._synthetic_added = False

    def train_on(self, tasks: list[Task]) -> None:
        """Learn chain patterns from a set of training tasks."""
        self.chain_counter.clear()
        for task in tasks:
            # Extract keywords from natural language
            keywords = self._extract_keywords(task.natural_language)
            # Update chain frequency keyed by keyword signature
            sig = frozenset(keywords)
            self.chain_patterns[sig] = task.expected_chain
            self.chain_counter[tuple(task.expected_chain)] += 1

        # Augment with synthetic chains that mimic productivity test difficulty
        if not self._synthetic_added:
            self._add_synthetic_chains(tasks)
            self._synthetic_added = True

    def _add_synthetic_chains(self, train_tasks: list[Task]) -> None:
        """Generate synthetic compositional chains not seen in training.

        Strategy: take two 2-tool train chains that share no common pair,
        concatenate them. This simulates productivity-like generalization
        during training.
        """
        train_chains = [list(t.expected_chain) for t in train_tasks]
        added = 0
        for i in range(len(train_chains)):
            for j in range(i + 1, len(train_chains)):
                if added >= self.n_synthetic:
                    break
                c1, c2 = train_chains[i], train_chains[j]
                # Only concatenate chains that share a tool (so they can be glued)
                shared = set(c1) & set(c2)
                if not shared:
                    continue
                # Concatenate via shared tool: c1 + c2 (skip duplicate)
                bridge = next(iter(shared))
                # Find bridge index in c2
                if bridge in c2:
                    new_chain = c1 + c2[c2.index(bridge) + 1 :]
                    if 2 < len(new_chain) <= 5:  # Avoid trivial or huge chains
                        # Register the synthetic chain with the keyword signature
                        # of both source tasks combined
                        sig1 = self._extract_keywords(train_tasks[i].natural_language)
                        sig2 = self._extract_keywords(train_tasks[j].natural_language)
                        combined_sig = frozenset(sig1 | sig2)
                        self.chain_patterns[combined_sig] = new_chain
                        self.chain_counter[tuple(new_chain)] += 1
                        added += 1
            if added >= self.n_synthetic:
                break

    def _extract_keywords(self, nl: str) -> set[str]:
        """Extract tool-relevant keywords from natural language."""
        keyword_patterns = {
            "search_web": [
                "weather",
                "stock",
                "price",
                "search",
                "look up",
                "find",
                "search_web",
                "search_news",
                "search_academic",
            ],
            "search_news": ["news", "headline", "search_news"],
            "search_academic": ["paper", "research", "arxiv", "search_academic"],
            "search_image": ["image", "photo", "picture"],
            "send_email": ["email", "send to", "mail", "send_email"],
            "send_sms": ["sms", "text", "phone", "send_sms"],
            "send_push": ["push", "notification", "send_push"],
            "send_slack": ["slack", "channel", "send_slack"],
            "unit_convert": ["convert", "usd", "eur", "exchange", "currency"],
            "calculator": ["calculate", "compute", "sum", "average", "max"],
            "statistics": ["statistic", "mean", "median", "std"],
            "round": ["round"],
            "sort": ["sort"],
            "read_file": ["read", "file"],
            "write_file": ["write", "save", "report"],
            "append_file": ["append", "add to file"],
            "list_files": ["list", "directory", "glob"],
            "delete_file": ["delete", "remove"],
            "get_datetime": ["date", "time", "today"],
            "format_date": ["format", "strftime"],
            "calendar_add": ["calendar", "schedule", "event", "reminder", "calendar_add"],
            "calendar_list": ["list events", "calendar_list"],
            "fetch_url": ["fetch", "url", "page"],
            "summarize": ["summarize", "summary"],
            "translate": ["translate", "translation"],
            "sql_query": ["sql", "query", "database", "select"],
            "csv_filter": ["csv", "filter rows", "csv_filter"],
            "db_insert": ["insert", "db_insert"],
            "json_transform": ["json", "transform", "pick keys"],
            "image_resize": ["resize", "image_resize"],
            "image_crop": ["crop", "image_crop"],
            "image_classify": ["classify image", "image_classify", "vision"],
            "ocr_extract": ["ocr", "extract text", "ocr_extract"],
            "audio_transcribe": ["transcribe", "audio_transcribe", "speech to text"],
            "text_to_speech": ["text to speech", "synthesize", "tts"],
            "audio_classify": ["audio classify", "audio_classify"],
        }
        nl_lower = nl.lower()
        keywords: set[str] = set()
        for tool, patterns in keyword_patterns.items():
            for p in patterns:
                if p in nl_lower:
                    keywords.add(tool)
        return keywords

    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        # On first step, try to look up the chain from training memory
        if len(trace.calls) == 0:
            self._committed_chain = None
            keywords = self._extract_keywords(task.natural_language)
            # Look for a chain matching these keywords (or a superset)
            best_match = None
            best_overlap = -1
            for sig, chain in self.chain_patterns.items():
                overlap = len(sig & keywords)
                if overlap > best_overlap and (
                    sig.issubset(keywords) or keywords.issubset(sig) or overlap >= 2
                ):
                    best_overlap = overlap
                    best_match = chain
            if best_match is not None:
                self._committed_chain = best_match

        # If we have a committed chain from memory, follow it
        if self._committed_chain:
            # EquivAware: detect variant mentioned in task NL and substitute
            # into the committed chain (only on first step).
            if len(trace.calls) == 0 and self.use_equiv_detector:
                self._committed_chain = self._apply_equiv_substitution(task, self._committed_chain)
            step_num = len(trace.calls)
            if step_num < len(self._committed_chain):
                tool = self._committed_chain[step_num]
                args = self._build_args_for_tool(tool, task, trace)
                return AgentStep(
                    thought=f"ChainAware: following learned chain {self._committed_chain}",
                    action=ToolCall(
                        tool_name=tool, arguments=args, call_id=f"{task.task_id}_ca_s{step_num}"
                    ),
                )

        # Fall back to inner NativeFC
        return self.inner.act(task, trace)

    def _apply_equiv_substitution(self, task: Task, chain: list[str]) -> list[str]:
        """For each tool in chain, if task NL mentions a functionally-equivalent
        variant, substitute it in. Returns a new chain list.
        """
        nl_lower = task.natural_language.lower()
        new_chain = []
        for tool in chain:
            # Get all variants of this canonical tool
            variants = self.library.variant_of(tool)
            # Also: if `tool` itself is a variant in some other group's canonical,
            # keep it (no-op).
            chosen = tool
            for variant in variants:
                # Detect variant mention in NL (case-insensitive, word boundary)
                v_lower = variant.lower()
                # Use simple substring check; works because tool names are
                # uniquely identifying tokens (e.g., "search_news", "send_sms").
                if v_lower in nl_lower and v_lower != tool.lower():
                    chosen = variant
                    break
            new_chain.append(chosen)
        return new_chain

    def _build_args_for_tool(self, tool: str, task: Task, trace: ExecutionTrace) -> dict[str, Any]:
        """Same arg-construction logic as NativeFC."""
        return self.inner._build_args(tool, task, trace)

    def reset(self) -> None:
        if hasattr(self, "_committed_chain"):
            del self._committed_chain
        self.inner.reset() if hasattr(self.inner, "reset") else None
