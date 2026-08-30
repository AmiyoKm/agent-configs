#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comment_scan import added_only, config_for, find_comments, override_active


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def main():
    if override_active():
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if not path:
        return

    if tool == "Write":
        new_text = ti.get("content") or ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                old_text = fh.read()
        except OSError:
            old_text = ""
        cfg = config_for(path)
    elif tool == "Edit":
        new_text = ti.get("new_string") or ""
        old_text = ti.get("old_string") or ""
        cfg = config_for(path)
    elif tool == "NotebookEdit":
        if (ti.get("cell_type") or "code") != "code":
            return
        new_text = ti.get("new_source") or ""
        old_text = ""
        cfg = config_for("cell.py")
    else:
        return

    if cfg is None or not new_text.strip():
        return

    hits = added_only(find_comments(new_text, cfg), old_text)
    if not hits:
        return

    shown = "\n".join(f"  line {n}: {s[:100]}" for n, s in hits[:8])
    more = f"\n  ... and {len(hits) - 8} more" if len(hits) > 8 else ""
    deny(
        "BLOCKED by ~/.claude/CLAUDE.md (Code comments): this edit adds "
        f"{len(hits)} new comment line(s) to {os.path.basename(path)}:\n{shown}{more}\n\n"
        "Never add comments, docstrings, or section headers. Only `TODO:` comments are "
        "allowed, unless the user explicitly asked for a comment in this request. Remove them and retry. "
        "If the user DID explicitly ask, tell them to run `touch ~/.claude/.allow-comments` "
        "to lift the block; do not create that file yourself."
    )


if __name__ == "__main__":
    main()
