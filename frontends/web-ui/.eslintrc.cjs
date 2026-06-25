// Project-local ESLint config — overrides the user-level ~/.eslintrc.json
// which references next/core-web-vitals (Mark's other project, not installed here).
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['@typescript-eslint', 'react-refresh', 'react-hooks'],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'node_modules'],
  rules: {
    // HMR optimization, not a correctness rule. icons.tsx + eventStreamContext.tsx
    // intentionally mix components with constant maps / hooks. Worst case dev impact
    // is a full reload instead of HMR; production builds are unaffected.
    'react-refresh/only-export-components': 'off',
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    '@typescript-eslint/no-unused-vars': [
      'warn',
      { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
    ],
    '@typescript-eslint/no-explicit-any': 'off',
  },
};
