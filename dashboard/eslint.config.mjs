import { defineConfig, globalIgnores } from "eslint/config";

// We adopted TypeScript 7 ahead of the lint toolchain: typescript-eslint
// (pulled in by eslint-config-next) hard-refuses TypeScript >= 7 at import
// time — its current peer range caps at < 6.1.0 — and throws before any rule
// runs. `tsc --noEmit` still type-checks the project on TS 7, so type safety
// is unaffected; only ESLint's TypeScript-aware rules are the casualty.
//
// Load the Next configs defensively rather than dropping them for good: when
// typescript-eslint ships TS 7 support and it is picked up, the import below
// starts succeeding again and full linting returns with no further change.
// Until then eslint-config-next is skipped, so `eslint .` lints the remaining
// JS config files and leaves the TS sources to `tsc`.
let nextConfigs = [];
try {
  const [vitals, typescript] = await Promise.all([
    import("eslint-config-next/core-web-vitals"),
    import("eslint-config-next/typescript"),
  ]);
  nextConfigs = [...vitals.default, ...typescript.default];
} catch (error) {
  console.warn(
    `[eslint] eslint-config-next could not load, skipping it (TypeScript-aware ` +
      `linting is off until typescript-eslint supports this TypeScript version): ` +
      `${error?.message ?? error}`,
  );
}

export default defineConfig([
  ...nextConfigs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);
