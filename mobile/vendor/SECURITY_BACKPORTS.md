# Maintained security backports

These three packages are explicit repository-local forks of upstream libraries, not claimed upstream patched releases. Each fork records the registry tarball integrity, retains the original license/attribution, and includes the exact source patch. No install hooks or unpatched minified build is distributed. npm overrides apply the same fork throughout the dependency tree.

* `braces` 3.0.3: GHSA-vfj7-8cjw-p6xm. Limit parser nesting and validate ASTs iteratively before recursive compile, expand or stringify. Reject cyclic or excessive caller-supplied ASTs. Cap Cartesian/range expansion at 10,000 outputs even if callers disable the upstream range limit.
* `node-forge` 1.4.0: GHSA-86w9-cpqp-85rv. Require exactly one algorithm OID and at most one primitive, empty NULL parameter inside RSA PKCS#1 v1.5 DigestAlgorithm. Reject additional nested values before comparing the digest.
* `sprintf-js` 1.1.3: GHSA-hp3w-g68c-fv3c. Bound width and precision before formatting, including the direct pre-parsed formatting API.

`npm run test:security` verifies malformed inputs/signatures are rejected while normal glob expansion, formatting and RSA signatures still work. Replace these local forks with verified upstream fixed releases as soon as available; the owner must review upstream security changes weekly via the scheduled audit. Library-specific dependency scans remain necessary alongside npm audit because a repository-local fork cannot inherit upstream advisory coverage automatically.
