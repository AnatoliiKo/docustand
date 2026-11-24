# Adapter manual

This folder holds the local adapter: `run` starts a job with an agent command you choose.

## Run

```sh
.maintain/manual/run docs-drift --local -- claude -p --permission-mode acceptEdits
```

`run <job> [--local] [-- <command>]` prepares the branch `maintain/<job>`, starts the command with the job instruction on stdin, then checks the changes, commits through the hooks and opens a pull request. Without a command it prints the instruction and the publish command. Without a permission mode the agent does not edit files. `acceptEdits` allows file edits only; a command needs `--allowedTools`, for example `--allowedTools "Bash(mise run check)"`.

`--local` stops after the commit: no `git push`, no `gh`. The next step is printed.

## Baselines

An edit of the baseline folder is declined in such a run. `publish` shrinks `size.json` and `eslint-suppressions.json` itself; the owner removes the entries of `adr.json`, `comments.json` and `betterleaks.ignore`.

## After a failure

- `mise run check` failed: fix the cause and run `publish` again. When `check-size` compares with an entry that is already smaller, run `git restore --source=HEAD --staged --worktree .baselines/size.json` and `publish` again.
- The `pre-push` hook failed: run `publish` again. When the files need an edit, run `git reset --soft HEAD^`, edit, and run `publish`.
- The pull request was squash-merged: run `mise run maintain -- start <job>` for the next run.
