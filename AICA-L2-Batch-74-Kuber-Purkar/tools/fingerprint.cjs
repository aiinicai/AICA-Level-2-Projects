// Prints this machine's fingerprint JSON (give this to the vendor to receive a license key).
const { machineIdentity } = require('../server/license.cjs');
const id = machineIdentity();
console.log('Machine code :', id.code);
console.log('Fingerprint JSON (send this to the vendor):');
console.log(JSON.stringify(id.hashes));
