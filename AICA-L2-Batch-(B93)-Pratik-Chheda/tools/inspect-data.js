// Prints the shape of the tracker's embedded data (development helper).
const fs = require('fs');
const h = fs.readFileSync(process.argv[2], 'utf8');
const m = h.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/);
const D = JSON.parse(m[1]);
const shape = v => Array.isArray(v) ? 'array(' + v.length + ')' : v && typeof v === 'object' ? 'object{' + Object.keys(v).join(',') + '}' : typeof v;
for (const [k, v] of Object.entries(D)) console.log(k, ':', shape(v));
const it = D.items[5];
console.log('\nITEM:', JSON.stringify(Object.fromEntries(Object.entries(it).map(([k, v]) => [k, shape(v)]))));
console.log('log sample:', JSON.stringify(it.logs.slice(0, 2)));
console.log('nextAction:', JSON.stringify(it.nextAction));
console.log('\nMEETING:', JSON.stringify(D.meetings[0]).slice(0, 500));
console.log('\nINVESTOR:', JSON.stringify(D.investors[0]).slice(0, 600));
const wp = D.items.find(x => x.profile); console.log('\nprofile:', wp && JSON.stringify(wp.profile).slice(0, 300));
for (const k of Object.keys(D)) if (!['items', 'meetings', 'investors'].includes(k)) console.log('\n' + k, '=', JSON.stringify(D[k]).slice(0, 400));
