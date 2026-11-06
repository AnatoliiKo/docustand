import json
import re
import tomllib

import yaml

from conftest import REPO_ROOT

STANDARD = REPO_ROOT / "template/.mise/conf.d/standard.toml.jinja"
HK_PKL = REPO_ROOT / "template/hk.pkl.jinja"
EXACT = re.compile(r'^"?[\w:@/.-]+"? = "\d+(\.\d+)+"$')


def tool_lines() -> list[str]:
    text = STANDARD.read_text()
    section = text.split("[tools]", 1)[1].split("\n[", 1)[0]
    return [line for line in section.splitlines() if line and not line.startswith(("#", "{%"))]


def test_every_tool_is_pinned_without_jinja():
    lines = tool_lines()

    assert lines
    for line in lines:
        assert EXACT.match(line), line


def test_terraform_tools_only_for_terraform_stack(render, tmp_path):
    plain = render(tmp_path / "plain", project_name="demo")
    tf = render(tmp_path / "tf", project_name="demo", stack=["terraform"])

    plain_tools = tomllib.loads((plain / ".mise/conf.d/standard.toml").read_text())["tools"]
    tf_tools = tomllib.loads((tf / ".mise/conf.d/standard.toml").read_text())["tools"]
    assert "terraform" not in plain_tools and "tflint" not in plain_tools
    assert {"terraform", "tflint"} <= set(tf_tools)
    assert not (plain / ".mise/tasks/tf-validate").exists()
    assert (tf / ".mise/tasks/tf-validate").exists()
    assert "tflint" not in (plain / "hk.pkl").read_text()


def test_hk_package_matches_hk_tool():
    hk = re.search(r'^hk = "([\d.]+)"$', STANDARD.read_text(), re.M).group(1)
    packages = re.findall(r"releases/download/v([\d.]+)/hk@([\d.]+)#", HK_PKL.read_text())

    assert packages and all(a == b == hk for a, b in packages), packages


TYPESCRIPT_FILES = [
    "eslint.config.mjs", "eslint.project.mjs", ".dependency-cruiser.standard.cjs", ".dependency-cruiser.cjs",
    "knip.json", ".jscpd.json",
]


def test_typescript_files_only_for_typescript_stack(render, tmp_path):
    plain = render(tmp_path / "plain", project_name="demo")
    ts = render(tmp_path / "ts", project_name="demo", stack=["typescript"])

    for name in TYPESCRIPT_FILES:
        assert (ts / name).is_file(), name
        assert not (plain / name).exists(), name
    assert json.loads((ts / ".mise/data/size-limits.json").read_text()) == {
        ".cts": 300, ".mts": 300, ".ts": 300, ".tsx": 300}
    assert json.loads((plain / ".mise/data/size-limits.json").read_text()) == {}
    tools = tomllib.loads((ts / ".mise/conf.d/standard.toml").read_text())["tools"]
    assert tools["npm:jscpd"] == "5.4.2" and "node" in tools
    assert "npm:jscpd" not in tomllib.loads((plain / ".mise/conf.d/standard.toml").read_text())["tools"]
    assert "eslint" not in (plain / "hk.pkl").read_text()
    assert "node_modules/" in (ts / ".gitignore").read_text().splitlines()


def test_typescript_hooks_split_fast_and_typed_lint(render, tmp_path):
    hk = (render(tmp_path, project_name="demo", stack=["typescript"]) / "hk.pkl").read_text()

    assert '["eslint-fast"]' in hk and '["ESLINT_NO_TYPES"] = "1"' in hk
    pre_commit = hk.split('["pre-commit"]', 1)[1].split('["commit-msg"]', 1)[0]
    check = hk.split('  ["check"]', 1)[1]
    assert "...fastLint" in pre_commit and "...fastLint" not in check
    for step in ('["typecheck"]', '["eslint"]', '["test"]', '["dependency-cruiser"]', '["knip"]'):
        assert step in hk.split("local pushSteps", 1)[1], step


def test_steiger_step_per_fsd_part(render, tmp_path):
    fsd = render(tmp_path / "fsd", project_name="demo", stack=["typescript"],
                 architecture={"apps/web/src": "FSD", "apps/server": "layers"})
    plain = render(tmp_path / "plain", project_name="demo", stack=["typescript"])

    hk = (fsd / "hk.pkl").read_text()
    assert '["steiger-1"]' in hk and 'List(bin("steiger"), "apps/web/src")' in hk
    assert "apps/server" not in hk
    assert "steiger" in json.loads((fsd / "knip.json").read_text())["ignoreDependencies"]
    assert "steiger" not in (plain / "hk.pkl").read_text()
    assert "steiger" not in json.loads((plain / "knip.json").read_text())["ignoreDependencies"]


def test_project_files_of_typescript_are_written_once(render, tmp_path):
    copier = yaml.safe_load((REPO_ROOT / "copier.yml").read_text())

    for name in ("eslint.project.mjs", ".dependency-cruiser.cjs", "knip.json", ".jscpd.json"):
        assert name in copier["_skip_if_exists"], name
    for name in ("eslint.config.mjs", ".dependency-cruiser.standard.cjs"):
        assert name not in copier["_skip_if_exists"], name
