// After `vite build --mode file`: writes "Vouchr demo.html" (one file, opens from a folder) with the icon embedded.
import { readFileSync, writeFileSync } from 'node:fs';
const html = readFileSync('dist-file/index.html', 'utf8');
const icon = `data:image/svg+xml;base64,${readFileSync('public/icon.svg').toString('base64')}`;
writeFileSync('Vouchr demo.html', html.replaceAll('href="./icon.svg"', `href="${icon}"`));
console.log('Vouchr demo.html written');
