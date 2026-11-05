"""The docustand plugin: manifests, skills and agents.

Version rule: `version` in `.claude-plugin/plugin.json` equals the topmost
released heading `## X.Y.Z` of `CHANGELOG.md`. While the changelog has only
`## Unreleased`, the version is `0.1.0`, the first release to come.
"""

import json
import os
import re
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO_ROOT

PLUGIN = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
SKILLS = sorted((REPO_ROOT / "skills").glob("*/SKILL.md"))
AGENTS = sorted((REPO_ROOT / "agents").glob("*.md"))
FIRST_VERSION = "0.1.0"
EXPECTED_SKILLS = {"repo-init", "project-docs", "quality-gates"}
WRITE_TOOLS = {"Bash", "Edit", "Write", "NotebookEdit"}
REMOVED_PATHS = ("docs/status", "docs/superpowers", "docs/plans")
# Names per the plugin and marketplace references of Claude Code.
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
INVENTORY_TABLE = "| Path | Kind | Decision (move/delete/keep) | Target |"


def frontmatter(path) -> dict:
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, f"{path}: no frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"{path}: frontmatter is not a mapping"
    return data


def tools(value) -> set[str]:
    if isinstance(value, str):
        return {t.strip() for t in value.split(",") if t.strip()}
    return set(value or [])


def released_version() -> str:
    heads = re.findall(r"^## (\d+\.\d+\.\d+)\b", (REPO_ROOT / "CHANGELOG.md").read_text(), re.M)
    return heads[0] if heads else FIRST_VERSION


def check_manifests_by_docs() -> None:
    """Fallback without the Claude Code CLI: the documented required fields."""
    plugin = json.loads(PLUGIN.read_text())
    assert NAME.match(plugin["name"])
    for key in ("version", "description"):
        assert isinstance(plugin.get(key), str) and plugin[key], key
    if "author" in plugin:
        assert plugin["author"].get("name")
    market = json.loads(MARKETPLACE.read_text())
    assert ID_PART.match(market["name"])
    assert market["owner"].get("name")
    assert market["plugins"], "no plugins"
    for entry in market["plugins"]:
        assert ID_PART.match(entry["name"])
        source = entry["source"]
        assert isinstance(source, str) and (source == "." or source.startswith("./"))
        assert ".." not in source


def test_plugin_manifest_valid():
    check_manifests_by_docs()


def test_plugin_validates_with_claude_cli(tmp_path):
    claude = shutil.which("claude")
    if claude is None:
        pytest.skip("claude CLI not installed")
    # A throwaway config dir keeps the validator away from ~/.claude.
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(tmp_path)}
    # `.` validates the marketplace; the root CLAUDE.md is a known warning, so
    # only the component directories run with --strict.
    for target in (["."], [".claude-plugin/plugin.json"], ["--strict", "skills"], ["--strict", "agents"]):
        result = subprocess.run([claude, "plugin", "validate", *target], cwd=REPO_ROOT, env=env,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, f"{target}\n{result.stdout}{result.stderr}"


def test_plugin_version_matches_changelog():
    plugin = json.loads(PLUGIN.read_text())
    assert plugin["name"] == "docustand"
    assert plugin["version"] == released_version()


def test_marketplace_lists_plugin_at_root():
    market = json.loads(MARKETPLACE.read_text())
    assert market["name"] == "docustand"
    entries = {e["name"]: e for e in market["plugins"]}
    assert set(entries) == {"docustand"}
    assert entries["docustand"]["source"] == "./"
    assert "version" not in entries["docustand"], "the version lives in plugin.json only"


def test_skills_have_frontmatter():
    assert {p.parent.name for p in SKILLS} >= EXPECTED_SKILLS
    for path in SKILLS:
        data = frontmatter(path)
        assert data.get("name") == path.parent.name, path
        assert isinstance(data.get("description"), str) and data["description"].strip(), path
        assert len(path.read_text().splitlines()) < 500, f"{path}: move detail to references/"


def test_agents_have_no_bash():
    assert AGENTS, "no agents"
    for path in AGENTS:
        data = frontmatter(path)
        assert data.get("name") == path.stem, path
        assert data.get("description"), path
        assert "tools" in data, f"{path}: without `tools` the agent inherits every tool"
        assert not tools(data["tools"]) & WRITE_TOOLS, path


def test_inventory_agent_is_read_only_and_cheap():
    data = frontmatter(REPO_ROOT / "agents" / "inventory.md")
    assert tools(data["tools"]) == {"Read", "Grep", "Glob"}
    assert data.get("model") == "haiku"
    assert INVENTORY_TABLE in (REPO_ROOT / "agents" / "inventory.md").read_text()


@pytest.mark.parametrize("removed", REMOVED_PATHS)
def test_skills_reference_no_removed_paths(removed):
    for root in (REPO_ROOT / "skills", REPO_ROOT / "agents"):
        for path in root.rglob("*"):
            if path.is_file():
                assert removed not in path.read_text(), f"{path} mentions {removed}"


def repo_init_text() -> str:
    text = (REPO_ROOT / "skills" / "repo-init" / "SKILL.md").read_text()
    return text + "".join(p.read_text() for p in (REPO_ROOT / "skills" / "repo-init" / "references").glob("*.md"))


def skill_texts():
    for path in (REPO_ROOT / "skills").rglob("*.md"):
        yield path, path.read_text()


def test_data_lists_are_quoted_for_zsh():
    # zsh expands unquoted brackets and braces as globs: "no matches found".
    unquoted = re.compile(r"--data\s+[\w-]+=[\[{]")
    for path, text in skill_texts():
        for n, line in enumerate(text.splitlines(), 1):
            assert not unquoted.search(line), f"{path}:{n}: quote the --data value: {line.strip()}"


def test_repo_init_finds_tags_not_releases():
    text = repo_init_text()
    assert "gh release view" not in text
    assert "git ls-remote --tags --refs --sort=-v:refname https://github.com/AnatoliiKo/docustand 'v*'" in text


def test_repo_init_names_plugin_root_for_references():
    head = (REPO_ROOT / "skills" / "repo-init" / "SKILL.md").read_text().split("## Rules", 1)[0]
    assert "Plugin root: `${CLAUDE_PLUGIN_ROOT}`" in head


def test_repo_init_carries_build_facts():
    text = repo_init_text()
    for fact in (
        "copier update -a .repo.yaml --defaults --data",
        "git status --porcelain",
        "${CLAUDE_PLUGIN_ROOT}/scripts/merge_existing.py conflicts",
        "${CLAUDE_PLUGIN_ROOT}/template/.mise/tasks/detect-stack",
        "mise run detect-stack",
        "gh api -X PUT repos/{owner}/{repo}/vulnerability-alerts",
        "gh secret set REPORT_APP_ID",
        "REPORT_APP_PRIVATE_KEY",
        "required_ci_branches",
        "docs/temp/inventory.md",
        "inventory",
        "hk install --mise",
        "merge_existing.py merge . docs/temp/rendered",
        "--skip <file 1>",
        "mise exec uv@0.13.7 pipx:copier@9.19.1 -- copier",
        "notes/probe.md",
        "otherwise stop",
        "`_src_path` to `gh:AnatoliiKo/docustand`",
        "explicit yes",
        "Branch protection waits until each branch exists on GitHub",
        "Fix the commas so the JSON stays valid.",
        "and the blank line before it",
        "profile first",
    ):
        assert fact in text, fact
