# 0014. TypeScript profile as the base layer

Date: 2026-11-06
Status: accepted

## Context

- The first repository with code in the pilot is `cinema-ops`: TypeScript on Node with React and Vite, Fastify, FSD, without Next.js.
- The specification listed Next.js and Expo profiles with the same quality rules and no profile for plain TypeScript.
- `detect-stack` finds no profile for `cinema-ops`.

## Decision

- The `typescript` profile is the base layer: ESLint, Prettier, `strict` and `tsc --noEmit`, `check-size` with 300 lines for `.ts` and `.tsx`, the complexity rules of section 9 of the specification, dependency-cruiser `no-circular`, knip.
- Steiger is part of the `typescript` profile and runs when `architecture` names FSD.
- The `nextjs` and `expo` profiles extend `typescript` and add only their own parts: `eslint-config-next` and the router of Next.js; `expo-doctor` and the SDK version rules of Expo.
- `detect-stack` reports `typescript` for `tsconfig.json` and `package.json` without `next` and without `expo` in the dependencies.
- A repository has one of the three TypeScript profiles in `stack`, never two.

## Rejected

- One `nextjs` profile that also matches repositories without `next`: its name and router rules do not describe the repository.
- Separate full profiles for Next.js and Expo: the quality rules would be copied three times and drift.

## Consequences

- The quality rules of TypeScript change in one place.
- Templates of `nextjs` and `expo` render the files of `typescript` plus their own.
- The pilot `cinema-ops` tunes the thresholds of the base layer for all three profiles.
