#!/usr/bin/env node
// Checks that what project docs point at exists: repo paths in backticks, relative
// Markdown links, ADR numbers, and package-manager / mise commands.
// Usage: node check-doc-refs.mjs [root] [--json] [--all] [--files a.md,b.md]
// History (plans, specs, journals, temp notes) may point at files that no longer exist,
// so it is skipped unless --all is given. Absolute paths are routes or host paths, not repo files.
// Exit 1 when a reference is broken. Ignore list: `.doc-refs-ignore` in root, one token per line.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const args = process.argv.slice(2);
const json = args.includes('--json');
const filesArg = args.includes('--files') ? args[args.indexOf('--files') + 1] : null;
const all = args.includes('--all');
const HISTORY = [/^docs\/temp\//, /^\.planning\//, /^temp\//, /(^|\/)CHANGELOG\.md$/i, /^docs\/archive\//];
const root = path.resolve(args.find((a, i) => !a.startsWith('--') && args[i - 1] !== '--files') ?? '.');

const SKIP_DIRS = new Set(['node_modules', '.git', 'vendor', 'dist', 'build', '.next', 'coverage', '.venv', '.superpowers', '.planning']);
const FILE_EXT = /\.(md|mdx|ts|tsx|js|mjs|cjs|jsx|json|ya?ml|toml|php|py|go|rs|rb|swift|kt|java|sh|ps1|sql|prisma|puml|css|scss|html|env|lock|pkl|tsp|proto|txt|xml|plist)$/i;
const PM_BUILTINS = new Set(['install', 'i', 'add', 'remove', 'rm', 'update', 'up', 'dlx', 'exec', 'x', 'create', 'init', 'why', 'outdated', 'list', 'ls', 'link', 'unlink', 'publish', 'pack', 'store', 'config', 'import', 'rebuild', 'prune', 'audit', 'licenses', 'env', 'setup', 'self-update', 'approve-builds', 'deploy', 'fetch', 'patch', 'patch-commit', 'help', 'root', 'bin', 'ci', 'version', 'start', 'test', 'run', 'recursive', '-r', '-w', '--filter', '-F']);

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (!SKIP_DIRS.has(e.name) && (!e.name.startsWith('.') || e.name === '.github')) walk(path.join(dir, e.name), out);
    } else if (/\.mdx?$/i.test(e.name)) out.push(path.join(dir, e.name));
  }
  return out;
}

const ignore = new Set();
try {
  for (const l of fs.readFileSync(path.join(root, '.doc-refs-ignore'), 'utf8').split('\n')) {
    if (l.trim() && !l.startsWith('#')) ignore.add(l.trim());
  }
} catch {}

const pkgCache = new Map();
function readJson(p) {
  if (!pkgCache.has(p)) {
    try { pkgCache.set(p, JSON.parse(fs.readFileSync(p, 'utf8'))); } catch { pkgCache.set(p, null); }
  }
  return pkgCache.get(p);
}
// All workspace package.json files, keyed by package name and by directory basename.
const packages = new Map();
for (const f of walkPkgs(root)) {
  const j = readJson(f);
  if (!j) continue;
  const dir = path.dirname(f);
  if (j.name) packages.set(j.name, j);
  packages.set(path.basename(dir), packages.get(path.basename(dir)) ?? j);
}
function walkPkgs(dir, depth = 0, out = []) {
  if (depth > 3) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory() && !SKIP_DIRS.has(e.name)) walkPkgs(path.join(dir, e.name), depth + 1, out);
    else if (e.name === 'package.json') out.push(path.join(dir, e.name));
  }
  return out;
}
const rootPkg = readJson(path.join(root, 'package.json'));
// Project tasks live in `mise.toml`, the tasks of the repository standard in `.mise/conf.d/*.toml`.
const miseToml = (() => {
  const confD = path.join(root, '.mise/conf.d');
  const tomls = [path.join(root, 'mise.toml'), ...(fs.existsSync(confD) ? fs.readdirSync(confD).filter((f) => f.endsWith('.toml')).map((f) => path.join(confD, f)) : [])];
  const texts = tomls.filter((f) => fs.existsSync(f)).map((f) => fs.readFileSync(f, 'utf8'));
  return texts.length ? texts.join('\n') : null;
})();
const adrDir = ['docs/decisions', 'docs/adr', 'doc/adr', 'docs/ADR'].map((d) => path.join(root, d)).find((d) => fs.existsSync(d));
const adrNumbers = new Set(adrDir ? fs.readdirSync(adrDir).map((f) => f.match(/^(\d{3,4})/)?.[1]).filter(Boolean).map(Number) : []);

const problems = [];
let checked = 0;
const report = (file, line, kind, ref, why) => {
  if (ignore.has(ref)) return;
  problems.push({ file: path.relative(root, file), line, kind, ref, why });
};

// A path git ignores (secrets, local config, backups) lives only on a machine, not in the repo.
function gitIgnored(rel) {
  try {
    execFileSync('git', ['-C', root, 'check-ignore', '-q', '--no-index', rel], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function existsPath(ref, fromFile) {
  const clean = ref.replace(/:\d+(:\d+)?$/, '').replace(/[#?].*$/, '').replace(/\/$/, '');
  if (!clean || /NNNN|XXXX|YYYY|<|\.\.\./.test(clean)) return true;
  if (clean.startsWith('/')) return fs.existsSync(clean);
  if (fs.existsSync(path.join(root, clean)) || fs.existsSync(path.join(path.dirname(fromFile), clean))) return true;
  return gitIgnored(clean);
}

function looksLikeRepoPath(tok) {
  if (/\s|[<>{}*$|=,;()'"]|^\/|^\.\.\.|^~|^[A-Za-z]:\\|\\|^https?:|^@|^-/.test(tok)) return false;
  if (/^\d|\.\.\.$/.test(tok)) return false;
  if (!tok.includes('/') && !FILE_EXT.test(tok)) return false;
  if (!tok.includes('/') && FILE_EXT.test(tok)) return /^[A-Z_]+\.md$|^[\w.-]+\.(md|json|toml|ya?ml|pkl)$/i.test(tok) && fs.existsSync(path.join(root, tok)) ? true : false;
  const first = tok.split('/')[0];
  return fs.existsSync(path.join(root, first)) || first === '.';
}

function scriptExists(pkg, name) {
  return Boolean(pkg?.scripts && Object.prototype.hasOwnProperty.call(pkg.scripts, name));
}

function checkCommand(cmd, file, line) {
  const parts = cmd.split(/&&|\|\||;/).map((c) => c.trim()).filter(Boolean);
  if (parts.length > 1) { for (const c of parts) checkCommand(c, file, line); return; }
  const t = cmd.trim().split(/\s+/);
  const tool = t[0];
  if (['pnpm', 'npm', 'yarn', 'bun'].includes(tool)) {
    if (!rootPkg) return;
    let i = 1;
    let pkg = rootPkg;
    let label = 'package.json';
    while (i < t.length && t[i].startsWith('-')) {
      if (t[i] === '--filter' || t[i] === '-F') {
        const sel = t[i + 1]?.replace(/^\.\//, '');
        pkg = packages.get(sel) ?? packages.get(path.basename(sel ?? '')) ?? null;
        label = `${sel}/package.json`;
        if (!pkg) { checked++; report(file, line, 'command', cmd, `package "${sel}" not found`); return; }
        i += 2;
      } else i += 1;
    }
    if (t[i] === 'run') i += 1;
    const name = t[i];
    if (!name || name.startsWith('-')) return;
    if (tool === 'npm' && t[1] !== 'run' && !['test', 'start'].includes(name)) return;
    if (PM_BUILTINS.has(name) && !scriptExists(pkg, name)) return;
    checked++;
    // pnpm/yarn/bun also run installed binaries: `pnpm vitest`, `pnpm tsc`.
    const isBin = tool !== 'npm' && fs.existsSync(path.join(root, 'node_modules/.bin', name));
    if (!scriptExists(pkg, name) && !isBin) report(file, line, 'command', cmd, `no script "${name}" in ${label}`);
  } else if (tool === 'mise' && t[1] === 'run' && t[2]) {
    checked++;
    if (!miseToml) report(file, line, 'command', cmd, 'no mise.toml or .mise/conf.d/*.toml');
    else if (!new RegExp(`\\[tasks\\.["']?${t[2].replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']?\\]|^${t[2]}\\s*=`, 'm').test(miseToml)
      && !fs.existsSync(path.join(root, 'mise-tasks', t[2])) && !fs.existsSync(path.join(root, '.mise/tasks', t[2]))) {
      report(file, line, 'command', cmd, `no mise task "${t[2]}"`);
    }
  }
}

const files = filesArg
  ? filesArg.split(',').map((f) => path.resolve(root, f))
  : walk(root).filter((f) => all || !HISTORY.some((re) => re.test(path.relative(root, f))));
for (const file of files) {
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split('\n');
  let fence = false;
  lines.forEach((raw, idx) => {
    const n = idx + 1;
    if (/^\s*(```|~~~)/.test(raw)) {
      fence = !fence;
      return;
    }
    if (fence) {
      // Commands inside shell fences: first token before a comment.
      const c = raw.replace(/#.*$/, '').trim();
      if (/^(pnpm|npm|yarn|bun|mise)\s/.test(c)) checkCommand(c, file, n);
      return;
    }
    for (const m of raw.matchAll(/`([^`\n]+)`/g)) {
      const tok = m[1].trim();
      if (/^(pnpm|npm run|yarn|bun|mise run)\s/.test(tok)) { checkCommand(tok, file, n); continue; }
      if (looksLikeRepoPath(tok)) {
        checked++;
        if (!existsPath(tok, file)) report(file, n, 'path', tok, 'does not exist');
      }
    }
    for (const m of raw.matchAll(/\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g)) {
      const href = m[1];
      if (/^(https?:|mailto:|#|tel:)/.test(href)) continue;
      checked++;
      if (!existsPath(decodeURI(href), file)) report(file, n, 'link', href, 'target does not exist');
    }
    if (adrDir) {
      for (const m of raw.matchAll(/\bADR[ -]?(\d{3,4})\b/gi)) {
        checked++;
        if (!adrNumbers.has(Number(m[1]))) report(file, n, 'adr', `ADR ${m[1]}`, `no ${path.relative(root, adrDir)}/${m[1]}-*.md`);
      }
    }
  });
}

if (json) console.log(JSON.stringify({ checked, problems }, null, 2));
else {
  for (const p of problems) console.log(`${p.file}:${p.line}  ${p.kind}  ${p.ref}  — ${p.why}`);
  console.log(`\n${checked} references checked, ${problems.length} broken.`);
}
process.exit(problems.length ? 1 : 0);
