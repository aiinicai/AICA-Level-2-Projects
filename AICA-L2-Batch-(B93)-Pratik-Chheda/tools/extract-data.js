// Copies the data embedded in a tracker index.html into a JSON file (kept out of git).
// Usage: node extract-data.js <index.html with data> <output.json>
'use strict';
const fs = require('fs');
const [input, output] = process.argv.slice(2);
if (!input || !output) { console.error('Usage: node extract-data.js <index.html> <output.json>'); process.exit(1); }
const m = fs.readFileSync(input, 'utf8').match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
if (!m) { console.error('No embedded data found (a protected website copy cannot be read this way)'); process.exit(1); }
const data = JSON.parse(m[1]);
fs.writeFileSync(output, JSON.stringify(data), 'utf8');
console.log(JSON.stringify({ saved: output, leads: data.items.length, meetings: data.meetings.length, investors: data.investors.length }));
