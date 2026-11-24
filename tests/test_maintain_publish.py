"""`publish` of `mise run maintain`: boundaries, baselines, results and failures."""

import json
import os
import shutil
import subprocess

import pytest

JOB = "docs-drift"
DOC = "docs/architecture.md"


def out(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def commits(w) -> int:
    return int(w.git("rev-list", "--count", "origin/main..HEAD").strip())


def no_code_ran(w) -> bool:
    return "mise run check" not in w.log and "check-size" not in w.log


def rejected(w, result, *names: str) -> None:
    assert result.returncode == 1, out(result)
    for name in names:
        assert name in out(result), out(result)
    assert no_code_ran(w), w.log
    assert commits(w) == 0 and "gh pr create" not in w.log
    assert w.remote_git("for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]


def publish(w, job: str = JOB, *flags: str):
    return w.maintain("publish", job, *flags)


def edit_doc(w, rel: str = DOC) -> None:
    path = w.root / rel
    path.write_text(path.read_text() + "\nOne more fact.\n")


@pytest.fixture
def started(world):
    w = world()
    w.start()
    return w


def test_publish_rejects_path_outside_job(started):
    started.write("src/app.py", "x = 1\n")
    edit_doc(started)

    rejected(started, publish(started), "src/app.py")


def test_publish_rejects_protected_file(world):
    w = world()
    w.start("dead-code")
    w.write(".config/hk.pkl", "// edited\n")

    result = publish(w, "dead-code")

    rejected(w, result, ".config/hk.pkl")


def test_publish_rejects_renamed_and_deleted_foreign_file(world):
    w = world()
    w.write("src/a.py", "a = 1\n")
    w.write("src/b.py", "b = 1\n")
    w.commit_base("feat: add sources")
    w.start()
    w.git("mv", "src/a.py", "src/c.py")
    (w.root / "src/b.py").unlink()

    result = publish(w)

    rejected(w, result, "src/a.py", "src/b.py", "src/c.py")


def test_publish_rejects_index_only_change(started):
    started.write("src/staged.py", "x = 1\n")
    started.git("add", "src/staged.py")
    (started.root / "src/staged.py").unlink()

    rejected(started, publish(started), "src/staged.py")


@pytest.mark.parametrize("name", [".mise/config.toml", "mise.local.toml", "hk.local.pkl", ".mise.toml"])
def test_publish_rejects_tool_override(started, name):
    started.write(name, "[tasks.check]\nrun = 'true'\n")

    rejected(started, publish(started), name)


def test_publish_rejects_ignored_tool_override(started):
    started.write(".git/info/exclude", "mise.local.toml\n")
    started.write("mise.local.toml", "[tasks.check]\nrun = 'true'\n")

    result = publish(started)

    rejected(started, result, "mise.local.toml")


def test_publish_rejects_new_root_entry(started):
    started.write("newroot.md", "# New\n")

    rejected(started, publish(started), "newroot.md")


def test_publish_reads_protection_from_base(started):
    settings = started.root / ".claude/settings.json"
    config = json.loads(settings.read_text())
    config["permissions"]["ask"].remove("Edit(/.config/**)")
    settings.write_text(json.dumps(config))
    started.write(".config/typos.toml", "# changed\n")
    manifest = started.root / ".maintain/jobs.yaml"
    manifest.write_text(manifest.read_text().replace('paths: ["**/*.md"]', 'paths: ["**"]', 1))

    result = publish(started)

    rejected(started, result, ".config/typos.toml", ".claude/settings.json", ".maintain/jobs.yaml")


def test_publish_reads_ask_rules_from_base(world):
    w = world(stack=["typescript"])
    w.start("dead-code")
    settings = w.root / ".claude/settings.json"
    config = json.loads(settings.read_text())
    config["permissions"]["ask"].remove("Edit(/**/package.json)")
    settings.write_text(json.dumps(config))
    w.write("docs/package.json", "{}\n")

    rejected(w, publish(w, "dead-code"), "docs/package.json: protected file", ".claude/settings.json")


def test_publish_reads_manifest_from_base(started):
    manifest = started.root / ".maintain/jobs.yaml"
    manifest.write_text(manifest.read_text().replace('paths: ["**/*.md"]', 'paths: ["**"]', 1))
    started.write("docs/data.txt", "x\n")

    rejected(started, publish(started), "docs/data.txt: outside the paths of the job", ".maintain/jobs.yaml")


def test_publish_from_clean_checkout_ignores_edited_task(started):
    started.write(".mise/tasks/maintain", "#!/bin/sh\nexit 0\n")
    edit_doc(started)
    clean = started.root.parent / "base-checkout"
    subprocess.run(["git", "clone", "-q", str(started.remote), str(clean)], check=True, capture_output=True)

    result = subprocess.run([str(clean / ".mise/tasks/maintain"), "publish", JOB, "--local"], cwd=started.root,
                            capture_output=True, text=True)

    rejected(started, result, ".mise/tasks/maintain")


def test_publish_accepts_non_latin_file_name(started):
    started.write("docs/заметки.md", "# Заметки\n")
    edit_doc(started)

    result = publish(started, JOB, "--local")

    assert result.returncode == 0, out(result)
    names = started.git("-c", "core.quotepath=off", "show", "--name-only", "--format=", "HEAD").split("\n")
    assert "docs/заметки.md" in names and DOC in names


def test_publish_commits_deleted_document(world):
    w = world()
    w.write("docs/runbooks/old.md", "# Old\n")
    w.commit_base("docs: add runbook")
    w.start()
    (w.root / "docs/runbooks/old.md").unlink()
    edit_doc(w)

    result = publish(w, JOB, "--local")

    assert result.returncode == 0, out(result)
    assert set(w.git("show", "--name-only", "--format=", "HEAD").split()) == {"docs/runbooks/old.md", DOC}
    assert not (w.root / "docs/runbooks/old.md").exists()


def test_docs_drift_rejects_generated_openspec_and_md_exceptions(world):
    w = world()
    w.write(".repo.yaml", w.root.joinpath(".repo.yaml").read_text() + "md_exceptions_note: x\n")
    answers = (w.root / ".repo.yaml").read_text().replace("md_exceptions: []", "md_exceptions:\n- docs/kept.md")
    (w.root / ".repo.yaml").write_text(answers.replace("md_exceptions_note: x\n", ""))
    w.write("docs/generated.md", "<!-- Do NOT edit: generated by tool -->\n\n# Table\n")
    w.write("docs/kept.md", "# Kept\n")
    w.write("openspec/spec.md", "# Spec\n")
    w.commit_base("docs: add documents")
    w.start()
    for name in ("docs/generated.md", "docs/kept.md", "openspec/spec.md"):
        w.write(name, w.root.joinpath(name).read_text() + "\nEdited.\n")

    rejected(w, publish(w), "docs/generated.md", "docs/kept.md", "openspec/spec.md")


def test_docs_drift_matches_question_mark_in_md_exceptions(world):
    w = world()
    answers = (w.root / ".repo.yaml").read_text().replace("md_exceptions: []", "md_exceptions:\n- docs/spec-?.md")
    w.write(".repo.yaml", answers)
    w.write("docs/spec-a.md", "# Spec\n")
    w.commit_base("docs: add spec")
    w.start()
    edit_doc(w, "docs/spec-a.md")

    rejected(w, publish(w), "docs/spec-a.md")


@pytest.mark.parametrize("name", [".vscode/settings.json", "packages/a/.storybook/main.ts"])
def test_publish_rejects_files_in_hidden_folders(world, name):
    w = world()
    w.write(name, "// base\n")
    w.commit_base("chore: add editor files")
    w.start("dead-code")
    w.write(name, "// edited\n")

    rejected(w, publish(w, "dead-code"), name)


def test_publish_rejects_agent_commits(started):
    started.write(DOC, started.root.joinpath(DOC).read_text() + "\nEdited.\n")
    started.git("commit", "-aq", "-m", "docs: align documents with the code")

    result = publish(started)

    assert result.returncode == 1 and "agent commits" in out(result)
    assert "docs: align documents with the code" in out(result) and no_code_ran(started)
    assert started.remote_git("for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]


def size_world(world):
    w = world()
    w.real_size()
    w.write(".mise/data/size-limits.json", '{".py": 3}')
    w.write("src/big.py", "".join(f"x{i} = {i}\n" for i in range(8)))
    w.write(".baselines/size.json", json.dumps({"src/big.py": {"lines": 8, "until": "2099-01-31"}}))
    w.commit_base("feat: add big file")
    w.start("dead-code")
    return w


def shrink(w, lines: int = 5) -> None:
    w.write("src/big.py", "".join(f"x{i} = {i}\n" for i in range(lines)))


def committed_size(w) -> dict:
    return json.loads(w.git("show", "HEAD:.baselines/size.json"))


def test_publish_shrinks_size_baseline_for_dead_code(world):
    w = size_world(world)
    shrink(w)

    result = publish(w, "dead-code", "--local")

    assert result.returncode == 0, out(result)
    assert committed_size(w)["src/big.py"]["lines"] == 5
    assert set(w.git("show", "--name-only", "--format=", "HEAD").split()) == {"src/big.py", ".baselines/size.json"}


def test_publish_shrinks_size_baseline_with_ci_set(world, monkeypatch):
    w = size_world(world)
    shrink(w)
    monkeypatch.setenv("CI", "1")

    result = publish(w, "dead-code", "--local")

    assert result.returncode == 0, out(result)
    assert committed_size(w)["src/big.py"]["lines"] == 5


def test_publish_removes_size_entry_of_file_under_limit(world):
    w = size_world(world)
    shrink(w, 2)

    assert publish(w, "dead-code", "--local").returncode == 0
    assert committed_size(w) == {}


def test_publish_rejects_baseline_edit_by_dead_code(world):
    w = world()
    w.write(".baselines/betterleaks.ignore", "abc:1\n")
    w.commit_base("chore: add ignore")
    w.start("dead-code")
    w.write(".baselines/betterleaks.ignore", "")

    rejected(w, publish(w, "dead-code"), ".baselines/betterleaks.ignore")


def test_publish_accepts_baseline_shrunk_by_agent_check(world):
    w = size_world(world)
    shrink(w)
    w.write(".baselines/size.json", json.dumps({"src/big.py": {"lines": 5, "until": "2099-01-31"}}))

    result = publish(w, "dead-code", "--local")

    assert result.returncode == 0, out(result)
    assert committed_size(w)["src/big.py"]["lines"] == 5


def test_publish_accepts_baseline_shrunk_by_failed_publish(world):
    w = size_world(world)
    shrink(w)
    (w.stub / "mise-fail").write_text("")
    first = publish(w, "dead-code", "--local")
    (w.stub / "mise-fail").unlink()
    w.write("src/small.py", "y = 1\n")

    second = publish(w, "dead-code", "--local")

    assert first.returncode == 1 and "check failed" in out(first)
    assert second.returncode == 0, out(second)
    assert commits(w) == 1 and committed_size(w)["src/big.py"]["lines"] == 5


def test_publish_keeps_text_of_unchanged_eslint_suppressions(world):
    w = world(stack=["typescript"])
    w.write(".baselines/eslint-suppressions.json", "{}")
    w.commit_base("chore: empty suppressions")
    eslint = w.root / "node_modules/.bin/eslint"
    eslint.parent.mkdir(parents=True)
    eslint.write_text("#!/bin/sh\necho eslint >> \"$STUB_LOG\"\n"
                     "printf '{\\n  \"a.ts\": {\"x\": {\"count\": 1}}\\n}' > .baselines/eslint-suppressions.json\n")
    eslint.chmod(0o755)
    w.start("dead-code")
    w.write("docs/a.ts", "export const a = 1;\n")

    result = publish(w, "dead-code", "--local")

    assert result.returncode == 0, out(result)
    assert "eslint" not in w.log
    assert (w.root / ".baselines/eslint-suppressions.json").read_text() == "{}"
    assert w.git("show", "--name-only", "--format=", "HEAD").split() == ["docs/a.ts"]


def test_publish_prunes_eslint_suppressions_and_keeps_text_when_json_is_equal(world):
    w = world(stack=["typescript"])
    text = '{"a.ts": {"x": {"count": 1}}}\n'
    w.write(".baselines/eslint-suppressions.json", text)
    w.commit_base("chore: add suppressions")
    eslint = w.root / "node_modules/.bin/eslint"
    eslint.parent.mkdir(parents=True)
    eslint.write_text("#!/bin/sh\necho eslint >> \"$STUB_LOG\"\n"
                     "printf '{\"a.ts\":{\"x\":{\"count\":1}}}' > .baselines/eslint-suppressions.json\n")
    eslint.chmod(0o755)
    w.start("dead-code")
    w.write("docs/a.ts", "export const a = 1;\n")

    result = publish(w, "dead-code", "--local")

    assert result.returncode == 0 and "eslint" in w.log, out(result)
    assert (w.root / ".baselines/eslint-suppressions.json").read_text() == text
    assert ".baselines/eslint-suppressions.json" not in w.git("show", "--name-only", "--format=", "HEAD").split()


def test_publish_rejects_baseline_growth(world):
    w = size_world(world)
    w.write(".baselines/size.json", json.dumps({"src/big.py": {"lines": 9, "until": "2099-01-31"}}))

    rejected(w, publish(w, "dead-code"), ".baselines/size.json")


def test_publish_rejects_burndown_adding_an_entry(world):
    w = world()
    w.write(".baselines/comments.json", json.dumps({"a.py": {"count": 1, "until": "2099-01-31"}}))
    w.commit_base("chore: add baseline")
    w.start("baseline-burndown")
    w.write(".baselines/comments.json", json.dumps({"a.py": {"count": 1, "until": "2099-01-31"},
                                                     "b.py": {"count": 1, "until": "2099-01-31"}}))

    rejected(w, publish(w, "baseline-burndown"), ".baselines/comments.json")


def test_publish_rejects_replaced_betterleaks_fingerprint(world):
    w = world()
    w.write(".baselines/betterleaks.ignore", "aaa:1\nbbb:2\n")
    w.commit_base("chore: add ignore")
    w.start("baseline-burndown")
    w.write(".baselines/betterleaks.ignore", "aaa:1\nccc:3\n")

    rejected(w, publish(w, "baseline-burndown"), ".baselines/betterleaks.ignore")


def test_publish_rejects_replaced_size_entry(world):
    w = size_world(world)
    w.write(".baselines/size.json", json.dumps({"src/other.py": {"lines": 4, "until": "2099-01-31"}}))

    rejected(w, publish(w, "dead-code"), ".baselines/size.json")


def test_publish_rejects_replaced_eslint_suppression(world):
    w = world(stack=["typescript"])
    w.write(".baselines/eslint-suppressions.json", '{"a.ts": {"x": {"count": 2}}}\n')
    w.commit_base("chore: add suppressions")
    w.start("dead-code")
    w.write(".baselines/eslint-suppressions.json", '{"a.ts": {"y": {"count": 1}}}\n')

    rejected(w, publish(w, "dead-code"), ".baselines/eslint-suppressions.json")


def test_publish_rejects_later_until(world):
    w = world()
    w.write(".baselines/adr.json", json.dumps({"docs/decisions/0001-a.md": {"count": 1, "until": "2027-01-31"}}))
    w.commit_base("chore: add adr baseline")
    w.start("baseline-burndown")
    w.write(".baselines/adr.json", json.dumps({"docs/decisions/0001-a.md": {"count": 1, "until": "2027-06-30"}}))

    rejected(w, publish(w, "baseline-burndown"), ".baselines/adr.json")


def test_publish_accepts_removed_entries_by_burndown(world):
    w = world()
    w.write(".baselines/betterleaks.ignore", "aaa:1\nbbb:2\n")
    w.write(".baselines/comments.json", json.dumps({"a.py": {"count": 2, "until": "2099-01-31"}}))
    w.commit_base("chore: add baselines")
    w.start("baseline-burndown")
    w.write(".baselines/betterleaks.ignore", "aaa:1\n")
    w.write(".baselines/comments.json", json.dumps({"a.py": {"count": 1, "until": "2099-01-31"}}))

    result = publish(w, "baseline-burndown", "--local")

    assert result.returncode == 0, out(result)
    assert "check-baseline" not in w.log and "mise run check" in w.log


def test_publish_without_changes_opens_no_pr(started):
    result = publish(started)

    assert result.returncode == 0 and "no changes" in out(result)
    assert no_code_ran(started) and "gh pr create" not in started.log and commits(started) == 0


def test_publish_failed_check_makes_no_commit(started):
    edit_doc(started)
    (started.stub / "mise-fail").write_text("")

    result = publish(started)

    assert result.returncode == 1 and "check failed" in out(result)
    assert commits(started) == 0 and "One more fact." in (started.root / DOC).read_text()
    assert started.remote_git("for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]
    assert "gh pr create" not in started.log


def test_publish_ignores_origin_moved_after_start(started):
    edit_doc(started)
    other = started.root.parent / "other"
    subprocess.run(["git", "clone", "-q", str(started.remote), str(other)], check=True, capture_output=True)
    (other / "NOTES.txt").write_text("x\n")
    for args in (("add", "-A"), ("-c", "user.name=T", "-c", "user.email=t@e.c", "commit", "-qm", "chore: other"),
                 ("push", "-q", "origin", "main")):
        subprocess.run(["git", "-C", str(other), *args], check=True, capture_output=True)

    result = publish(started, JOB, "--local")

    assert result.returncode == 0, out(result)
    assert commits(started) == 1


def test_publish_compares_baselines_with_the_merge_base(world):
    w = size_world(world)
    shrink(w)
    other = w.root.parent / "other"
    subprocess.run(["git", "clone", "-q", str(w.remote), str(other)], check=True, capture_output=True)
    (other / ".baselines/size.json").write_text("{}\n")
    for args in (("-c", "user.name=T", "-c", "user.email=t@e.c", "commit", "-qam", "chore: drop entries"),
                 ("push", "-q", "origin", "main")):
        subprocess.run(["git", "-C", str(other), *args], check=True, capture_output=True)

    result = publish(w, "dead-code", "--local")

    assert result.returncode == 0, out(result)
    assert committed_size(w)["src/big.py"]["lines"] == 5


def test_publish_runs_check_baseline_with_the_merge_base(world):
    w = world()
    w.write(".mise/tasks/check-baseline", '#!/bin/sh\necho "check-baseline $*" >> "$STUB_LOG"\nexit 1\n')
    w.commit_base("chore: stub the baseline check")
    w.start()
    edit_doc(w)

    result = publish(w)

    assert result.returncode == 1 and commits(w) == 0
    assert f"check-baseline {w.git('rev-parse', 'origin/main').strip()}" in w.log
    assert "gh pr create" not in w.log


def test_publish_rejects_files_changed_during_the_check(started):
    edit_doc(started)
    (started.stub / "mise-edit").write_text("echo '# Stray' > docs/stray.md\n")

    result = publish(started)

    assert result.returncode == 1 and "docs/stray.md" in out(result)
    assert "mise run check" in started.log
    assert commits(started) == 0 and "gh pr create" not in started.log


def test_publish_rejects_files_a_hook_adds_to_the_commit(started):
    edit_doc(started)
    hook = started.root / ".git/hooks/pre-commit"
    hook.write_text("#!/bin/sh\necho '# Stray' > docs/stray.md\ngit add docs/stray.md\n")
    hook.chmod(0o755)

    result = publish(started)

    assert result.returncode == 1 and "docs/stray.md" in out(result)
    assert commits(started) == 0 and "gh pr create" not in started.log
    assert started.remote_git("for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]
    assert "One more fact." in (started.root / DOC).read_text()


def test_publish_keeps_remote_branch_that_appears_before_the_push(started):
    edit_doc(started)
    foreign = started.remote_git("commit-tree", "-m", "chore: foreign", "main^{tree}").strip()
    shim = started.stub / "bin/git"
    real = shutil.which("git")
    shim.write_text(f'#!/bin/sh\nif [ "$1" = push ]; then\n  "{real}" -C "{started.remote}" update-ref '
                    f'refs/heads/maintain/docs-drift {foreign}\nfi\nexec "{real}" "$@"\n')
    shim.chmod(0o755)

    result = publish(started)

    assert result.returncode == 1, out(result)
    assert started.remote_git("rev-parse", "maintain/docs-drift").strip() == foreign
    assert "gh pr create" not in started.log


def test_publish_resumes_after_failed_pr_create(started):
    edit_doc(started)
    started.prs(create_fail=True)

    first = publish(started)
    head = started.git("rev-parse", "HEAD").strip()
    started.prs()
    second = publish(started)

    assert first.returncode == 1 and second.returncode == 0, out(second)
    assert "mise run maintain -- publish docs-drift" in out(first)
    assert started.git("rev-parse", "HEAD").strip() == head
    assert started.log.count("gh pr create") == 2
    assert len(json.loads((started.stub / "gh.json").read_text())["prs"]) == 1
    assert started.remote_git("rev-parse", "maintain/docs-drift").strip() == head


@pytest.mark.parametrize("state", ["MERGED", "CLOSED"])
def test_publish_after_merged_pr_opens_no_second_pr(started, state):
    edit_doc(started)
    assert publish(started).returncode == 0
    head = started.git("rev-parse", "HEAD").strip()
    started.prs({"number": 5, "state": state, "headRefOid": head, "isCrossRepository": False})
    before = started.remote_git("for-each-ref", "--format=%(refname) %(objectname)")
    created = started.log.count("gh pr create")

    result = publish(started)

    assert result.returncode == 0, out(result)
    assert "#5" in out(result) and "mise run maintain -- start docs-drift" in out(result)
    assert started.git("rev-parse", "HEAD").strip() == head
    assert started.remote_git("for-each-ref", "--format=%(refname) %(objectname)") == before
    assert started.log.count("gh pr create") == created
    (started.stub / "log.txt").write_text("")
    local = publish(started, JOB, "--local")
    assert local.returncode == 0 and "gh " not in started.log


def test_publish_resumes_after_failed_pre_push(started):
    edit_doc(started)
    hook = started.root / ".git/hooks/pre-push"
    hook.write_text("#!/bin/sh\necho push blocked >&2\nexit 1\n")
    hook.chmod(0o755)

    first = publish(started)
    head = started.git("rev-parse", "HEAD").strip()
    hook.unlink()
    second = publish(started)

    assert first.returncode == 1 and commits(started) == 1
    assert "mise run maintain -- publish docs-drift" in out(first)
    assert started.log.count("gh pr create") == 1 and second.returncode == 0, out(second)
    assert started.git("rev-parse", "HEAD").strip() == head


def test_publish_refuses_dirty_tree_after_own_commit(started):
    edit_doc(started)
    assert publish(started, JOB, "--local").returncode == 0
    head = started.git("rev-parse", "HEAD").strip()
    edit_doc(started, "README.md")

    result = publish(started)

    assert result.returncode == 1 and "uncommitted changes on top of the published commit" in out(result)
    assert "README.md" in out(result) and "git reset --soft HEAD^" in out(result)
    assert "agent commits" not in out(result)
    assert started.git("rev-parse", "HEAD").strip() == head
    assert "One more fact." in (started.root / "README.md").read_text()
    started.git("reset", "-q", "--soft", "HEAD^")
    again = publish(started, JOB, "--local")
    assert again.returncode == 0, out(again)
    assert set(started.git("show", "--name-only", "--format=", "HEAD").split()) == {DOC, "README.md"}


def test_publish_failed_commit_hook_makes_no_commit(started):
    edit_doc(started)
    hook = started.root / ".git/hooks/pre-commit"
    hook.write_text("#!/bin/sh\necho hook says no >&2\nexit 1\n")
    hook.chmod(0o755)

    result = publish(started)

    assert result.returncode == 1 and "hook says no" in out(result)
    assert commits(started) == 0 and "gh pr create" not in started.log
    assert started.remote_git("for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]
    assert "One more fact." in (started.root / DOC).read_text()


def test_publish_pushes_only_maintain_branch(started):
    edit_doc(started)
    before = started.remote_git("rev-parse", "main").strip()

    result = publish(started)

    assert result.returncode == 0, out(result)
    refs = started.remote_git("for-each-ref", "--format=%(refname)").split()
    assert sorted(refs) == ["refs/heads/main", "refs/heads/maintain/docs-drift"]
    assert started.remote_git("rev-parse", "main").strip() == before
    assert "gh pr create --base main --head maintain/docs-drift" in started.log


def test_publish_local_calls_no_gh_and_no_push(started):
    edit_doc(started)

    result = publish(started, JOB, "--local")

    assert result.returncode == 0 and "mise run maintain -- publish docs-drift" in out(result)
    assert commits(started) == 1 and "gh " not in started.log
    assert started.remote_git("for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]


def test_publish_drops_hook_variables(started, monkeypatch):
    edit_doc(started)
    hook = started.root / ".git/hooks/pre-commit"
    seen = started.root.parent / "hook-env.txt"
    hook.write_text(f"#!/bin/sh\nenv | grep -E '^(HK|HK_SKIP_STEPS|GIT_LITERAL_PATHSPECS)=' > {seen} || true\n")
    hook.chmod(0o755)
    for key in ("HK", "HK_SKIP_STEPS", "GIT_LITERAL_PATHSPECS"):
        monkeypatch.setenv(key, "1")

    result = publish(started, JOB, "--local")

    assert result.returncode == 0, out(result)
    assert seen.read_text() == ""


def test_pr_body_passes_check_pr_body(started):
    edit_doc(started)
    assert publish(started).returncode == 0
    body = (started.stub / "body.txt").read_text()

    checked = subprocess.run([str(started.root / ".mise/tasks/check-pr-body")], env={**os.environ, "PR_BODY": body},
                             capture_output=True, text=True)

    assert checked.returncode == 0, out(checked)
    assert len(body.splitlines()) <= 20
    for heading in ("## What", "## Why", "## How verified"):
        assert heading in body


def eslint_stub(w, body: str) -> None:
    eslint = w.root / "node_modules/.bin/eslint"
    eslint.parent.mkdir(parents=True, exist_ok=True)
    eslint.write_text(f"#!/bin/sh\n{body}\n")
    eslint.chmod(0o755)


def test_publish_restores_base_text_of_empty_eslint_suppressions(world):
    w = world(stack=["typescript"])
    assert (w.root / ".baselines/eslint-suppressions.json").read_text().strip() == "{}"
    w.start("dead-code")
    (w.root / ".baselines/eslint-suppressions.json").write_text("{}")
    w.write("docs/a.ts", "export const a = 1;\n")

    result = publish(w, "dead-code", "--local")

    assert result.returncode == 0, out(result)
    assert w.git("show", "--name-only", "--format=", "HEAD").split() == ["docs/a.ts"]


def test_publish_without_other_changes_after_empty_eslint_rewrite_has_no_changes(world):
    w = world(stack=["typescript"])
    w.start("dead-code")
    (w.root / ".baselines/eslint-suppressions.json").write_text("{}")

    result = publish(w, "dead-code")

    assert result.returncode == 0 and "no changes" in out(result)
    assert commits(w) == 0 and "gh pr create" not in w.log


def test_publish_checks_paths_after_cleaning_before_check(world):
    w = world(stack=["typescript"])
    w.write(".baselines/eslint-suppressions.json", '{"a.ts": {"x": {"count": 1}}}\n')
    w.commit_base("chore: add suppressions")
    eslint_stub(w, "printf '[tasks.check]\\nrun = \"true\"\\n' > .mise/config.toml")
    w.start("dead-code")
    w.write("docs/a.ts", "export const a = 1;\n")

    result = publish(w, "dead-code")

    assert result.returncode == 1 and ".mise/config.toml" in out(result)
    assert "mise run check" not in w.log and commits(w) == 0


def test_publish_rejects_size_entry_moved_by_rename_before_check(world):
    w = size_world(world)
    w.git("mv", "src/big.py", "src/moved.py")

    result = publish(w, "dead-code")

    assert result.returncode == 1 and ".baselines/size.json" in out(result)
    assert "mise run check" not in w.log and commits(w) == 0


def test_publish_passes_git_listed_files_to_eslint(world):
    w = world(stack=["typescript"])
    w.write(".baselines/eslint-suppressions.json", '{"docs/a.ts": {"x": {"count": 1}}}\n')
    w.write("docs/a.ts", "export const a = 1;\n")
    w.commit_base("chore: add suppressions")
    eslint_stub(w, 'echo "eslint $*" >> "$STUB_LOG"')
    w.start("dead-code")
    w.write(".claude/worktrees/w/docs/copy.ts", "export const b = 1;\n")
    w.write(".git/info/exclude", "docs/ignored.ts\n")
    w.write("docs/ignored.ts", "export const c = 1;\n")
    w.write("docs/new.ts", "export const d = 1;\n")

    result = publish(w, "dead-code", "--local")

    line = next(item for item in w.log.splitlines() if item.startswith("eslint "))
    assert "--no-warn-ignored" in line and "docs/a.ts" in line and "docs/new.ts" in line, out(result)
    assert "copy.ts" not in line and "ignored.ts" not in line


def test_publish_ignores_ds_store_in_config_folders(started):
    started.write(".config/.DS_Store", "x")
    started.write(".git/info/exclude", ".DS_Store\n")
    edit_doc(started)

    assert publish(started, JOB, "--local").returncode == 0


def test_publish_rejects_baseline_record_without_a_field(world):
    w = world()
    w.write(".baselines/comments.json", json.dumps({"a.py": {"count": 2, "until": "2099-01-31"}}))
    w.commit_base("chore: add baseline")
    w.start("baseline-burndown")
    w.write(".baselines/comments.json", json.dumps({"a.py": {"until": "2099-01-31"}}))

    rejected(w, publish(w, "baseline-burndown"), ".baselines/comments.json")


def test_publish_refuses_foreign_remote_branch(started):
    started.git("checkout", "-q", "-b", "other", "origin/main")
    started.write("NOTES.txt", "x\n")
    started.git("add", "-A")
    started.git("commit", "-qm", "chore: foreign")
    started.git("push", "-q", "origin", "other:maintain/docs-drift")
    started.git("checkout", "-q", "maintain/docs-drift")
    foreign = started.remote_git("rev-parse", "maintain/docs-drift").strip()
    edit_doc(started)

    result = publish(started)

    assert result.returncode == 1 and "git push origin --delete maintain/docs-drift" in out(result)
    assert started.remote_git("rev-parse", "maintain/docs-drift").strip() == foreign
    assert "gh pr create" not in started.log


def test_publish_refuses_open_pull_request_before_commit(started):
    edit_doc(started)
    started.prs({"number": 9, "state": "OPEN", "headRefOid": "b" * 40, "isCrossRepository": False})

    result = publish(started)

    assert result.returncode == 1 and "#9" in out(result)
    assert commits(started) == 0 and "mise run check" not in started.log
