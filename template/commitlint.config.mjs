// Commit message rules of the repository standard.
// Self-contained: no `extends` and no imports, so the rules do not depend on where
// mise installs npm packages. The default commitlint parser reads Conventional Commits.

const TYPES = ["build", "chore", "ci", "docs", "feat", "fix", "perf", "refactor", "revert", "style", "test"];
const FORBIDDEN = /claude|anthropic\.com/i;
const EXEMPT_KEYS = new Set(["skip-check"]);
const TRAILER = /^([A-Za-z0-9][A-Za-z0-9-]*)\s*:\s*(.*)$/;
const GENERATED_WITH = /^\W*generated with\b/i;
const GIT_GENERATED = /^(Merge |Revert "|fixup! |squash! |amend! )/;
const SCISSORS = /^# -+ >8 -+$/;

// The message as git stores it: no comment lines, nothing below the scissors line.
function clean(raw) {
  const lines = [];
  for (const line of (raw ?? "").split("\n")) {
    if (SCISSORS.test(line)) break;
    if (!line.startsWith("#")) lines.push(line.replace(/\s+$/, ""));
  }
  return lines;
}

// Trailers are the last paragraph after the header when at least a quarter of its
// lines are `Key: value` lines (git counts indented lines as continuations).
function trailers(raw) {
  const paragraphs = clean(raw).join("\n").trim().split(/\n\s*\n/);
  if (paragraphs.length < 2) return [];
  const result = [];
  let lines = 0;
  for (const line of paragraphs.at(-1).split("\n")) {
    if (/^\s/.test(line) && result.length) {
      result.at(-1).value += ` ${line.trim()}`;
      continue;
    }
    lines += 1;
    const match = TRAILER.exec(line);
    if (match) result.push({ key: match[1], value: match[2] });
  }
  return result.length * 4 >= lines ? result : [];
}

function claudeTrailers(raw) {
  return trailers(raw)
    .filter(({ key }) => !EXEMPT_KEYS.has(key.toLowerCase()))
    .filter(({ key, value }) => FORBIDDEN.test(key) || FORBIDDEN.test(value))
    .map(({ key, value }) => `${key}: ${value}`);
}

function generatedWithLines(raw) {
  return clean(raw).slice(1).filter((line) => GENERATED_WITH.test(line));
}

export default {
  // The default (Angular) header pattern without the `!` breaking-change marker of Conventional Commits.
  parserPreset: {
    parserOpts: {
      headerPattern: /^(\w*)(?:\((.*)\))?!?: (.*)$/,
      breakingHeaderPattern: /^(\w*)(?:\((.*)\))?!: (.*)$/,
      headerCorrespondence: ["type", "scope", "subject"],
    },
  },
  // Merge, revert and fixup headers written by git skip the header rules, never the trailer rules.
  defaultIgnores: false,
  ignores: [
    (message) => GIT_GENERATED.test(message)
      && claudeTrailers(message).length === 0
      && generatedWithLines(message).length === 0,
  ],
  plugins: [
    {
      rules: {
        "trailer-no-claude": ({ raw }) => {
          const found = claudeTrailers(raw);
          return [found.length === 0, `trailers must not mention Claude or Anthropic: ${found.join("; ")}`];
        },
        "body-no-generated-with": ({ raw }) => {
          const found = generatedWithLines(raw);
          return [found.length === 0, `remove the "Generated with" line: ${found.join("; ")}`];
        },
      },
    },
  ],
  rules: {
    "header-max-length": [2, "always", 72],
    "header-trim": [2, "always"],
    "type-empty": [2, "never"],
    "type-case": [2, "always", "lower-case"],
    "type-enum": [2, "always", TYPES],
    "scope-case": [2, "always", "lower-case"],
    "subject-empty": [2, "never"],
    "subject-full-stop": [2, "never", "."],
    "body-leading-blank": [2, "always"],
    "footer-leading-blank": [2, "always"],
    "trailer-no-claude": [2, "always"],
    "body-no-generated-with": [2, "always"],
  },
};
