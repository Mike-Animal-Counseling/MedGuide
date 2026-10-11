/**
 * Javascript implementation of basic PEM (Privacy Enhanced Mail) algorithms.
 *
 * See: RFC 1421.
 *
 * @author Dave Longley
 *
 * Copyright (c) 2013-2014 Digital Bazaar, Inc.
 *
 * A Forge PEM object has the following fields:
 *
 * type: identifies the type of message (eg: "RSA PRIVATE KEY").
 *
 * procType: identifies the type of processing performed on the message,
 *   it has two subfields: version and type, eg: 4,ENCRYPTED.
 *
 * contentDomain: identifies the type of content in the message, typically
 *   only uses the value: "RFC822".
 *
 * dekInfo: identifies the message encryption algorithm and mode and includes
 *   any parameters for the algorithm, it has two subfields: algorithm and
 *   parameters, eg: DES-CBC,F8143EDE5960C597.
 *
 * headers: contains all other PEM encapsulated headers -- where order is
 *   significant (for pairing data like recipient ID + key info).
 *
 * body: the binary-encoded body.
 */
var forge = require('./forge');
require('./util');

// shortcut for pem API
var pem = module.exports = forge.pem = forge.pem || {};

/**
 * Encodes (serializes) the given PEM object.
 *
 * @param msg the PEM message object to encode.
 * @param options the options to use:
 *          maxline the maximum characters per line for the body, (default: 64).
 *
 * @return the PEM-formatted string.
 */
pem.encode = function(msg, options) {
  options = options || {};
  var rval = '-----BEGIN ' + msg.type + '-----\r\n';

  // encode special headers
  var header;
  if(msg.procType) {
    header = {
      name: 'Proc-Type',
      values: [String(msg.procType.version), msg.procType.type]
    };
    rval += foldHeader(header);
  }
  if(msg.contentDomain) {
    header = {name: 'Content-Domain', values: [msg.contentDomain]};
    rval += foldHeader(header);
  }
  if(msg.dekInfo) {
    header = {name: 'DEK-Info', values: [msg.dekInfo.algorithm]};
    if(msg.dekInfo.parameters) {
      header.values.push(msg.dekInfo.parameters);
    }
    rval += foldHeader(header);
  }

  if(msg.headers) {
    // encode all other headers
    for(var i = 0; i < msg.headers.length; ++i) {
      rval += foldHeader(msg.headers[i]);
    }
  }

  // terminate header
  if(msg.procType) {
    rval += '\r\n';
  }

  // add body
  rval += forge.util.encode64(msg.body, options.maxline || 64) + '\r\n';

  rval += '-----END ' + msg.type + '-----\r\n';
  return rval;
};

/**
 * Decodes (deserializes) all PEM messages found in the given string.
 *
 * @param str the PEM-formatted string to decode.
 *
 * @return the PEM message objects in an array.
 */
pem.decode = function(str) {
  var rval = [];

  // Parse boundaries with linear scans instead of backtracking expressions.
  var messages = readPemMessages(str);
  var messageIndex = 0;
  var rCRLF = /\r?\n/;
  var match;
  while(true) {
    match = messages[messageIndex++];
    if(!match) {
      break;
    }

    // accept "NEW CERTIFICATE REQUEST" as "CERTIFICATE REQUEST"
    // https://datatracker.ietf.org/doc/html/rfc7468#section-7
    var type = match[1];
    if(type === 'NEW CERTIFICATE REQUEST') {
      type = 'CERTIFICATE REQUEST';
    }

    var msg = {
      type: type,
      procType: null,
      contentDomain: null,
      dekInfo: null,
      headers: [],
      body: forge.util.decode64(match[3])
    };
    rval.push(msg);

    // no headers
    if(!match[2]) {
      continue;
    }

    // parse headers
    var lines = match[2].split(rCRLF);
    var li = 0;
    while(match && li < lines.length) {
      // get line, trim any rhs whitespace
      var line = lines[li].trimEnd();

      // RFC2822 unfold any following folded lines
      for(var nl = li + 1; nl < lines.length; ++nl) {
        var next = lines[nl];
        if(!/\s/.test(next[0])) {
          break;
        }
        line += next;
        li = nl;
      }

      // parse header
      var colon = line.indexOf(':');
      if(colon < 1 || colon > 128 || !/^[\x21-\x7e]{1,128}$/.test(line.slice(0, colon))) {
        throw new Error('Invalid PEM header');
      }
      match = [line, line.slice(0, colon), line.slice(colon + 1).trimStart()];
      if(match) {
        var header = {name: match[1], values: []};
        var values = match[2].split(',');
        for(var vi = 0; vi < values.length; ++vi) {
          header.values.push(ltrim(values[vi]));
        }

        // Proc-Type must be the first header
        if(!msg.procType) {
          if(header.name !== 'Proc-Type') {
            throw new Error('Invalid PEM formatted message. The first ' +
              'encapsulated header must be "Proc-Type".');
          } else if(header.values.length !== 2) {
            throw new Error('Invalid PEM formatted message. The "Proc-Type" ' +
              'header must have two subfields.');
          }
          msg.procType = {version: values[0], type: values[1]};
        } else if(!msg.contentDomain && header.name === 'Content-Domain') {
          // special-case Content-Domain
          msg.contentDomain = values[0] || '';
        } else if(!msg.dekInfo && header.name === 'DEK-Info') {
          // special-case DEK-Info
          if(header.values.length === 0) {
            throw new Error('Invalid PEM formatted message. The "DEK-Info" ' +
              'header must have at least one subfield.');
          }
          msg.dekInfo = {algorithm: values[0], parameters: values[1] || null};
        } else {
          msg.headers.push(header);
        }
      }

      ++li;
    }

    if(msg.procType === 'ENCRYPTED' && !msg.dekInfo) {
      throw new Error('Invalid PEM formatted message. The "DEK-Info" ' +
        'header must be present if "Proc-Type" is "ENCRYPTED".');
    }
  }

  if(rval.length === 0) {
    throw new Error('Invalid PEM formatted message.');
  }

  return rval;
};

function foldHeader(header) {
  var rval = header.name + ': ';

  // ensure values with CRLF are folded
  var values = [];
  var insertSpace = function(match, $1) {
    return ' ' + $1;
  };
  for(var i = 0; i < header.values.length; ++i) {
    values.push(header.values[i].replace(/^(\S+\r\n)/, insertSpace));
  }
  rval += values.join(',') + '\r\n';

  // do folding
  var length = 0;
  var candidate = -1;
  for(var i = 0; i < rval.length; ++i, ++length) {
    if(length > 65 && candidate !== -1) {
      var insert = rval[candidate];
      if(insert === ',') {
        ++candidate;
        rval = rval.substr(0, candidate) + '\r\n ' + rval.substr(candidate);
      } else {
        rval = rval.substr(0, candidate) +
          '\r\n' + insert + rval.substr(candidate + 1);
      }
      length = (i - candidate - 1);
      candidate = -1;
      ++i;
    } else if(rval[i] === ' ' || rval[i] === '\t' || rval[i] === ',') {
      candidate = i;
    }
  }

  return rval;
}

function ltrim(str) {
  return str.trimStart();
}

function readPemMessages(str) {
  if(typeof str !== 'string' || str.length > 1048576) throw new RangeError('PEM input exceeds safe limits');
  var messages = [], position = 0;
  while(position < str.length) {
    var begin = str.indexOf('-----BEGIN ', position);
    if(begin === -1) break;
    var typeEnd = str.indexOf('-----', begin + 11);
    if(typeEnd === -1 || typeEnd - begin > 100) throw new Error('Invalid PEM boundary');
    var type = str.slice(begin + 11, typeEnd);
    if(!/^[A-Z0-9][A-Z0-9 -]{0,79}$/.test(type)) throw new Error('Invalid PEM type');
    var bodyStart = typeEnd + 5, endMarker = '-----END ' + type + '-----';
    var end = str.indexOf(endMarker, bodyStart);
    if(end === -1) throw new Error('Missing PEM end boundary');
    var block = str.slice(bodyStart, end).trim();
    var lines = block.split('\n').map(function(line) { return line.endsWith('\r') ? line.slice(0, -1) : line; });
    for(var i = 0; i < lines.length; ++i) if(lines[i].length > 16384) throw new RangeError('PEM line exceeds safe limits');
    var headerLines = [], bodyLines = lines;
    if(lines.length && lines[0].indexOf(':') !== -1) {
      var separator = lines.indexOf('');
      if(separator < 1 || separator > 128) throw new Error('Invalid PEM header separator');
      headerLines = lines.slice(0, separator); bodyLines = lines.slice(separator + 1);
    }
    var body = bodyLines.join('\n');
    if(!/^[A-Za-z0-9+/= \t\r\n]*$/.test(body)) throw new Error('Invalid PEM body');
    messages.push([str.slice(begin, end + endMarker.length), type, headerLines.length ? headerLines.join('\n') : null, body]);
    if(messages.length > 100) throw new RangeError('Too many PEM messages');
    position = end + endMarker.length;
  }
  return messages;
}
