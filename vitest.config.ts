import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
    // Only *.vitest.ts: the *.test.ts suites import claude-code/testing and run under
    // `claude plugin test`, which in turn cannot load a vitest file.
    include: ['**/*.vitest.ts'],
    exclude: ['node_modules', 'dist', '.claude-plugin'],
  },
})
