# Instructions for Codex

## Subagents - model selection

- Always delegate to lower-cost / lower-intelligence models for subagents when the task does not need full reasoning.
- Prefer `gpt-5-mini`, `gpt-5-nano`, `luna`, or any `5.x mini/nano/luna` variant for Explore, Task, research, file search, and other low-intelligence subtasks.
- Reserve the full/flagship model only for tasks that explicitly require deep reasoning, synthesis, or architectural decisions.
- Do not use the top-tier model for subagents by default - default to the cheapest model that can do the job, and escalate only if it fails.

## Human-facing text - unslop

- Always apply the `unslop` skill when generating text that a human will read.
- This includes: pull request descriptions, commit messages that are externally visible, docs for human review, status reports, summaries, and any agent output describing work or reporting back to the user.
- Invoke via the `unslop` skill (Skill tool or equivalent) - run its scan/rewrite/self-audit steps before finalizing the text.
- Do not skip unslop for internal reasoning - only for human-visible output it is mandatory.

