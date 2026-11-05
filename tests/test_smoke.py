import subprocess


def test_render_fixture_exists(render, git_repo, tmp_path):
    src = git_repo(tmp_path / "tpl")
    (src / "copier.yml").write_text("_subdirectory: template\n")
    (src / "template").mkdir()
    (src / "template" / ".gitkeep").write_text("")
    for args in (["add", "-A"], ["commit", "-m", "template"]):
        subprocess.run(["git", "-C", str(src), *args], check=True, capture_output=True)

    dest = render(tmp_path, src=src)

    assert dest.is_dir()
