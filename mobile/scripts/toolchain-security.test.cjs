const test = require('node:test');
const assert = require('node:assert/strict');
const braces = require('braces');
const forge = require('node-forge');
const { sprintf } = require('sprintf-js');

test('every resolved vulnerable package is the explicitly maintained fork', () => {
  for (const name of ['braces', 'node-forge', 'sprintf-js']) {
    assert.equal(require(name + '/package.json').name, '@medguide/' + name + '-hardened');
  }
});
test('normal patterns work, while recursive patterns and caller ASTs are bounded', () => {
  assert.deepEqual(braces.expand('src/{a,b}.js'), ['src/a.js', 'src/b.js']);
  assert.equal(braces.compile('{a,b}'), '(a|b)');
  const pattern = '{'.repeat(5000) + 'a,b' + '}'.repeat(5000);
  for (const method of ['parse', 'compile', 'expand', 'stringify']) assert.throws(() => braces[method](pattern), SyntaxError);
  let tree = { type: 'text', value: 'a' };
  for (let i = 0; i < 1000; i++) tree = { type: 'brace', nodes: [tree] };
  for (const method of ['compile', 'expand', 'stringify']) assert.throws(() => braces[method](tree), SyntaxError);
  const cyclic = { type: 'root', nodes: [] }; cyclic.nodes.push(cyclic);
  assert.throws(() => braces.compile(cyclic), SyntaxError);
  assert.throws(() => braces.expand('{a,b}'.repeat(20)), RangeError);
  assert.throws(() => braces.expand('{1..1000000000}', { rangeLimit: false }), RangeError);
});
test('RSA verification accepts normal signatures and rejects nested extra DigestAlgorithm values', () => {
  const { publicKey, privateKey } = forge.pki.rsa.generateKeyPair({ bits: 1024, e: 0x10001 });
  const md = forge.md.sha256.create().update('synthetic regression message');
  const digest = md.digest().getBytes();
  assert.equal(publicKey.verify(digest, privateKey.sign(md)), true);
  const asn = forge.asn1, u = asn.Class.UNIVERSAL;
  const oid = () => asn.create(u, asn.Type.OID, false, asn.oidToDer(forge.pki.oids.sha256).getBytes());
  const emptyNull = () => asn.create(u, asn.Type.NULL, false, '');
  const extraCases = [
    [oid(), emptyNull(), emptyNull()],
    [oid(), asn.create(u, asn.Type.SEQUENCE, true, [emptyNull()])],
    [oid(), asn.create(u, asn.Type.NULL, false, 'not-empty')],
  ];
  for (const children of extraCases) {
    const info = asn.create(u, asn.Type.SEQUENCE, true, [
      asn.create(u, asn.Type.SEQUENCE, true, children),
      asn.create(u, asn.Type.OCTETSTRING, false, digest),
    ]);
    const signature = privateKey.sign({ digest: () => asn.toDer(info) }, 'NONE');
    assert.throws(() => publicKey.verify(digest, signature));
  }
});
test('format widths and precision are bounded without changing normal output', () => {
  assert.equal(sprintf('%.2f %s', 1.25, 'ok'), '1.25 ok');
  assert.throws(() => sprintf('%1000000000s', 'x'), RangeError);
  assert.throws(() => sprintf('%.1000000000f', 1.2), RangeError);
  assert.throws(() => sprintf('x'.repeat(10001)), RangeError);
});
