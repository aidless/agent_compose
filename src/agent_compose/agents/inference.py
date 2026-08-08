"""Generic library-agnostic tool inference for template agents.

Used only when `use_generic_inference=True` (external-validity runs). The
default heuristic agents keep their original hardcoded keyword maps so the
main-benchmark results are unchanged.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "with", "to", "of", "in", "on",
    "current", "given", "then", "using", "via", "from", "your", "you", "and",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", str(text).lower()) if t not in STOPWORDS and len(t) > 2}


def infer_tool_generic(library, nl: str, called: Iterable[str]) -> Optional[str]:
    """Return the uncalled library tool whose name/description/params best match the NL."""
    called = set(called)
    nl_tokens = _tokens(nl)
    best, best_score = None, 0
    for tool in library.all_tools:
        if tool.name in called:
            continue
        keywords = set(tool.name.split("_"))
        keywords |= _tokens(tool.description or "")
        for prop in (tool.parameters or {}).get("properties", {}):
            keywords |= _tokens(str(prop))
        score = len(keywords & nl_tokens)
        if tool.name.lower() in nl:
            score += 2
        if score > best_score:
            best, best_score = tool.name, score
    return best if best_score > 0 else None


def build_args_generic(library, tool_name: str, task, trace) -> dict[str, Any]:
    """Build arguments by binding task parameters to schema property names."""
    tool = library.get(tool_name)
    props = (tool.parameters or {}).get("properties", {})
    params = task.parameters or {}
    norm_params = {re.sub(r"[^a-z0-9]", "", str(k)).lower(): v for k, v in params.items()}
    args: dict[str, Any] = {}
    for name, spec in props.items():
        key = re.sub(r"[^a-z0-9]", "", str(name)).lower()
        if key in norm_params:
            args[name] = norm_params[key]
        elif name in params:
            args[name] = params[name]
        else:
            t = (spec or {}).get("type", "string")
            args[name] = 0 if t == "number" else ("sample" if t in ("string", "object") else [])
    return args