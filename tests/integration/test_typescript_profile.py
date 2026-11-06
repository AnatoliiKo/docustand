"""Integration tests of the `typescript` profile: every check fails on one violation.

Needs mise, network on the first run (npm packages, Node 22 and jscpd through mise)
and about 30 s for `npm ci` once per session. The project pins Node 22 in its own
`mise.toml`, the way `cinema-ops` keeps Node 22 under the Node of the standard.
"""

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from conftest import init_git_repo, run_copier
from test_gates_fail import PRE_COMMIT_BUDGET_S, assert_step_fails, check, failed_steps, mise_env, sh, write

pytestmark = pytest.mark.integration

NODE = "22.23.3"
DEV_DEPENDENCIES = {
    "@feature-sliced/steiger-plugin": "0.8.2",
    "dependency-cruiser": "18.7.2",
    "eslint": "10.14.0",
    "eslint-plugin-sonarjs": "4.2.2",
    "knip": "6.44.1",
    "prettier": "3.9.10",
    "steiger": "0.9.0",
    "typescript": "6.0.3",
    "typescript-eslint": "8.72.1",
}
PACKAGE = {
    "name": "demo",
    "private": True,
    "type": "module",
    "scripts": {"typecheck": "tsc --noEmit", "test": "node --test"},
    "devDependencies": DEV_DEPENDENCIES,
}
TSCONFIG = {
    "compilerOptions": {
        "strict": True,
        "target": "es2023",
        "module": "nodenext",
        "moduleResolution": "nodenext",
        "noEmit": True,
        "skipLibCheck": True,
    },
    "include": ["src", "web"],
}
MAIN = """\
import { label } from "../web/src/shared/ui/index.js";
import { add } from "./math.js";

export function run(): string {
  return `${label} ${add(1, 2)}`;
}
"""
MATH = """\
export function add(a: number, b: number): number {
  return a + b;
}
"""
TEST = """\
import assert from "node:assert/strict";
import test from "node:test";

test("adds", () => {
  assert.equal(1 + 1, 2);
});
"""
STEIGER = """\
import fsd from "@feature-sliced/steiger-plugin";
import { defineConfig } from "steiger";

export default defineConfig([...fsd.configs.recommended]);
"""


def branches(n: int) -> str:
    """A function with complexity n + 1."""
    body = "".join(f"  if (x === {i}) return {i};\n" for i in range(n))
    return f"export function pick(x: number): number {{\n{body}  return -1;\n}}\n"


@pytest.fixture(scope="session")
def ts_base(tmp_path_factory):
    env = mise_env(tmp_path_factory.getbasetemp())
    dest = tmp_path_factory.mktemp("ts") / "project"
    rendered = run_copier(dest, project_name="demo", stack=["typescript"],
                          architecture={"web/src": "fsd"})
    if rendered.returncode != 0:
        pytest.fail(f"copier failed:\n{rendered.stderr}")
    init_git_repo(dest)
    (dest / "mise.toml").write_text(f'[tools]\nnode = "{NODE}"\n')
    write(dest, "package.json", json.dumps(PACKAGE, indent=2) + "\n")
    write(dest, "tsconfig.json", json.dumps(TSCONFIG, indent=2) + "\n")
    write(dest, "src/main.ts", MAIN)
    write(dest, "src/math.ts", MATH)
    write(dest, "src/math.test.mjs", TEST)
    write(dest, "web/src/shared/ui/index.ts", 'export const label = "sum";\n')
    write(dest, "steiger.config.mjs", STEIGER)
    sh(dest, env, "mise", "install", check=True)
    sh(dest, env, "mise", "x", "--", "npm", "install", "--no-audit", "--no-fund", check=True)
    sh(dest, env, "git", "add", "-A", check=True)
    sh(dest, env, "git", "commit", "-m", "chore: add project files", check=True)
    return dest, env


@pytest.fixture
def ts(ts_base, tmp_path):
    src, env = ts_base
    dest = tmp_path / "project"
    shutil.copytree(src, dest, symlinks=True)
    return dest, env


def eslint(project, *args: str, no_types: bool = False) -> subprocess.CompletedProcess:
    root, env = project
    env = {**env, "ESLINT_NO_TYPES": "1"} if no_types else env
    return sh(root, env, "mise", "x", "--", "node_modules/.bin/eslint", "--no-warn-ignored", *args)


def test_clean_typescript_project_passes(ts):
    result = check(ts)

    assert result.returncode == 0, result.stdout + result.stderr
    for step in ("prettier", "eslint", "typecheck", "test", "dependency-cruiser", "knip", "steiger-1",
                 "check-size"):
        assert step in result.stdout + result.stderr, step


def test_project_node_wins_over_standard(ts):
    root, env = ts

    node = sh(root, env, "mise", "which", "node", check=True).stdout.strip()

    assert f"/node/{NODE}/" in node, node


def test_gitignore_keeps_node_modules_out(ts):
    root, env = ts

    assert sh(root, env, "git", "check-ignore", "-q", "node_modules/eslint/package.json").returncode == 0


def test_fails_on_prettier(ts):
    write(ts[0], "src/math.ts", MATH.replace("return a + b;", "return a+b"))

    assert_step_fails(check(ts), "prettier")


def test_template_files_are_not_formatted_by_prettier(ts):
    root = ts[0]
    path = root / "eslint.config.mjs"
    path.write_text(path.read_text() + "\nconst  unused_spacing = 1;\nvoid unused_spacing;\n")

    assert "prettier" not in failed_steps(check(ts))


def test_fails_on_complexity(ts):
    write(ts[0], "src/pick.ts", branches(12))
    write(ts[0], "src/main.ts", MAIN + 'export { pick } from "./pick.js";\n')

    result = check(ts)

    assert_step_fails(result, "eslint")
    assert "complexity" in result.stdout + result.stderr


def test_project_rule_cannot_weaken_complexity(ts):
    root = ts[0]
    write(root, "eslint.project.mjs", 'export default [{ rules: { complexity: ["error", 50] } }];\n')
    write(root, "src/pick.ts", branches(12))

    result = eslint(ts, "src/pick.ts")

    assert result.returncode == 1
    assert "Maximum allowed is 10" in result.stdout


@pytest.mark.parametrize("ignore", [
    '{ ignores: ["src/**"] }',
    '{ name: "skip", ignores: ["src/**"] }',
    '[[{ ignores: ["src/**"] }]]',
])
def test_project_global_ignores_are_dropped(ts, ignore):
    root = ts[0]
    write(root, "eslint.project.mjs", f"export default [{ignore}];\n")
    write(root, "src/pick.ts", branches(12))

    result = eslint(ts, "src/pick.ts")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Maximum allowed is 10" in result.stdout
    assert "global ignores of eslint.project.mjs are dropped" in result.stderr


def test_project_ignores_with_files_still_apply(ts):
    root = ts[0]
    write(root, "eslint.project.mjs", 'export default [{ files: ["src/**"], ignores: ["src/pick.ts"], '
          'rules: { "no-var": "error" } }];\n')
    write(root, "src/pick.ts", "export var x = 1;\n")
    write(root, "src/other.ts", "export var y = 1;\n")

    result = eslint(ts, "src/pick.ts", "src/other.ts")

    assert result.returncode == 1
    assert "other.ts" in result.stdout and "pick.ts" not in result.stdout


def test_stricter_threshold_through_protected_file(ts):
    root = ts[0]
    write(root, "src/pick.ts", branches(6))
    assert eslint(ts, "src/pick.ts").returncode == 0

    path = root / "eslint.config.mjs"
    path.write_text(path.read_text().replace("complexity: ['error', 10]", "complexity: ['error', 5]"))
    result = eslint(ts, "src/pick.ts")

    assert result.returncode == 1
    assert "Maximum allowed is 5" in result.stdout


def test_typed_rules_run_before_push_not_before_commit(ts):
    root = ts[0]
    write(root, "eslint.project.mjs", 'import tseslint from "typescript-eslint";\n\n'
          "export default [...tseslint.configs.recommendedTypeChecked];\n")
    write(root, "src/job.ts", "export async function job(): Promise<void> {}\n\n"
          "export function start(): void {\n  job();\n}\n")

    assert eslint(ts, "src/job.ts", no_types=True).returncode == 0
    result = eslint(ts, "src/job.ts")
    assert result.returncode == 1
    assert "no-floating-promises" in result.stdout


def test_fails_on_type_error(ts):
    write(ts[0], "src/math.ts", MATH.replace("return a + b;", 'return a + "b";'))

    assert_step_fails(check(ts), "typecheck")


def test_fails_on_test(ts):
    write(ts[0], "src/math.test.mjs", TEST.replace("2);", "3);"))

    assert_step_fails(check(ts), "test")


def test_fails_on_cycle(ts):
    root = ts[0]
    write(root, "src/a.ts", 'import { b } from "./b.js";\n\nexport const a = (): number => b() + 1;\n')
    write(root, "src/b.ts", 'import { a } from "./a.js";\n\nexport const b = (): number => (typeof a === "function" ? 1 : 0);\n')
    write(root, "src/main.ts", MAIN + 'export { a } from "./a.js";\n')

    assert_step_fails(check(ts), "dependency-cruiser")


def test_fails_on_unused_file(ts):
    write(ts[0], "src/orphan.ts", "export const orphan = 1;\n")

    assert_step_fails(check(ts), "knip")


def test_fails_on_fsd_violation(ts):
    write(ts[0], "web/src/features/a/index.ts", "export const a = 1;\n")
    write(ts[0], "src/main.ts", MAIN + 'export { a } from "../web/src/features/a/index.js";\n')

    assert_step_fails(check(ts), "steiger-1")


def test_fails_on_large_file(ts):
    body = "".join(f"export const v{i} = {i};\n" for i in range(301))
    write(ts[0], "src/big.ts", body)
    write(ts[0], "src/main.ts", MAIN + 'export * from "./big.js";\n')

    result = check(ts)

    assert_step_fails(result, "check-size")
    assert "src/big.ts:1: 301 non-empty lines, limit 300" in result.stdout + result.stderr


def test_duplication_check_fails_over_threshold(ts):
    root, env = ts
    assert sh(root, env, "mise", "x", "--", "jscpd", "--config", ".jscpd.json", "--no-tips", ".").returncode == 0
    body = "".join(f"  total += values[{i}] * {i + 3} - offset;\n" for i in range(12))
    for name in ("a", "b"):
        write(root, f"src/dup_{name}.ts", f"export function sum_{name}(values: number[], offset: number): number {{\n"
              f"  let total = 0;\n{body}  return total;\n}}\n")

    result = sh(root, env, "mise", "x", "--", "jscpd", "--config", ".jscpd.json", "--no-tips", ".")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "over threshold" in result.stdout + result.stderr


def test_typescript_pre_commit_budget(ts):
    root, env = ts
    write(root, "src/math.ts", MATH + "\nexport const zero = 0;\n")
    sh(root, env, "git", "add", "src/math.ts", check=True)
    sh(root, env, "mise", "x", "--", "hk", "run", "pre-commit", check=True)

    start = time.monotonic()
    result = sh(root, env, "mise", "x", "--", "hk", "run", "pre-commit", check=True)
    elapsed = time.monotonic() - start
    print(f"typescript pre-commit on one changed file: {elapsed:.2f} s")

    assert re.search(r"eslint-fast", result.stdout + result.stderr)
    assert elapsed <= PRE_COMMIT_BUDGET_S, f"pre-commit took {elapsed:.2f} s (budget {PRE_COMMIT_BUDGET_S} s)"


def test_size_baseline_follows_a_rename(ts):
    root, env = ts
    body = "".join(f"export const v{i} = {i};\n" for i in range(320))
    write(root, "src/big.ts", body)
    write(root, "src/main.ts", MAIN + 'export * from "./big.js";\n')
    sh(root, env, "git", "add", "-A", check=True)
    sh(root, env, "mise", "run", "check-size", "--", "--write-baseline", check=True)
    sh(root, env, "git", "commit", "-q", "-m", "chore: record size baseline", check=True)
    (root / "src/moved").mkdir()
    sh(root, env, "git", "mv", "src/big.ts", "src/moved/big.ts", check=True)
    write(root, "src/main.ts", MAIN + 'export * from "./moved/big.js";\n')
    sh(root, env, "git", "add", "-A", check=True)

    sh(root, env, "mise", "x", "--", "hk", "run", "pre-commit", check=True)

    assert json.loads((root / ".size-baseline.json").read_text()) == {"src/moved/big.ts": 320}
    assert ".size-baseline.json" in sh(root, env, "git", "diff", "--cached", "--name-only", check=True).stdout
