/*
 * One-click launcher for ABC Travel & Expense.
 *   node launch.js          -> starts the app on http://localhost:8080 with your company database
 *   node launch.js --demo   -> creates (if needed) and starts the DEMO database on http://localhost:8081
 * Checks the Node.js version, adds the right flags, starts the server and opens the browser.
 */
'use strict';
const { spawn, spawnSync, exec } = require('child_process');
const path = require('path');
const fs = require('fs');

const [maj, min] = process.versions.node.split('.').map(Number);
const ok = maj > 22 || (maj === 22 && min >= 5);
if (!ok) {
  console.error(`\n[ERROR] Node.js ${process.versions.node} is too old. Please install Node.js 22 LTS or newer from https://nodejs.org\n`);
  process.exit(1);
}
const flags = ['--no-warnings'];
if (maj === 22 && min < 13) flags.push('--experimental-sqlite');

const demo = process.argv.includes('--demo');
const env = { ...process.env };
env.PORT = env.PORT || (demo ? '8081' : '8080');
if (demo) {
  env.DB_FILE = path.join(__dirname, 'data', 'abc_travel_demo.db');
  if (!fs.existsSync(env.DB_FILE)) {
    console.log('Creating demo database with sample employees and trips...');
    spawnSync(process.execPath, [...flags, path.join(__dirname, 'tools', 'seed_demo_data.js'), env.DB_FILE], { stdio: 'inherit' });
  }
  console.log('\nDEMO MODE - login: admin@abc-demo.com / Demo@1234 (all demo users use Demo@1234)');
}
const url = `http://localhost:${env.PORT}`;
const child = spawn(process.execPath, [...flags, path.join(__dirname, 'server.js')], { env, stdio: 'inherit' });
setTimeout(() => {
  if (process.argv.includes('--no-browser')) return;
  const cmd = process.platform === 'win32' ? `start "" "${url}"` : process.platform === 'darwin' ? `open "${url}"` : `xdg-open "${url}"`;
  exec(cmd, () => {});
}, 1500);
child.on('exit', (code) => process.exit(code || 0));
process.on('SIGINT', () => child.kill('SIGINT'));
