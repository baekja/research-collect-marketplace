# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **Claude Code Plugin Marketplace** packaging of the `firecrawl-pyzotero-zotero` paper-collection workflow. The original Python source lives in a sibling repo (`/Users/baekjw/Downloads/firecrawl-pyzotero-zotero workflow/`, preserved as lecture demo material); this repo restructures it into the plugin-marketplace contract so users can install it via `/plugin marketplace add`.

`TASK_SPEC.md` documents the Constitution (§0) and the SDD process used to build this repo. It is load-bearing for any future restructuring.

## Commands

```bash
# install editable + register MCPs (idempotent; prints rather than auto-runs deps)
bash plugins/research-collect/scripts/install.sh

# unit + schema tests (excludes integration by default — pyproject.toml addopts)
python3 -m pytest

# roundtrip against local Zotero desktop (Zotero app must be running with Local API on)
python3 -m pytest -m integration

# plugin/marketplace structure validation only
python3 -m pytest tests/test_plugin_structure.py -v

# single test
python3 -m pytest tests/test_normalize.py::TestBibKey::test_basic -v
```

The user-facing entrypoint inside Claude Code is the **research-collect skill** (natural-language auto-trigger on phrases like "논문 수집", "paper collection") or the **`/research-collect`** slash command.

## Architecture

### Layered file layout (non-obvious)

The Python package is **not** under `src/`. It lives at:

```
plugins/research-collect/skills/research-collect/scripts/research_collect/
```

The plugin marketplace contract requires the skill folder to be self-contained (so `/plugin install` copies code along with `SKILL.md`). `pyproject.toml` at repo root absorbs this layout via:

```toml
[tool.setuptools.packages.find]
where = ["plugins/research-collect/skills/research-collect/scripts"]
```

After `pip install -e .` you can still `from research_collect import ingest, normalize, ...` as if it were a normal `src/` layout.

### Pipeline (search → normalize → Zotero)

```
search backend (MCP or built-in)  →  data/raw.json (standard schema)
                                          ↓
                                    research_collect.ingest.run()
                                          ↓
                                    connect() — env-driven mode
                          ┌────────────────┴───────────────────┐
                          │ local: connector /saveItems         │
                          │ cloud: pyzotero + PDF download      │
                          │        + Unpaywall OA fallback      │
                          └─────────────────────────────────────┘
```

`data/raw.json` is the **search-backend abstraction boundary**. `SKILL.md` Step 1 picks among `firecrawl-mcp` / `exa-mcp` / `brave-search-mcp` / built-in `web_search` and transforms each backend's output into this schema. The downstream Python pipeline is backend-agnostic by design — never add `if backend == ...` branches in Python.

### Two-mode Zotero (env-driven)

`zotero_writer.connect()` selects based on environment, not flags:

- `ZOTERO_USER_ID` + `ZOTERO_API_KEY` both set → **cloud** (pyzotero, PDF attachment, Unpaywall OA fallback when `UNPAYWALL_EMAIL` is also set)
- Either missing → **local** (Zotero desktop `connector/saveItems`, metadata only, no PDF possible)

The HTTP-level reasons for the split are in `plugins/research-collect/skills/research-collect/references/zotero_local_limits.md` — the local API returns 400/404/501 for write/delete on items, so PDF attachment is structurally impossible in local mode.

### Triggering surface

Two ways for users to invoke the workflow:

1. **Natural-language auto-trigger** — the `description` field in `SKILL.md` frontmatter is what Claude matches against. Korean keywords, English keywords, and tool names (firecrawl, exa, brave-search) all live in that one field. Editing trigger phrases = editing this field, nothing else. Hard cap: **1536 chars** (official Skills spec), minimum 50.
2. **Explicit slash command** — `plugins/research-collect/commands/research-collect.md`. `$ARGUMENTS` + `argument-hint` make it auto-completable.

### Hooks (plugin-level safety)

`plugins/research-collect/hooks/{hooks.json, check_env.sh}` register a **PreToolUse Bash matcher** that blocks `git add .env` and `git commit` when `.env` is staged (exit 2 = hard block in the Claude Code hook contract). Works without any git pre-commit hook on the consumer side.

## Editing rules (from TASK_SPEC.md §0 Constitution)

Future edits must respect these:

1. **Don't modify Python logic in `scripts/research_collect/`** — the modules were extracted byte-for-byte from the sibling lecture repo and stay identical. Add behavior via new modules or new pipeline steps.
2. **Plugin must stay backend-agnostic.** New search backends are absorbed by the `data/raw.json` schema, not by Python branching.
3. **Don't auto-install deps.** `install.sh` prints commands; SKILL.md's Prerequisites check is advisory.
4. **Mode branch stays env-driven.** `connect()` reads `os.environ`. No CLI flag for mode selection.
5. **`.env` is never committed.** Enforced by the hook above and `.gitignore`. `.env.example` carries placeholders only.
6. **Korean for prose, English for code identifiers and commit messages.**
7. **Don't touch the sibling `firecrawl-pyzotero-zotero workflow/` directory.** It's the preserved lecture source; this repo is a packaging layer.

## Cross-file consistency points

When you change one of these, the others usually need a matching update:

| If you change… | Also update… |
|----------------|--------------|
| Search backend list | `SKILL.md` Step 1, `references/search_backends.md`, `tests/test_plugin_structure.py::TestSkillMd::test_mentions_all_backends` |
| Zotero local/cloud behavior | `SKILL.md` "Mode selection logic" + "Known limitations" tables, `references/zotero_local_limits.md` |
| Slash command args | `commands/research-collect.md` `argument-hint` frontmatter **and** the parsing instructions in the body |
| Python package path | `pyproject.toml` `[tool.setuptools.packages.find]`, `tests/test_plugin_structure.py::TestScriptsLayout` |
| Plugin manifest fields | `tests/test_plugin_structure.py::TestPluginJson` (validates `name`/`version`/`description`, kebab-case, semver) |
| SKILL.md trigger phrases | Stay within `[50, 1536]` chars (`test_has_yaml_frontmatter`) |

`tests/test_plugin_structure.py` is the executable spec for these contracts — run it after any plugin-shape edit.
