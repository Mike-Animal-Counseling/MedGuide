# Upstream provenance

Source: deepmerge 4.3.1, registry tarball https://registry.npmjs.org/deepmerge/-/deepmerge-4.3.1.tgz.

Integrity: sha512-3sUqbMEc77XqpdNO7FRyRog+eW3ph+GYCbj+rK+uYyRMuwsVy0rMiVtPn+QJlKFvWP/1PYpapqYn0Me2knFn+A==

The unminified upstream CommonJS build, type declarations, and license are retained. SECURITY.patch records the complete source change. This is an explicitly named local fork because the upstream advisory GHSA-gcqx-w48m-w2h4 has no fixed release as of 2026-10-31. All destination writes define own data properties, so neither source nor target keys can invoke the prototype setter. Review upstream weekly and replace the fork with a verified upstream fix when available.
