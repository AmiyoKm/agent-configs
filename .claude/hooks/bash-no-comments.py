#!/usr/bin/env python3
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comment_scan import config_for, find_comments, override_active

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
REDIRECT = re.compile(r"(?:>>?|\btee\b(?:\s+-a)?)\s+([^\s;|&<>]+)")


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def heredoc_blocks(command):
    lines = command.split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = HEREDOC.search(line)
        if not m:
            i += 1
            continue
        delim = m.group(2)
        allow_tabs = "<<-" in line[: m.end()]
        targets = REDIRECT.findall(line)
        body = []
        j = i + 1
        while j < len(lines):
            probe = lines[j].lstrip("\t") if allow_tabs else lines[j]
            if probe.strip() == delim:
                break
            body.append(lines[j])
            j += 1
        blocks.append((targets, "\n".join(body)))
        i = j + 1
    return blocks


def main():
    if override_active():
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if payload.get("tool_name") != "Bash":
        return
    command = ((payload.get("tool_input") or {}).get("command")) or ""
    if "<<" not in command:
        return

    findings = []
    for targets, body in heredoc_blocks(command):
        if not body.strip():
            continue
        for target in targets:
            path = target.strip("'\"")
            if os.path.basename(path).startswith("."):
                continue
            cfg = config_for(path)
            if cfg is None:
                continue
            hits = find_comments(body, cfg)
            if hits:
                findings.append((path, hits))
            break

    if not findings:
        return

    detail = []
    total = 0
    for path, hits in findings:
        total += len(hits)
        for n, s in hits[:5]:
            detail.append(f"  {os.path.basename(path)} line {n}: {s[:100]}")
    deny(
        "BLOCKED by ~/.claude/CLAUDE.md (Code comments): this shell command writes "
        f"{total} comment line(s) into a code file via heredoc:\n" + "\n".join(detail[:8]) +
        "\n\nNever add comments, docstrings, or section headers. Only `TODO:` comments are "
        "allowed, unless the user explicitly asked for a comment in this request. Rewrite the command without them. "
        "If the user DID explicitly ask, tell them to run `touch ~/.claude/.allow-comments` "
        "to lift the block; do not create that file yourself."
    )


if __name__ == "__main__":
    main()
