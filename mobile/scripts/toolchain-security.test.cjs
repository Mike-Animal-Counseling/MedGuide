const test = require('node:test');
const assert = require('node:assert/strict');
const braces = require('braces');
const forge = require('node-forge');
const { sprintf } = require('sprintf-js');
const fs = require('node:fs');
const vm = require('node:vm');

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

test('PEM parsing preserves normal and encrypted keys and rejects excessive malformed input', () => {
  const { privateKey } = forge.pki.rsa.generateKeyPair({ bits: 1024, e: 0x10001 });
  assert.equal(forge.pki.privateKeyFromPem(forge.pki.privateKeyToPem(privateKey)).n.toString(), privateKey.n.toString());
  const password = 'synthetic-toolchain-only';
  const encrypted = forge.pki.encryptRsaPrivateKey(privateKey, password, { algorithm: 'aes256', legacy: true });
  assert.equal(forge.pki.decryptRsaPrivateKey(encrypted, password).n.toString(), privateKey.n.toString());
  assert.throws(() => forge.pem.decode(' '.repeat(1048577)), RangeError);
  assert.throws(() => forge.pem.decode('-----BEGIN '.repeat(10000)));
  assert.throws(() => forge.pem.decode('-----BEGIN RSA PRIVATE KEY-----\n' + ' '.repeat(50000)));
});

test('HTTP cookies reject dangerous object keys without modifying prototypes', () => {
  const http = require('node-forge/lib/http');
  // A cookie-only fixture initializes no sockets and performs no network I/O.
  const client = http.createClient({ url: 'https://synthetic.example.invalid', socketPool: {}, connections: -1, persistCookies: false });
  for (const name of ['__proto__', 'constructor', 'prototype']) assert.equal(client.setCookie({ name, value: 'synthetic', path: '/', secure: true }), false);
  assert.equal(client.setCookie({ name: 'valid', value: 'synthetic', path: '__proto__', secure: true }), false);
  assert.equal({}.synthetic, undefined);
});

test('dedicated prime worker rejects foreign origins and oversized work messages', () => {
  let handler; const responses = [];
  const self = { location: { origin: 'https://synthetic.example.invalid' }, addEventListener: (_name, value) => { handler = value; }, postMessage: value => responses.push(value) };
  vm.runInNewContext(fs.readFileSync(require.resolve('node-forge/lib/prime.worker'), 'utf8'), { self, require: name => name === './forge' ? forge : require('node-forge/lib/jsbn') });
  const count = responses.length;
  handler({ origin: 'https://foreign.example.invalid', data: { hex: '01', workLoad: 1 } });
  handler({ origin: '', data: { hex: '01', workLoad: 1000000 } });
  handler({ origin: '', data: { hex: 'f'.repeat(3000), workLoad: 1 } });
  assert.equal(responses.length, count);
  handler({ origin: '', data: { hex: '01', workLoad: 1 } });
  assert.equal(responses.length, count + 1);
});
