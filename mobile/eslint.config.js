const { defineConfig } = require('eslint/config');
const { fixupConfigRules } = require('@eslint/compat');
const expoConfig = require('eslint-config-expo/flat');

// Preserve Expo plugin rules while adapting their legacy APIs to ESLint 10.
module.exports = defineConfig([
  { ignores: ['vendor/**', 'dist/**'] },
  ...fixupConfigRules(expoConfig),
]);
