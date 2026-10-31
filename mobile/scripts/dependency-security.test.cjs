const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('distributed matcher adapter matches its reviewed readable sources', () => {
  const archive = require('node:zlib').gunzipSync(fs.readFileSync(path.join(__dirname, '../vendor/medguide-minimatch-compat-1.0.0.tgz')));
  const entries = new Map();
  for (let offset = 0; offset + 512 <= archive.length && archive[offset];) {
    const header = archive.subarray(offset, offset + 512);
    const name = header.subarray(0, 100).toString().replace(/\0.*$/, '');
    const size = parseInt(header.subarray(124, 136).toString().replace(/\0.*$/, '').trim(), 8);
    assert.ok(Number.isSafeInteger(size) && size >= 0);
    entries.set(name, archive.subarray(offset + 512, offset + 512 + size));
    offset += 512 + Math.ceil(size / 512) * 512;
  }
  const files = ['README.md', 'index.cjs', 'index.d.ts', 'index.mjs', 'package.json'];
  assert.equal(entries.size, files.length);
  for (const file of files) {
    assert.deepEqual(entries.get('package/' + file), fs.readFileSync(path.join(__dirname, '../vendor/minimatch', file)));
  }
});

test('deep merge preserves data without poisoning output prototypes from either input', () => {
  const merge = require('deepmerge');
  assert.equal(require('deepmerge/package.json').name, '@medguide/deepmerge-hardened');
  const poisonedTarget = JSON.parse('{"__proto__":{"privileged":true},"nested":{"a":1}}');
  const poisonedSource = JSON.parse('{"__proto__":{"privileged":true},"nested":{"b":2}}');
  for (const [target, source] of [[poisonedTarget, {}], [{}, poisonedSource], [poisonedTarget, poisonedSource]]) {
    const result = merge(target, source);
    assert.equal(Object.getPrototypeOf(result), Object.prototype);
    assert.equal(result.privileged, undefined);
    assert.equal({}.privileged, undefined);
  }
  const symbol = Symbol('kept');
  const result = merge({ nested: { a: 1 }, items: [1], [symbol]: { x: 1 } }, { nested: { b: 2 }, items: [2] });
  assert.deepEqual(result.nested, { a: 1, b: 2 });
  assert.deepEqual(result.items, [1, 2]);
  assert.deepEqual(result[symbol], { x: 1 });
  assert.deepEqual(merge({ items: [1] }, { items: [2] }, { arrayMerge: (_target, source) => source }).items, [2]);
});

test('maintained minimatch supports legacy callable and modern named module interfaces', async () => {
  const matcher = require('minimatch');
  const modern = await import('minimatch');
  assert.equal(require('minimatch/package.json').name, '@medguide/minimatch-compat');
  assert.equal(require('minimatch-core/package.json').version, '11.0.3');
  assert.equal(typeof matcher, 'function');
  assert.equal(matcher('src/feature.test.ts', 'src/**/*.ts'), true);
  assert.equal(matcher('src/feature.js', 'src/**/*.ts'), false);
  assert.equal(matcher.defaults({ dot: true })('.hidden', '*'), true);
  assert.equal(new modern.Minimatch('src/**/*.ts').match('src/feature.ts'), true);
  assert.equal(modern.default('file.ts', '*.ts'), true);
  assert.deepEqual(matcher.match(['a.ts', 'b.js'], '*.ts'), ['a.ts']);
});

test('glob cancellation stops directory reads after the rejected walk', async () => {
  const { glob, globSync } = require('glob');
  const fixture = fs.mkdtempSync(path.join(process.cwd(), '.toolchain-fixture-'));
  try {
    for (let i = 0; i < 8; i++) {
      fs.mkdirSync(path.join(fixture, 'branch-' + i, 'nested'), { recursive: true });
      fs.writeFileSync(path.join(fixture, 'branch-' + i, 'nested', 'file.ts'), 'synthetic');
    }
    assert.equal(globSync('**/*.ts', { cwd: fixture }).length, 8);
    const controller = new AbortController();
    let reads = 0;
    const instrumented = {
      ...fs,
      readdir(...args) {
        reads++;
        const callback = args.pop();
        fs.readdir(...args, (error, entries) => {
          controller.abort(new Error('budget-expired'));
          callback(error, entries);
        });
      },
      promises: {
        ...fs.promises,
        async readdir(...args) {
          reads++;
          const entries = await fs.promises.readdir(...args);
          controller.abort(new Error('budget-expired'));
          return entries;
        },
      },
    };
    await assert.rejects(glob('**/*', { cwd: fixture, signal: controller.signal, fs: instrumented }), /budget-expired/);
    const readsAtRejection = reads;
    await new Promise(resolve => setTimeout(resolve, 50));
    assert.equal(readsAtRejection, 1);
    assert.equal(reads, readsAtRejection);
  } finally {
    assert.equal(path.dirname(fixture), process.cwd());
    fs.rmSync(fixture, { recursive: true, force: true });
  }
});

test('Zod rejects oversized constrained arrays without an issue for each element', () => {
  const { z } = require('zod');
  const result = z.array(z.number()).max(8).safeParse(Array(10000).fill('invalid'));
  assert.equal(result.success, false);
  assert.ok(result.error.issues.length < 20);
});
