#!/usr/bin/env python3
import json
import os
import re

OVERRIDE_FILE = os.path.join(os.path.expanduser("~"), ".claude", ".allow-comments")


def override_active():
    return os.path.exists(OVERRIDE_FILE)

C_LIKE = {
    "js", "jsx", "ts", "tsx", "mjs", "cjs", "mts", "cts", "c", "h", "cpp", "hpp",
    "cxx", "hxx", "cc", "cs", "java", "go", "rs", "swift", "kt", "kts", "scala",
    "php", "dart", "proto", "sol", "zig", "groovy", "gradle", "jsonc", "json5",
    "m", "mm", "glsl", "hlsl", "wgsl",
}
CSS_LIKE = {"css", "scss", "less", "sass", "styl"}
HASH_LIKE = {
    "py", "pyi", "rb", "sh", "bash", "zsh", "fish", "pl", "pm", "r", "yaml", "yml",
    "toml", "tf", "tfvars", "hcl", "nix", "ex", "exs", "ps1", "psm1", "jl", "cr",
    "nim", "mk", "ini", "cfg", "conf", "service", "gemspec", "rake",
}
DASH_LIKE = {"lua", "sql", "hs", "elm", "adb", "ads", "vhd", "vhdl"}
XML_LIKE = {"html", "htm", "xml", "vue", "svelte", "svg", "xhtml", "astro"}

BASENAME_HASH = {
    "makefile", "dockerfile", "justfile", "rakefile", "gemfile", "vagrantfile",
    "brewfile", "procfile", "containerfile", ".bashrc", ".zshrc", ".bash_profile",
    ".profile", ".gitconfig", "cmakelists.txt", "pkgbuild",
}

PRAGMA = re.compile(
    r"""^(
        (\#|//|/\*|--|<!--)\s*todo(\([^)]*\))?\b
      | \#!
      | \#\s*(-\*-|coding[:=]|type:\s|noqa|pragma:|pylint:|mypy:|ruff:|fmt:|yapf:
             |isort:|nosec|pyright:|flake8:|bandit|shellcheck|rubocop:|pyre-
             |frozen_string_literal:|encoding:|hadolint|checkov:|tflint-ignore
             |syntax=|nolint|codespell:|pytype:|region\b|endregion\b)
      | //\s*(@ts-|ts-|eslint|prettier-ignore|biome-ignore|istanbul|c8\s|v8\s
             |jshint|jscs|tslint|deno-lint|oxlint|nolint|swiftlint|ktlint
             |clang-format|nolint|code\s+generated|\+build|@flow|@jsx|@license
             |@preserve|dprint-ignore|stylelint-|sourcemappingurl|\#\s*sourceurl
             |region\b|endregion\b)
      | //go:
      | /\*\s*(eslint|global|jshint|istanbul|c8\s|prettier-ignore|dprint-ignore
              |stylelint-|@license|@preserve|@flow|@jsx|nolint)
      | <!--\s*(prettier-ignore|eslint|markdownlint|dprint-ignore|stylelint-)
      | --\s*(noqa|luacheck|sqlfluff|@type)
    )""",
    re.VERBOSE | re.IGNORECASE,
)

DEF_LINE = re.compile(r"^\s*(async\s+def|def|class)\b.*:\s*$")


def config_for(path):
    base = os.path.basename(path).lower()
    ext = base.rsplit(".", 1)[-1] if "." in base else ""
    if base in BASENAME_HASH or base.startswith("dockerfile.") or base.startswith("makefile."):
        ext = "sh"
    if not ext:
        return None
    if ext in C_LIKE:
        return {"line": ["//"], "bo": "/*", "bc": "*/", "quotes": "\"'", "bt": True,
                "triple": False, "docstring": False}
    if ext in CSS_LIKE:
        return {"line": [], "bo": "/*", "bc": "*/", "quotes": "\"'", "bt": False,
                "triple": False, "docstring": False}
    if ext in HASH_LIKE:
        py = ext in ("py", "pyi")
        return {"line": ["#"], "bo": None, "bc": None, "quotes": "\"'", "bt": False,
                "triple": py, "docstring": py}
    if ext in DASH_LIKE:
        bo = "/*" if ext == "sql" else ("{-" if ext in ("hs", "elm") else "--[[")
        bc = "*/" if ext == "sql" else ("-}" if ext in ("hs", "elm") else "]]")
        return {"line": ["--"], "bo": bo, "bc": bc, "quotes": "\"'", "bt": False,
                "triple": False, "docstring": False}
    if ext in XML_LIKE:
        return {"line": [], "bo": "<!--", "bc": "-->", "quotes": "\"'", "bt": False,
                "triple": False, "docstring": False}
    return None


def scan_line(line, cfg, st):
    i = 0
    n = len(line)
    while i < n:
        if st["block"]:
            if cfg["bc"] and line.startswith(cfg["bc"], i):
                st["block"] = False
                i += len(cfg["bc"])
            else:
                i += 1
            continue
        if st["tq"]:
            if line.startswith(st["tq"], i):
                i += 3
                st["tq"] = None
            else:
                i += 1
            continue
        if st["bt"]:
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == "`":
                st["bt"] = False
            i += 1
            continue
        ch = line[i]
        if cfg["triple"]:
            opener = next((t for t in ('"""', "'''") if line.startswith(t, i)), None)
            if opener:
                end = line.find(opener, i + 3)
                if end == -1:
                    st["tq"] = opener
                    return None, i
                i = end + 3
                continue
        if cfg["bt"] and ch == "`":
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == "`":
                    break
                j += 1
            if j >= n:
                st["bt"] = True
                return None, i
            i = j + 1
            continue
        if ch in cfg["quotes"]:
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == ch:
                    break
                j += 1
            i = (j + 1) if j < n else n
            continue
        for marker in cfg["line"]:
            if line.startswith(marker, i):
                return i, i
        if cfg["bo"] and line.startswith(cfg["bo"], i):
            if cfg["bc"] and cfg["bc"] in line[i + len(cfg["bo"]):]:
                pass
            else:
                st["block"] = True
            return i, i
        i += 1
    return None, n


def find_comments(text, cfg):
    st = {"block": False, "tq": None, "bt": False}
    hits = []
    prev_code = None
    for lineno, raw in enumerate(text.split("\n"), 1):
        stripped = raw.strip()
        was_block = st["block"]
        was_tq = st["tq"]
        was_bt = st["bt"]
        if was_block or was_tq or was_bt:
            scan_line(raw, cfg, st)
            continue
        if not stripped:
            scan_line(raw, cfg, st)
            continue
        if PRAGMA.match(stripped):
            scan_line(raw, cfg, st)
            prev_code = stripped
            continue
        if cfg["docstring"] and (stripped.startswith('"""') or stripped.startswith("'''")):
            if prev_code is None or DEF_LINE.match(prev_code):
                hits.append((lineno, stripped))
        pos, _ = scan_line(raw, cfg, st)
        if pos is not None and not PRAGMA.match(raw[pos:].strip()):
            hits.append((lineno, stripped))
        else:
            prev_code = stripped
    return hits


def added_only(hits, old_text):
    old = {ln.strip() for ln in old_text.split("\n")}
    return [(n, s) for n, s in hits if s not in old]
