"""Plugin과 Marketplace 구조 정합성 검증."""
import json
import os
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
    def test_exists_and_executable(self):
        path = REPO_ROOT / "plugins" / "research-collect" / "scripts" / "install.sh"
        assert path.exists()
        import subprocess
        r = subprocess.run(["bash", "-n", str(path)], capture_output=True)
        assert r.returncode == 0, f"syntax error: {r.stderr.decode()}"


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
    """Hooks — Task 8.5."""

    HOOKS_JSON = REPO_ROOT / "plugins" / "research-collect" / "hooks" / "hooks.json"
    CHECK_SH = REPO_ROOT / "plugins" / "research-collect" / "hooks" / "check_env.sh"

    def test_hooks_json_valid(self):
        data = json.loads(self.HOOKS_JSON.read_text())
        assert "hooks" in data
        assert "PreToolUse" in data["hooks"]

    def test_check_env_sh_syntax(self):
        import subprocess
        r = subprocess.run(["bash", "-n", str(self.CHECK_SH)], capture_output=True)
        assert r.returncode == 0, f"syntax error: {r.stderr.decode()}"

    def test_check_env_sh_executable(self):
        assert os.access(self.CHECK_SH, os.X_OK), \
            f"not executable: {self.CHECK_SH}"
