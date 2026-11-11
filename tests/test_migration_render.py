"""Applying the template over an existing repository without losing lines.

Follows the migration order of `repo-init`: render aside, list conflicts,
copy with `--skip` per conflict, merge, and later `copier update`.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, init_git_repo

SCRIPT = REPO_ROOT / "scripts" / "merge_existing.py"
DATA = ["--data", "project_name=demo", "--data", "stack=[terraform]"]

GITIGNORE = "/vendor\n/node_modules\n.env\n/storage/*.key\n.phpunit.result.cache\n"
MISE_TOML = '[tools]\nphp = "8.4"\n\n[tasks.serve]\nrun = "php artisan serve"\n'
CLAUDE_MD = "".join(f"Project rule {n}\n" for n in range(1, 21))
TESTS_YML = "name: tests\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: phpunit\n"
CI_YML = "name: ci\non: [push]\njobs:\n  c:\n    runs-on: ubuntu-latest\n    steps:\n      - run: lint\n"
TFLINT = 'rule "terraform_naming_convention" {\n  enabled = true\n}\n'
RENOVATE = '{\n  "extends": ["config:base"],\n  "labels": ["own"]\n}\n'

OWN_FILES = {
    ".gitignore": GITIGNORE,
    "mise.toml": MISE_TOML,
    "CLAUDE.md": CLAUDE_MD,
    ".github/workflows/tests.yml": TESTS_YML,
    ".github/workflows/ci.yml": CI_YML,
    ".tflint.hcl": TFLINT,
    ".github/renovate.json": RENOVATE,
}


def run(*cmd, cwd=None, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True,
    )


def script(*args, cwd=None) -> subprocess.CompletedProcess:
    return run(sys.executable, SCRIPT, *args, cwd=cwd)


@pytest.fixture
def existing(tmp_path):
    """A non-empty git repository of a Laravel project, committed."""
    project = init_git_repo(tmp_path / "project")
    for rel, text in OWN_FILES.items():
        path = project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    run("git", "add", "-A", cwd=project)
    run("git", "commit", "-m", "chore: laravel project", cwd=project)
    return project


def migrate(tmp_path, project, template=REPO_ROOT, ref="HEAD"):
    """Steps 1-4 of the migration order; returns (rendered, results)."""
    rendered = tmp_path / "rendered"
    step1 = run("copier", "copy", "--defaults", "--vcs-ref", ref, *DATA, template, rendered)
    step2 = script("conflicts", project, rendered)
    conflicts = step2.stdout.split()
    skips = [a for c in conflicts for a in ("--skip", c)]
    step3 = run("copier", "copy", "--defaults", "--vcs-ref", ref, *DATA, *skips, template, project)
    step4 = script("merge", project, rendered)
    return rendered, [step1, step2, step3, step4]


def test_copy_over_existing_is_non_interactive(tmp_path, existing):
    _, steps = migrate(tmp_path, existing)
    for step in steps:
        assert step.returncode == 0, f"{step.args}\n{step.stdout}\n{step.stderr}"


def test_conflicting_standard_files_kept(tmp_path, existing):
    _, (_, step2, _, _) = migrate(tmp_path, existing)
    listed = step2.stdout.split()
    assert (existing / ".tflint.hcl").read_bytes() == TFLINT.encode()
    assert (existing / ".github/renovate.json").read_bytes() == RENOVATE.encode()
    assert ".tflint.hcl" in listed
    assert ".github/renovate.json" in listed
    skip_if_exists = {
        "README.md", "docs/architecture.md", "docs/tasks.md", "docs/access.md",
        "docs/operations.md", ".gitignore", "CLAUDE.md",
    }
    assert not skip_if_exists & set(listed)
    assert listed == sorted(listed)


def test_no_foreign_line_lost(tmp_path, existing):
    migrate(tmp_path, existing)
    for rel in (".gitignore", "CLAUDE.md", ".github/workflows/tests.yml", ".github/workflows/ci.yml"):
        result = (existing / rel).read_text().splitlines()
        for line in OWN_FILES[rel].splitlines():
            assert line in result, f"{rel}: lost {line!r}"
    assert (existing / "mise.toml").read_bytes() == MISE_TOML.encode()


def test_gitignore_block_appended_once(tmp_path, existing):
    rendered, _ = migrate(tmp_path, existing)
    assert script("merge", existing, rendered).returncode == 0
    text = (existing / ".gitignore").read_text()
    assert text.count("# >>> repository standard") == 1
    assert text.count("# <<< repository standard") == 1
    assert text.startswith(GITIGNORE)
    assert "!.claude/hooks/" in text
    assert ".terraform/" in text


def _fresh_render(tmp_path):
    rendered = tmp_path / "rendered"
    result = run("copier", "copy", "--defaults", "--vcs-ref", "HEAD", *DATA, REPO_ROOT, rendered)
    assert result.returncode == 0, result.stderr
    return rendered


def test_no_markers_all_lines_present_is_noop(tmp_path):
    rendered = _fresh_render(tmp_path)
    project = tmp_path / "fresh"
    project.mkdir()
    (project / ".gitignore").write_bytes((rendered / ".gitignore").read_bytes())
    before = (project / ".gitignore").read_bytes()
    for args in ((), ("--audit",), ()):
        assert script("merge", project, rendered, *args).returncode == 0
        assert (project / ".gitignore").read_bytes() == before


def test_no_markers_some_lines_present_appends_only_missing(tmp_path):
    rendered = _fresh_render(tmp_path)
    project = tmp_path / "partial"
    project.mkdir()
    (project / ".gitignore").write_text("/vendor\ndocs/temp/\nCLAUDE.local.md\n")
    for args in ((), ("--audit",), ()):
        assert script("merge", project, rendered, *args).returncode == 0
    lines = (project / ".gitignore").read_text().splitlines()
    assert lines.count("# >>> repository standard") == 1
    block = lines[lines.index("# >>> repository standard") + 1:lines.index("# <<< repository standard")]
    assert "docs/temp/" not in block and "CLAUDE.local.md" not in block
    assert "!.claude/hooks/" in block and ".claude/*" in block
    content = [l for l in lines if l and not l.startswith("# ")]
    assert len(content) == len(set(content))


def test_merge_is_idempotent_and_never_deletes(tmp_path, existing):
    rendered, _ = migrate(tmp_path, existing)
    snapshot = {p: p.read_bytes() for p in existing.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert script("merge", existing, rendered).returncode == 0
    assert script("merge", existing, rendered, "--audit").returncode == 0
    after = {p: p.read_bytes() for p in existing.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert after == snapshot


@pytest.mark.integration
def test_standard_tools_in_conf_d(tmp_path, existing):
    if shutil.which("mise") is None:
        pytest.skip("mise is not installed")
    (existing / "mise.toml").write_text('[tools]\nphp = "8.4"\npython = "3.12"\n')
    migrate(tmp_path, existing)
    assert (existing / ".mise" / "conf.d" / "standard.toml").is_file()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MISE_", "__MISE"))}
    # php is not installed: offline keeps mise from resolving 8.4 over the network.
    env.update(MISE_TRUSTED_CONFIG_PATHS=str(tmp_path), MISE_YES="1",
               MISE_OFFLINE="1")
    listing = run("mise", "ls", "--current", cwd=existing, env=env)
    assert listing.returncode == 0, listing.stderr
    rows = {line.split()[0]: line for line in listing.stdout.splitlines() if line.strip()}
    assert "php" in rows and "mise.toml" in rows["php"]
    assert "hk" in rows and "standard.toml" in rows["hk"]
    assert "python" in rows
    assert "standard.toml" not in rows["python"]
    assert "mise.toml" in rows["python"]


def test_audit_appends_missing_block_lines(tmp_path, existing):
    rendered, _ = migrate(tmp_path, existing)
    path = existing / ".gitignore"
    text = path.read_text()
    assert "!.claude/hooks/\n" in text
    path.write_text(text.replace("!.claude/hooks/\n", ""))
    before = path.read_text().splitlines()
    assert script("merge", existing, rendered, "--audit").returncode == 0
    after = path.read_text().splitlines()
    assert after.count("!.claude/hooks/") == 1
    end = after.index("# <<< repository standard")
    assert after.index("!.claude/hooks/") < end
    after.remove("!.claude/hooks/")
    assert after == before


def test_existing_ci_yml_reported(tmp_path, existing):
    rendered, (_, _, _, step4) = migrate(tmp_path, existing)
    for name in (".github/workflows/ci.yml", ".github/workflows/tests.yml", "mise.toml", "CLAUDE.md"):
        assert name in step4.stdout
    assert "standard-ci.yml" not in step4.stdout
    assert (existing / ".github/workflows/standard-ci.yml").is_file()
    assert (existing / ".github/workflows/ci.yml").read_text() == CI_YML


@pytest.mark.integration
def test_update_reaches_standard_files_only(tmp_path):
    template = tmp_path / "template-repo"
    template.mkdir()
    shutil.copy(REPO_ROOT / "copier.yml", template / "copier.yml")
    shutil.copytree(REPO_ROOT / "template", template / "template")
    init_git_repo(template)
    run("git", "add", "-A", cwd=template)
    run("git", "commit", "-m", "v1", cwd=template)
    run("git", "tag", "v0.0.1", cwd=template)

    ci = template / "template/.github/workflows/standard-ci.yml.jinja"
    ci.write_text(ci.read_text() + "# changed in v0.0.2\n")
    toml = template / "template/.mise/conf.d/standard.toml.jinja"
    toml.write_text(toml.read_text() + "\n# changed in v0.0.2\n")
    run("git", "add", "-A", cwd=template)
    run("git", "commit", "-m", "v2", cwd=template)
    run("git", "tag", "v0.0.2", cwd=template)

    project = init_git_repo(tmp_path / "project")
    for rel, text in OWN_FILES.items():
        path = project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    run("git", "add", "-A", cwd=project)
    run("git", "commit", "-m", "chore: laravel project", cwd=project)

    _, steps = migrate(tmp_path, project, template=template, ref="v0.0.1")
    for step in steps:
        assert step.returncode == 0, f"{step.args}\n{step.stdout}\n{step.stderr}"
    run("git", "add", "-A", cwd=project)
    run("git", "commit", "-m", "chore: apply standard", cwd=project)

    update = run("copier", "update", "-a", ".repo.yaml", "--defaults", "--vcs-ref", "v0.0.2", cwd=project)
    assert update.returncode == 0, f"{update.stdout}\n{update.stderr}"
    assert "# changed in v0.0.2" in (project / ".github/workflows/standard-ci.yml").read_text()
    assert "# changed in v0.0.2" in (project / ".mise/conf.d/standard.toml").read_text()
    assert (project / "mise.toml").read_text() == MISE_TOML
    assert (project / ".github/workflows/ci.yml").read_text() == CI_YML
