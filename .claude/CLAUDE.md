## Human-facing text - unslop

- Always apply the `unslop` skill when generating text that a human will read.
- This includes: pull request descriptions, docs for human review, status reports, summaries, and any agent output describing work or reporting back to the user.
- Do not skip unslop for internal reasoning - only for human-visible output it is mandatory.
- Match the length of anything written to disk - reports, research notes, PR bodies, docs - to what the task actually needs. Cover the substance, then stop. No padding, no redundant summary section, no boilerplate.

## Subagents - opencode only

- Do not spawn Anthropic-model subagents (Explore, general-purpose, Plan, code-simplifier, etc). They burn tokens for work I can get directly.
- The `opencode-*` family is the exception and is encouraged. Those run on free non-Anthropic models through a haiku dispatcher, so they cost me almost nothing.
  - `opencode-explore` - read-only search. "Where is X", tracing call paths, mapping a module, anything breadth-first across files.
  - `opencode-general` - bulk mechanical work (repetitive edits, boilerplate, scripted refactors, fixtures), and second opinions from another model. Pass "model: provider/id" when I name one.
  - `opencode-code-review` - read-only review of finished work.
- All of them default to `opencode/muse-spark-1.2-contributor-free`. Never ask me which model to use; only override when I name one.
- I may still explicitly ask for an Anthropic subagent in a specific request. That request is the only permission.

## Code review with opencode-code-review

- Run `opencode-code-review` when a coherent piece of code is finished - a feature wired up, a bug fixed, a refactor landed. Not after every edit, and not once at the end of a long session when the findings are too tangled to act on.
- Prefer to review before I have moved on. A finding on the change I just made is cheap to fix; the same finding three changes later is not.
- Send it the diff (`git diff HEAD`), the project's CLAUDE.md, and a note if any `.ts`/`.tsx` file changed so it applies the `typescript-best-practices` skill. If the project has crtk conventions, tell it to use the crtk MCP.
- Say what the change was meant to do. The reviewer reads the diff, not my intent, and without it a deliberate choice reads as a mistake.
- Review before committing, not after. Review before opening a PR, always.
- The project's CLAUDE.md is the authority on conventions. Where it is silent, follow the surrounding code.
- Judge the findings myself - free models produce false positives. Fix the real ones and move on; tell me only what mattered. Pay special attention to bugs and to convention breaks like types declared in the wrong file, code in the wrong layer, or dead code left behind.

## Progress updates

- One sentence before the first tool call saying what I am about to do. Then work.
- While working, speak up only when I find something that changes the plan, hit a real blocker, or am about to do something you would want to stop.
- When done, lead with the outcome. What happened or what I found comes first; detail after, for when you want it.
- Do not narrate each tool call, do not restate the request back to you, and do not announce a step and then immediately do it.

## Code comments

- Never add comments to code. Not explanatory comments, not section headers, not docstrings.
- `TODO:` comments are the one allowed form. `FIXME`, `NOTE`, `XXX` and the rest are not.
- Otherwise the only exception is when I explicitly ask for a comment or docstring in that specific request.
- Do not remove existing comments unless asked; just do not write new ones.

This rule is enforced by PreToolUse hooks, not by good intentions. `Write`, `Edit`,
`NotebookEdit`, and Bash heredoc writes into code files are all scanned, and any edit
that adds a new comment line is denied outright. `TODO:` comments and linter/compiler pragmas (`# type:`,
`# noqa`, `// @ts-expect-error`, `//go:build`, shebangs, and similar) are exempt.
If I explicitly ask for a comment, I will run `touch ~/.claude/.allow-comments`
myself to lift the block. Never create that file on your own.
