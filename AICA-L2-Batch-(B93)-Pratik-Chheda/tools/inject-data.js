// Puts a tracker dataset (JSON) into index.html so the app opens with that data.
// The repository keeps tracker/app/index.html empty; run this locally before building
// the desktop app or the protected website copy, and never commit the result.
// Usage: node inject-data.js <data.json> <index.html in> <index.html out>
'use strict';
const fs = require('fs');
const [dataFile, input, output] = process.argv.slice(2);
if (!dataFile || !input || !output) { console.error('Usage: node inject-data.js <data.json> <index.html in> <index.html out>'); process.exit(1); }
const data = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
for (const k of ['items', 'meetings', 'investors', 'logDates']) if (!Array.isArray(data[k])) { console.error('The data file has no ' + k + ' list'); process.exit(1); }
const html = fs.readFileSync(input, 'utf8');
const re = /<script id="data" type="application\/json">[\s\S]*?<\/script>/;
if (!re.test(html)) { console.error('No data block found in ' + input); process.exit(1); }
// "</" inside the JSON would end the script tag early
const json = JSON.stringify(data).replace(/<\//g, '<\\/');
fs.writeFileSync(output, html.replace(re, () => '<script id="data" type="application/json">' + json + '</script>'), 'utf8');
console.log(JSON.stringify({ saved: output, leads: data.items.length }));
