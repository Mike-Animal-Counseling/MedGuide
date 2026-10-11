const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([{ ignores: ['vendor/**', 'dist/**'] }, ...expoConfig]);
