import re
import tomllib

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
