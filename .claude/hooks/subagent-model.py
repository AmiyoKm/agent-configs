#!/usr/bin/env python3
import json
import sys

BANNED = ("opus", "fable")
PARENT_INHERITING = {"", "general-purpose", "claude", "Explore", "Plan"}


def emit(obj):
    print(json.dumps(obj))
    sys.exit(0)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if payload.get("tool_name") != "Agent":
        return
    ti = payload.get("tool_input") or {}
    model = (ti.get("model") or "").strip().lower()
    subagent = ti.get("subagent_type") or ""

    if subagent == "fork":
        return

    if model in BANNED:
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"BLOCKED by ~/.claude/CLAUDE.md (Subagents - model selection): "
                    f"model={model!r} is not allowed for subagents. Use 'haiku' for "
                    "fast research/search/exploration, or 'sonnet' when more capability "
                    "is needed. Retry with one of those."
                ),
            }
        })

    if not model and subagent in PARENT_INHERITING:
        ti["model"] = "haiku"
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": (
                    "~/.claude/CLAUDE.md requires haiku/sonnet for subagents; no model "
                    "was set on a parent-inheriting agent, so it was pinned to haiku."
                ),
                "updatedInput": ti,
            }
        })


main()
