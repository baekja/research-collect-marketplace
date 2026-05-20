"""Plugin과 Marketplace 구조 정합성 검증."""
import json
import os
import sys
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_JSON = REPO_ROOT / "plugins" / "research-collect" / ".claude-plugin" / "plugin.json"
SKILL_MD = REPO_ROOT / "plugins" / "research-collect" / "skills" / "research-collect" / "SKILL.md"
SCRIPTS_DIR = REPO_ROOT / "plugins" / "research-collect" / "skills" / "research-collect" / "scripts" / "research_collect"
REFERENCES_DIR = REPO_ROOT / "plugins" / "research-collect" / "skills" / "research-collect" / "references"


class TestMarketplaceJson:
    def test_exists(self):
        assert MARKETPLACE_JSON.exists(), f"missing: {MARKETPLACE_JSON}"

    def test_valid_json(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        assert "name" in data
        assert "plugins" in data
        assert isinstance(data["plugins"], list)
        assert len(data["plugins"]) >= 1

    def test_name_kebab_case(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        import re
        assert re.fullmatch(r"[a-z0-9-]+", data["name"]), \
            f"marketplace name must be kebab-case: {data['name']}"

    def test_not_reserved_name(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        reserved = {
            "claude-code-marketplace", "claude-code-plugins",
            "claude-plugins-official", "anthropic-marketplace",
            "anthropic-plugins", "agent-skills",
            "knowledge-work-plugins", "life-sciences",
        }
        assert data["name"] not in reserved


class TestPluginJson:
    def test_exists(self):
        assert PLUGIN_JSON.exists(), f"missing: {PLUGIN_JSON}"

    def test_valid_json(self):
        data = json.loads(PLUGIN_JSON.read_text())
        for key in ("name", "version", "description"):
            assert key in data, f"plugin.json missing key: {key}"

    def test_name_kebab_case(self):
        import re
        data = json.loads(PLUGIN_JSON.read_text())
        assert re.fullmatch(r"[a-z0-9-]+", data["name"])

    def test_version_semver(self):
        import re
        data = json.loads(PLUGIN_JSON.read_text())
        assert re.fullmatch(r"\d+\.\d+\.\d+", data["version"])


class TestSkillMd:
    def test_exists(self):
        assert SKILL_MD.exists()

    def test_has_yaml_frontmatter(self):
        text = SKILL_MD.read_text()
        assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
        end = text.find("\n---\n", 4)
        assert end > 0, "SKILL.md frontmatter not closed"
        fm = yaml.safe_load(text[4:end])
        assert "name" in fm
        assert "description" in fm
        assert len(fm["description"]) <= 1536, "description too long (official spec: 1536)"
        assert len(fm["description"]) >= 50, "description too short — Claude won't trigger well"

    def test_required_sections(self):
        text = SKILL_MD.read_text()
        required = [
            "When to use",
            "Prerequisites",
            "Step 1",
            "Step 2",
            "Mode selection",
            "Troubleshooting",
        ]
        for section in required:
            assert section in text, f"SKILL.md missing section: {section}"

    def test_mentions_all_backends(self):
        text = SKILL_MD.read_text().lower()
        for backend in ("firecrawl", "exa", "brave", "web_search"):
            assert backend in text, f"SKILL.md must mention backend: {backend}"


class TestScriptsLayout:
    def test_python_package_present(self):
        assert (SCRIPTS_DIR / "__init__.py").exists()
        for mod in ("ingest", "normalize", "md_writer", "zotero_writer", "pdf_downloader"):
            assert (SCRIPTS_DIR / f"{mod}.py").exists(), f"missing: {mod}.py"

    def test_references_present(self):
        for doc in ("zotero_local_limits.md", "unpaywall_setup.md", "search_backends.md"):
            path = REFERENCES_DIR / doc
            assert path.exists(), f"missing: {doc}"
            assert path.stat().st_size > 500, f"too short: {doc}"


class TestInstallScript:
    SH = REPO_ROOT / "plugins" / "research-collect" / "scripts" / "install.sh"
    PS1 = REPO_ROOT / "plugins" / "research-collect" / "scripts" / "install.ps1"

    @pytest.mark.skipif(sys.platform == "win32", reason="bash optional on Windows")
    def test_sh_exists_and_valid(self):
        assert self.SH.exists()
        import subprocess
        r = subprocess.run(["bash", "-n", str(self.SH)], capture_output=True)
        assert r.returncode == 0, f"syntax error: {r.stderr.decode()}"

    def test_ps1_exists(self):
        assert self.PS1.exists(), \
            f"missing PowerShell installer (Windows parity): {self.PS1}"

    def test_ps1_registers_both_mcps(self):
        text = self.PS1.read_text()
        assert "claude mcp add firecrawl" in text
        assert "claude mcp add zotero" in text
        assert "pip install -e" in text


class TestCommands:
    """Slash command `/research-collect` — Task 6.5."""

    CMD = REPO_ROOT / "plugins" / "research-collect" / "commands" / "research-collect.md"

    def test_exists(self):
        assert self.CMD.exists(), f"missing: {self.CMD}"

    def test_has_frontmatter(self):
        text = self.CMD.read_text()
        assert text.startswith("---\n"), "command must start with YAML frontmatter"
        end = text.find("\n---\n", 4)
        assert end > 0, "command frontmatter not closed"
        fm = yaml.safe_load(text[4:end])
        assert "description" in fm
        assert "argument-hint" in fm

    def test_uses_arguments_token(self):
        text = self.CMD.read_text()
        assert "$ARGUMENTS" in text, "command body must reference $ARGUMENTS"


class TestHooks:
    """Hooks — cross-platform Python implementation."""

    HOOKS_JSON = REPO_ROOT / "plugins" / "research-collect" / "hooks" / "hooks.json"
    CHECK_PY = REPO_ROOT / "plugins" / "research-collect" / "hooks" / "check_env.py"
    CHECK_SH_LEGACY = REPO_ROOT / "plugins" / "research-collect" / "hooks" / "check_env.sh"

    def test_hooks_json_valid(self):
        data = json.loads(self.HOOKS_JSON.read_text())
        assert "hooks" in data
        assert "PreToolUse" in data["hooks"]

    def test_hooks_json_invokes_python_not_bash(self):
        data = json.loads(self.HOOKS_JSON.read_text())
        cmd = data["hooks"]["PreToolUse"][0]["command"]
        assert cmd.startswith("python "), \
            f"hook command must start with 'python ' for cross-platform support, got: {cmd!r}"
        assert "check_env.py" in cmd

    def test_check_env_py_exists_and_compiles(self):
        assert self.CHECK_PY.exists(), f"missing: {self.CHECK_PY}"
        import py_compile
        py_compile.compile(str(self.CHECK_PY), doraise=True)

    def test_legacy_sh_removed(self):
        assert not self.CHECK_SH_LEGACY.exists(), \
            "check_env.sh should have been removed in favor of check_env.py"


class TestCrossPlatform:
    """Windows compatibility contracts."""

    GITATTR = REPO_ROOT / ".gitattributes"

    def test_gitattributes_pins_sh_to_lf(self):
        assert self.GITATTR.exists(), "missing .gitattributes (Windows CRLF guard)"
        text = self.GITATTR.read_text()
        assert "*.sh" in text and "eol=lf" in text, \
            ".gitattributes must force LF for *.sh files"

    def test_no_python3_in_user_facing_docs(self):
        """python3.exe does not exist on Windows by default."""
        roots = [
            SKILL_MD,
            REPO_ROOT / "plugins" / "research-collect" / "commands" / "research-collect.md",
            REFERENCES_DIR / "unpaywall_setup.md",
        ]
        for path in roots:
            text = path.read_text()
            assert "python3" not in text, \
                f"{path.name} still references python3 (breaks on Windows)"
