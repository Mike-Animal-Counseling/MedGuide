'use strict';
// Legacy consumers call require('minimatch'); modern consumers use named exports.
// Both paths delegate to the same patched upstream matcher without copying it.
const core = require('minimatch-core');
module.exports = core.minimatch;
module.exports.minimatch = core.minimatch;
module.exports.Minimatch = core.Minimatch;
module.exports.GLOBSTAR = core.GLOBSTAR;
module.exports.sep = core.sep;
module.exports.filter = core.filter;
module.exports.defaults = core.defaults;
module.exports.braceExpand = core.braceExpand;
module.exports.match = core.match;
module.exports.makeRe = core.minimatch.makeRe;
module.exports.escape = core.escape;
module.exports.unescape = core.unescape;
