/*
 * Starts ABC Travel & Expense AND a secure public HTTPS link (Cloudflare quick tunnel),
 * so the app can be opened and installed ("Add to Home Screen" / "Install App") on any mobile phone.
 *
 *   node public_link.js           -> company database, port 8080
 *   node public_link.js --demo    -> demo database, port 8081
 *
 * Requires cloudflared (free). Start_Public_Link.bat installs it automatically with winget.
 * The link looks like https://random-words.trycloudflare.com and changes every time you restart.
 * Keep this window open and the PC awake while people use the link.
 */
'use strict';
const { spawn, spawnSync, exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const [maj, min] = process.versions.node.split('.').map(Number);
if (maj < 22 || (maj === 22 && min < 5)) { console.error('Node.js 22 or newer is required.'); process.exit(1); }
const flags = ['--no-warnings'];
if (maj === 22 && min < 13) flags.push('--experimental-sqlite');

const demo = process.argv.includes('--demo');
const env = { ...process.env, PORT: process.env.PORT || (demo ? '8081' : '8080') };
if (demo) {
  env.DB_FILE = path.join(__dirname, 'data', 'abc_travel_demo.db');
  if (!fs.existsSync(env.DB_FILE)) spawnSync(process.execPath, [...flags, path.join(__dirname, 'tools', 'seed_demo_data.js'), env.DB_FILE], { stdio: 'inherit' });
}

function findCloudflared() {
  const cands = ['cloudflared'];
  if (process.platform === 'win32') {
    const pf = process.env['ProgramFiles'] || 'C:\\Program Files';
    const pf86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
    const la = process.env.LOCALAPPDATA || '';
    cands.push(path.join(pf86, 'cloudflared', 'cloudflared.exe'), path.join(pf, 'cloudflared', 'cloudflared.exe'),
      path.join(la, 'Microsoft', 'WinGet', 'Links', 'cloudflared.exe'), path.join(__dirname, 'cloudflared.exe'));
  } else cands.push('/usr/local/bin/cloudflared', '/opt/homebrew/bin/cloudflared');
  for (const c of cands) {
    if (c !== 'cloudflared' && !fs.existsSync(c)) continue;
    const r = spawnSync(c, ['--version'], { encoding: 'utf8' });
    if (!r.error && r.status === 0) return c;
  }
  return null;
}

const cf = findCloudflared();
if (!cf) {
  console.error('\n[ERROR] cloudflared is not installed.');
  console.error('  Windows: winget install --id Cloudflare.cloudflared   (or run Start_Public_Link.bat)');
  console.error('  macOS:   brew install cloudflared\n');
  process.exit(1);
}

const local = `http://localhost:${env.PORT}`;
let server = { kill() {} };
let printed = false;
require('http').get(local + '/api/health', (res) => { res.resume(); console.log('App is already running at ' + local + ' - using it.'); startTunnel(); })
  .on('error', () => {
    server = spawn(process.execPath, [...flags, path.join(__dirname, 'server.js')], { env, stdio: ['ignore', 'pipe', 'inherit'] });
    server.stdout.on('data', () => {});
    server.on('exit', (code) => { console.error('Server stopped (' + code + ').'); process.exit(code || 1); });
    setTimeout(startTunnel, 1500);
  });

function startTunnel() {
  console.log(`Local app running at ${local}. Creating secure public link (takes 5-20 seconds)...`);
  const tunnel = spawn(cf, ['tunnel', '--no-autoupdate', '--url', local], { stdio: ['ignore', 'pipe', 'pipe'] });
  const onData = (buf) => {
    const m = String(buf).match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/i);
    if (m && !printed) {
      printed = true;
      const url = m[0];
      fs.writeFileSync(path.join(__dirname, 'PUBLIC_LINK.txt'),
        `ABC Travel & Expense - public link (valid while the PC and this window stay on)\r\n\r\n${url}\r\n\r\nCreated: ${new Date().toLocaleString()}\r\n`);
      console.log('\n==================================================================');
      console.log('  SHARE THIS LINK WITH EMPLOYEES (works on mobile & any PC):');
      console.log('\n     ' + url + '\n');
      console.log('  On phone: open the link in Chrome -> tap "Install App" in the menu bar');
      console.log('            (iPhone: Safari -> Share -> Add to Home Screen)');
      console.log('  Link also saved in PUBLIC_LINK.txt. It changes each time you restart.');
      console.log('  KEEP THIS WINDOW OPEN and the PC awake. Press Ctrl+C to stop.');
      console.log('==================================================================\n');
      if (!process.argv.includes('--no-browser')) {
        const cmd = process.platform === 'win32' ? `start "" "${url}"` : process.platform === 'darwin' ? `open "${url}"` : `xdg-open "${url}"`;
        setTimeout(() => exec(cmd, () => {}), 4000);
      }
    }
  };
  tunnel.stdout.on('data', onData);
  tunnel.stderr.on('data', onData);
  tunnel.on('exit', (code) => { console.error('Public link stopped (cloudflared exit ' + code + ').'); server.kill(); process.exit(code || 0); });
  const stop = () => { tunnel.kill(); server.kill(); process.exit(0); };
  process.on('SIGINT', stop); process.on('SIGTERM', stop);
  setTimeout(() => { if (!printed) console.log('Still waiting for the link... check the internet connection / firewall.'); }, 45000);
}
