# minimatch compatibility entry points

This is a local adapter, not an upstream fork or a claimed patched legacy release. It delegates matching to the exact upstream minimatch 11.0.3 package through the npm alias `minimatch-core`. Legacy CommonJS callers receive the callable matcher; modern CommonJS and ESM callers retain named exports. The matcher implementation and its security fixes remain upstream.

Regression coverage lives in `scripts/toolchain-security.test.cjs`; the full lint, Jest and Expo export gates verify toolchain interoperability. Remove the adapter once all consumers support the maintained upstream module interface.
