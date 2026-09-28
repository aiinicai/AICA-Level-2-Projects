// Builds a client demo copy of the tracker with every real identity replaced by invented data.
// Structure, dates, statuses, follow up timing, meeting status and counts are kept, so every
// chart and view looks like the real thing; companies, people, investors, phone numbers,
// emails, note wording and fund amounts are invented. The output refuses to save if any
// real name, phone number or email from the source is still present.
//
// Usage: node make-demo.js <plain index.html> <demo .html>
'use strict';
const fs = require('fs');

const [input, output] = process.argv.slice(2);
let html = fs.readFileSync(input, 'utf8');
const dataRe = /<script id="data" type="application\/json">([\s\S]*?)<\/script>/;
const D = JSON.parse(html.match(dataRe)[1]);

// ---------------------------------------------------------------- deterministic helpers
let seed = 20260928;
const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
const hash = s => { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
const pickBy = (arr, key) => arr[hash(key) % arr.length];
const norm = s => String(s || '').trim().toLowerCase();

// ---------------------------------------------------------------- invented pools
const FIRST = ['Rohan', 'Ananya', 'Vikram', 'Priya', 'Arjun', 'Meera', 'Kunal', 'Sneha', 'Aditya', 'Ritu', 'Nikhil', 'Kavya', 'Neha', 'Rahul', 'Pooja', 'Amit', 'Isha', 'Varun', 'Tanya', 'Manish', 'Divya', 'Karan', 'Shreya', 'Harsh', 'Nisha', 'Gaurav', 'Rhea', 'Yash', 'Aarti'];
const LAST = ['Mehta', 'Iyer', 'Kapoor', 'Nair', 'Joshi', 'Reddy', 'Bansal', 'Desai', 'Kulkarni', 'Malhotra', 'Rao', 'Saxena', 'Gupta', 'Menon', 'Chawla', 'Bhatt', 'Pillai', 'Sethi', 'Agarwal', 'Khanna', 'Trivedi', 'Shetty', 'Jain', 'Verma'];
const BRAND = ['Aarav', 'Vistara', 'Nirmaan', 'Sanjeevani', 'Kaveri', 'Shakti', 'Tejas', 'Prakriti', 'Samarth', 'Vedanta', 'Arya', 'Sthira', 'Utkarsh', 'Navya', 'Pragati', 'Suryoday', 'Amrit', 'Dhruva', 'Ekam', 'Harit', 'Ishaan', 'Janya', 'Kalpa', 'Lakshya', 'Mitra', 'Ojas', 'Parth', 'Rudra', 'Saksham', 'Udaan', 'Vayu', 'Yukti', 'Aakar', 'Bodhi', 'Charvi', 'Dakshin', 'Eshan', 'Gati', 'Hansa', 'Indus', 'Jyoti', 'Kiran', 'Lumina', 'Medha', 'Nirvaan', 'Orion', 'Pavan', 'Quanta', 'Riddhi', 'Swastik', 'Tarang', 'Unnati', 'Varsha', 'Yamuna', 'Zeal'];
const LINE = { food: 'Agro Foods', agri: 'Agro Foods', pharma: 'Pharma', health: 'Healthcare', hospital: 'Healthcare', textile: 'Textiles', infra: 'Infra Projects', construct: 'Infra Projects', ev: 'EV Mobility', auto: 'Auto Components', solar: 'Solar', renew: 'Renewables', energy: 'Renewables', pack: 'Packaging', logist: 'Logistics', chem: 'Chemicals', electric: 'Electricals', tech: 'Technologies', it: 'Technologies', software: 'Technologies', retail: 'Retail', fmcg: 'Consumer Products', steel: 'Steel', metal: 'Metals', plastic: 'Polymers', jewel: 'Jewellers', real: 'Realty', finance: 'Finserv', edu: 'Learning', rail: 'Rail Systems', defence: 'Defence Systems' };
const LINES = ['Precision Engineering', 'Industries', 'Technologies', 'Agro Foods', 'Pharma', 'Packaging', 'Logistics', 'Electricals', 'Polymers', 'Infra Projects', 'Consumer Products', 'Renewables'];
const GEO = ['Northbridge', 'Sahyadri', 'Konkan', 'Deccan', 'Meridian', 'Aravalli', 'Coromandel', 'Brahmaputra', 'Western Ghats', 'Vindhya', 'Satpura', 'Malabar', 'Thar', 'Godavari', 'Nilgiri', 'Chambal', 'Kaziranga', 'Sundarban', 'Himalaya Crest', 'Kanchenjunga', 'Palk Bay', 'Mandovi', 'Tapti', 'Cauvery', 'Krishna Valley', 'Ganga Delta', 'Rann', 'Konark', 'Hampi', 'Chilika', 'Lonar', 'Shivalik', 'Saurashtra', 'Bastar', 'Garhwal'];
const SUF = ['Capital', 'Ventures', 'Growth Partners', 'Equity Advisors', 'Family Office', 'Investments', 'Capital Markets', 'Holdings'];
const FIRMS = []; SUF.forEach((s, j) => GEO.forEach((g, i) => FIRMS.push(g + ' ' + SUF[(i + j) % SUF.length])));
const CITIES = ['Mumbai', 'Pune', 'Ahmedabad', 'Bengaluru', 'Hyderabad', 'Chennai', 'Delhi NCR', 'Jaipur', 'Indore', 'Surat', 'Nagpur', 'Kolkata'];

const used = new Set();
const uniq = make => { for (let i = 0; i < 500; i++) { const v = make(i); if (!used.has(v)) { used.add(v); return v; } } return make(999) + ' ' + used.size; };
const personMap = new Map(), companyMap = new Map(), firmMap = new Map();
function person(real) {
  const k = norm(real); if (!k) return '';
  if (!personMap.has(k)) {
    const parts = String(real).split(/\s*(?:&|\band\b|,|\/)\s*/i).filter(Boolean);
    const one = i => uniq(j => FIRST[(hash(k + i) + j) % FIRST.length] + ' ' + LAST[(hash(k + 'l' + i) + j * 7) % LAST.length]);
    personMap.set(k, parts.length > 1 ? one(0).split(' ')[0] + ' & ' + one(1).split(' ')[0] : one(0));
  }
  return personMap.get(k);
}
function company(real, sector) {
  const k = norm(real); if (!k) return '';
  if (!companyMap.has(k)) {
    const s = norm(sector);
    const line = Object.entries(LINE).find(([w]) => new RegExp('\\b' + w).test(s));
    companyMap.set(k, uniq(j => BRAND[(hash(k) + j) % BRAND.length] + ' ' + (line ? line[1] : LINES[(hash(k + 's') + j) % LINES.length])));
  }
  return companyMap.get(k);
}
function firm(real) {
  const k = norm(real); if (!k) return '';
  if (!firmMap.has(k)) firmMap.set(k, uniq(j => FIRMS[(hash(k) + j) % FIRMS.length] + (j >= FIRMS.length ? ' ' + (j + 1) : '')));
  return firmMap.get(k);
}
const phone = k => { const h = hash('p' + k); return '9' + String(8 + (h % 2)) + String(h % 1000).padStart(3, '0') + ' ' + String(h % 100000).padStart(5, '0'); };
const email = (nameStr, dom) => String(nameStr || 'contact').toLowerCase().replace(/[^a-z]+/g, '.').replace(/^\.|\.$/g, '').slice(0, 20) + '@' + dom;
const domainOf = c => String(c).toLowerCase().replace(/[^a-z]+/g, '').slice(0, 14) + '.example.in';

// ---------------------------------------------------------------- invented note wording
const FILLER = /^\s*((no|not)\s*(updat\w*|upates|updatesz|update|reply|revert\w*|reverted back|answered)|na|wip|pending|in process|no reply.*|no revert\w*|noupdate|pending no revert from promoter|no updates?\s*[&-]\s*pending)[\s.\-]*$/i;
const POOLS = {
  meeting: ['Meeting held with the promoter; walked through the business and fund requirement', 'Zoom call with the CFO; discussed timelines and data requirements', 'Site visit done; plant running at about 70 percent capacity', 'Promoter meeting scheduled to discuss the raise structure', 'Joint call with the investor and promoter; follow up questions shared', 'Meeting requested by the promoter to understand the process'],
  mandate: ['Mandate discussion held; promoter reviewing the scope of work', 'Mandate signed; data collection to start', 'Commercials agreed in principle; mandate to be shared', 'Promoter asked for a revised retainer proposal'],
  drop: ['Promoter not interested at this stage; closed for now', 'Declined; valuation expectations too high', 'Not suitable for our investor base; closed', 'Promoter has low bandwidth this quarter; parked', 'Deal closed with another advisor'],
  hold: ['On hold till audited numbers are ready', 'On hold; promoter travelling, revisit next month'],
  share: ['Teaser shared with two family offices; awaiting feedback', 'Details shared with the investor; waiting for their view', 'Pitch deck shared; investor asked for last three years financials', 'Shared with the credit fund for an initial look'],
  data: ['Financials received; reviewing with the team', 'Asked for GST returns and the latest provisional numbers', 'KYC documents received from the promoter', 'Data room access shared with the analyst'],
  follow: ['Follow up call done; promoter to revert this week', 'Reminder sent; promoter to confirm the next step', 'Spoke to the associate; update expected next week', 'Called the promoter; asked to connect after the board meeting', 'Follow up tomorrow on the documents list', 'Promoter asked to reconnect on Friday']
};
function note(t) {
  const s = String(t || '');
  if (!s.trim() || FILLER.test(s)) return s;
  const l = s.toLowerCase();
  const pool = /meet|zoom|gmeet|visit|call with|joint call/.test(l) ? 'meeting' : /mandate|retainer|commercial/.test(l) ? 'mandate'
    : /not interested|declin|not suitable|low bandwidth|closed|drop|rrp/.test(l) ? 'drop' : /on hold/.test(l) ? 'hold'
    : /shared|investor|deck|teaser/.test(l) ? 'share' : /financial|document|kyc|data|gst|audit/.test(l) ? 'data' : 'follow';
  let out = pickBy(POOLS[pool], s);
  // keep the timing words the tracker reads for due dates and meeting times
  const cue = l.match(/\b(today|tomorrow|next week|this week|monday|tuesday|wednesday|thursday|friday|saturday|sunday|post \d{1,2}(st|nd|rd|th)? \w+)\b/);
  const tm = s.match(/\b\d{1,2}(?:[:.]\d{2})?\s*(am|pm)\b/i);
  if (cue && !out.toLowerCase().includes(cue[0])) out += ', ' + cue[0];
  if (tm) out += ' at ' + tm[0];
  return out;
}
const fundAsk = cr => { if (cr == null) return ''; const v = Math.max(2, Math.round(cr * (0.75 + (hash('f' + cr) % 50) / 100))); const lo = Math.max(1, Math.round(v * 0.8)); return lo + '-' + v + ' Cr'; };

// ---------------------------------------------------------------- rebuild the data
const realNames = new Set();
const keep = s => { if (s && String(s).trim().length >= 4) realNames.add(String(s).trim()); };
D.items.forEach(x => {
  [x.company, x.title, x.dealKey, x.counterparty, x.via, x.associate].forEach(keep);
  String(x.associate || '').split(/\s*(?:&|,|\/| - )\s*/).forEach(keep);
  String(x.counterparty || '').split(/\s*(?:&|,|\/| - )\s*/).forEach(keep);
  if (x.profile) keep(x.profile.name);
});
D.investors.forEach(c => { String(c.name || '').split(/\s*(?:;|&|,|\/|\(|\))\s*/).forEach(keep); keep(c.company); keep(c.connected); (c.deals || []).forEach(keep); });
(D.event.attendees || []).forEach(a => String(a.name).split(/\s*(?:-|&|,)\s*/).forEach(keep));
// company names written into the app's alias table and captions are real too
{ const a = html.match(/const ALIAS=\[([\s\S]*?)\];\n/); if (a) a[1].replace(/'([^']+)'\]/g, (m, n) => { keep(n); return m; }); }
// the Overview caption quotes a real company as its example of merged spellings
{ const c = html.match(/e\.g\. ([^<'"]{2,40}) spellings/); if (c) keep(c[1]); }
const realPhones = new Set(), realEmails = new Set();
const grab = s => { String(s || '').replace(/(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}/g, m => { realPhones.add(m.replace(/\D/g, '').slice(-10)); return m; }); String(s || '').replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, m => { realEmails.add(m.toLowerCase()); return m; }); };
D.items.forEach(x => { grab(x.mobile); grab(x.email); x.logs.forEach(l => grab(l.t)); });
D.investors.forEach(c => { grab(c.contact); grab(c.email); (c.notes || []).forEach(n => grab(n.t)); });

// never hand out an invented name that happens to match a real one
{
  const realWords = new Set([...realNames].join(' ').toLowerCase().split(/[^a-z]+/).filter(w => w.length >= 4));
  for (const pool of [FIRST, LAST, BRAND, GEO]) for (let i = pool.length - 1; i >= 0; i--) if (pool[i].toLowerCase().split(/\s+/).some(w => realWords.has(w))) pool.splice(i, 1);
  FIRMS.length = 0; SUF.forEach((s, j) => GEO.forEach((g, i) => FIRMS.push(g + ' ' + SUF[(i + j) % SUF.length])));
}
const cityMap = new Map();
const city = c => { const k = norm(c); if (!k) return ''; if (!cityMap.has(k)) cityMap.set(k, pickBy(CITIES, k)); return cityMap.get(k); };

D.items.forEach(x => {
  const co = company(x.company || x.dealKey || x.title, x.sector);
  const key = company(x.dealKey || x.company || x.title, x.sector);
// when the deal column is the lead's own title it names a company, otherwise usually the investor it went to
  const dealIsTitle = x.counterparty && (norm(x.title) === norm(x.counterparty) || norm(x.dealKey) === norm(x.counterparty));
  const cp = x.counterparty ? (norm(x.counterparty) === norm(x.company) ? co : dealIsTitle ? company(x.counterparty, x.sector) : firm(x.counterparty)) : '';
  x.title = dealIsTitle && norm(x.title) === norm(x.counterparty) ? cp : (norm(x.title) === norm(x.dealKey) ? key : company(x.title, x.sector));
  x.company = x.company ? co : ''; x.dealKey = key; x.counterparty = cp;
  x.via = x.via ? firm(x.via) : '';
  x.associate = person(x.associate); x.associateBased = city(x.associateBased); x.dealBased = city(x.dealBased);
  x.mobile = x.mobile ? person(x.associate + x.id).split(' ')[0] + ', ' + phone(x.id) : '';
  x.email = x.email ? email(person('promoter' + x.id), domainOf(x.company || x.title)) : '';
  x.docs = x.docs ? pickBy(['Pitch deck received', 'Financials received', 'KYC pending', 'Teaser received', 'Documents awaited'], x.docs) : '';
  x.fundAsk = x.fundAskCr != null ? fundAsk(x.fundAskCr) : (x.fundAsk ? 'To be confirmed' : '');
  if (x.fundAskCr != null) x.fundAskCr = +x.fundAsk.split('-')[1];
  x.nextFollowRaw = '';
  x.logs = x.logs.map(l => ({ ...l, t: note(l.t) }));
  x.lastNote = note(x.lastNote); x.lastSubstantiveNote = note(x.lastSubstantiveNote);
  if (x.nextAction) x.nextAction = { ...x.nextAction, text: note(x.nextAction.text), cue: x.nextAction.cue ? String(x.nextAction.cue).replace(/[A-Za-z]{4,}\s[A-Z][a-z]+/g, 'the promoter') : x.nextAction.cue };
  x.statusWhy = { Converted: 'History mentions the mandate signed', Dropped: 'Latest note says the promoter declined or the deal closed', 'On hold': 'Latest note says on hold', 'Closed elsewhere': 'Latest note says the deal closed with another advisor' }[x.status] || 'Open; status from recent activity';
  x.ownerWhy = x.owner === 'Unassigned' ? 'No PC, DS, VR mention in the row' : 'Last initials mentioned in the update log';
  if (x.profile) x.profile = { associate: x.associate, name: x.company || x.title, info: 'Mid sized ' + (x.sector || 'manufacturing') + ' business with a pan India customer base', products: 'Core product lines plus contract manufacturing', financials: 'FY25 revenue 25 to 75 Cr (illustrative)' };
});
D.meetings.forEach(m => {
  const it = D.items.find(x => m.ids && m.ids.includes(x.id));
  m.title = it ? it.title : company(m.title);
  m.dealKey = it ? it.dealKey : company(m.dealKey || m.title);
  m.associate = person(m.associate);
  m.text = note(m.text);
});
D.investors.forEach((c, i) => {
  const nm = person('inv' + c.name);
  c.company = firm(c.company || c.name); c.name = nm; c.based = city(c.based);
  c.connected = c.connected ? person(c.connected) : ''; c.contact = c.contact ? phone('inv' + i) : '';
  c.email = c.email ? email(nm, domainOf(c.company)) : '';
  c.deals = (c.deals || []).map(d => company(d));
  c.notes = (c.notes || []).map(n => ({ ...n, t: note(n.t), deal: n.deal ? company(n.deal) : '' }));
  c.latest = note(c.latest); c.nextFollowRaw = '';
  c.tokens = [c.name.toLowerCase(), c.company.toLowerCase()];
  if (c.dupRows) c.dupRows = c.dupRows;
});
D.event = { name: 'Investor meet', date: D.event.date, attendees: (D.event.attendees || []).map((a, i) => ({ ...a, name: person('guest' + i + a.name) })) };
D.source = 'Demo_Tracker.xlsx';
// sheet names other than the standard ones are named after people or events; rename them
const SHEET_STD = ['Associates', 'InvestorsFirms', 'Sheet5', 'Associate Leads', 'Investor meet'];
const sheetRenames = [];
const sheets = {}; Object.entries(D.sheets).forEach(([k, v]) => { const n = SHEET_STD.includes(k) ? k : /lead/i.test(k) ? 'Associate Leads' : 'Investor meet'; if (n !== k) sheetRenames.push([k, n]); sheets[n] = v; }); D.sheets = sheets;

// ---------------------------------------------------------------- write the demo page
html = html.replace(dataRe, () => '<script id="data" type="application/json">' + JSON.stringify(D) + '</script>');
html = html.replace('<html lang="en">', '<html lang="en" data-demo="1">');
html = html.replace(/const ALIAS=\[[\s\S]*?\];\n/, 'const ALIAS=[];\n');
// the demo keeps its own browser storage, so it never shows or changes real entries saved in the same browser
for (const [a, b] of [["const SK='df_lead_tracker_v2'", "const SK='df_demo_tracker_v1'"], ["'df_lead_tracker_edits_v1'", "'df_demo_tracker_old'"], ["const AUTO_KEY='df_automation'", "const AUTO_KEY='df_demo_automation'"], ["cfgKey:'df_drive_cfg'", "cfgKey:'df_demo_drive_cfg'"]]) {
  if (!html.includes(a)) { console.error('Expected to find ' + a); process.exit(1); }
  html = html.split(a).join(b);
}
for (const [from, to] of sheetRenames) html = html.split(from).join(to);
html = html.replace(/e\.g\. [^<'"]{2,40} spellings/, 'e.g. spelling variants of one company');
// any remaining real name in the app's text (for example the Data notes page) becomes its invented twin
const COMPANYISH = /\b(pvt|private|limited|ltd|llp|industries|capital|group|foods?|tech|technologies|bikes?|liquor|electricals|renewables|biofuels|automation|railtech|chem|gardens|tools|computing|jewellers|ventures|advisors|works|scuba)\b/i;
const twin = n => personMap.get(norm(n)) || companyMap.get(norm(n)) || firmMap.get(norm(n)) || (COMPANYISH.test(n) ? company(n) : person(n));
const STOP = /^(institute|institue|individual|fund raising|lead sourcing|deal sourcing|consultant|merchant banker|mumbai|bangalore|delhi|andheri|pending|updates?|shared|investor|family office|hni|valuation|ethanol|details|equity|funding|promoter|financials|meeting|others?)$/i;
// the firm's own name and its partners stay as they are
const names = [...realNames].filter(n => n.length >= 5 && !STOP.test(n) && !/sample advisory/i.test(n) && /[a-z]/i.test(n)).sort((a, b) => b.length - a.length);
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// sweep only the page's own text and code; the invented data block is left untouched
const dStart = html.indexOf('<script id="data" type="application/json">'), dEnd = html.indexOf('</script>', dStart) + 9;
let before = html.slice(0, dStart), dataBlock = html.slice(dStart, dEnd), after = html.slice(dEnd);
for (const n of names) {
  const re = new RegExp('(^|[^A-Za-z])' + esc(n) + '(?![A-Za-z])', 'gi');
  before = before.replace(re, (m, p) => p + twin(n));
  after = after.replace(re, (m, p) => p + twin(n));
}
html = before + dataBlock + after;

// example numbers written into the app's own text (Data notes) become a standard dummy
{
  const at = html.indexOf('<script>\n"use strict";');
  html = html.slice(0, at) + html.slice(at).replace(/\b[6-9]\d{4}\s?\d{5}\b/g, '98765 43210').replace(/\b\d\.\d{9}E\d\b/g, '9.876543210E9');
}

// ---------------------------------------------------------------- leak check
const low = html.toLowerCase();
const leakNames = names.filter(n => new RegExp('(^|[^a-z])' + esc(n.toLowerCase()) + '(?![a-z])').test(low));
const leakPhones = [...realPhones].filter(p => p.length === 10 && (low.includes(p) || low.includes(p.slice(0, 5) + ' ' + p.slice(5))));
const leakEmails = [...realEmails].filter(e => low.includes(e));
if (process.env.DF_DEMO_DEBUG) leakPhones.forEach(p => { const i = low.indexOf(p) >= 0 ? low.indexOf(p) : low.indexOf(p.slice(0, 5) + ' ' + p.slice(5)); console.error('phone context:', JSON.stringify(html.slice(Math.max(0, i - 120), i + 20).replace(/\d/g, '#'))); });
if (leakNames.length || leakPhones.length || leakEmails.length) {
  console.error('Refusing to save; real data still present:', JSON.stringify({ names: leakNames.slice(0, 20), nameCount: leakNames.length, phones: leakPhones.length, emails: leakEmails.length }));
  process.exit(2);
}
fs.writeFileSync(output, html, 'utf8');
console.log(JSON.stringify({ saved: output, leads: D.items.length, meetings: D.meetings.length, investors: D.investors.length, namesReplaced: names.length, phonesChecked: realPhones.size, emailsChecked: realEmails.size }));
