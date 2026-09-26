import fs from 'fs';
import path from 'path';
import sharp from 'sharp';

const publicDir = path.resolve('public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

// Crisp modern SVG icon with emerald green gradient and Rupee + Sparkle / Chart
const svgIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#059669" />
      <stop offset="50%" stop-color="#10b981" />
      <stop offset="100%" stop-color="#047857" />
    </linearGradient>
    <linearGradient id="glyph" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="100%" stop-color="#ecfdf5" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#022c22" flood-opacity="0.25"/>
    </filter>
  </defs>
  
  <!-- Rounded Base Plate -->
  <rect x="32" y="32" width="448" height="448" rx="104" fill="url(#bg)" filter="url(#shadow)"/>
  
  <!-- Subtle inner card pattern -->
  <rect x="64" y="64" width="384" height="384" rx="80" fill="none" stroke="#ffffff" stroke-width="4" stroke-opacity="0.2"/>

  <!-- Indian Rupee + Growth Line Hybrid -->
  <g fill="none" stroke="url(#glyph)" stroke-width="32" stroke-linecap="round" stroke-linejoin="round">
    <!-- Rupee Top Bars -->
    <path d="M192 168h128" />
    <path d="M192 216h128" />
    <!-- Rupee Loop & Leg -->
    <path d="M192 168c64 0 96 32 96 68 0 44-48 64-96 64" />
    <path d="M228 300l84 100" />
    <path d="M192 144v170" />
  </g>
  
  <!-- AI Sparkle / Star in top right -->
  <path d="M370 140c0 18 14 32 32 32-18 0-32 14-32 32 0-18-14-32-32-32 18 0 32-14 32-32z" fill="#fef08a" />
  <circle cx="340" cy="190" r="6" fill="#fef08a" />
</svg>`;

// Maskable SVG with safe margin (central 80% circle safe zone)
const maskableSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bgMask" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#059669" />
      <stop offset="100%" stop-color="#047857" />
    </linearGradient>
  </defs>
  <!-- Full bleed background -->
  <rect width="512" height="512" fill="url(#bgMask)"/>
  
  <!-- Scaled down to safe 75% center -->
  <g transform="translate(64, 64) scale(0.75)">
    <g fill="none" stroke="#ffffff" stroke-width="32" stroke-linecap="round" stroke-linejoin="round">
      <path d="M192 168h128" />
      <path d="M192 216h128" />
      <path d="M192 168c64 0 96 32 96 68 0 44-48 64-96 64" />
      <path d="M228 300l84 100" />
      <path d="M192 144v170" />
    </g>
    <path d="M370 140c0 18 14 32 32 32-18 0-32 14-32 32 0-18-14-32-32-32 18 0 32-14 32-32z" fill="#fef08a" />
  </g>
</svg>`;

async function run() {
  fs.writeFileSync(path.join(publicDir, 'icon.svg'), svgIcon, 'utf8');

  const svgBuffer = Buffer.from(svgIcon);
  const maskableBuffer = Buffer.from(maskableSvg);

  await sharp(svgBuffer).resize(180, 180).png().toFile(path.join(publicDir, 'apple-touch-icon.png'));
  await sharp(svgBuffer).resize(192, 192).png().toFile(path.join(publicDir, 'pwa-192x192.png'));
  await sharp(svgBuffer).resize(512, 512).png().toFile(path.join(publicDir, 'pwa-512x512.png'));
  await sharp(maskableBuffer).resize(512, 512).png().toFile(path.join(publicDir, 'pwa-maskable-512x512.png'));
  await sharp(svgBuffer).resize(48, 48).png().toFile(path.join(publicDir, 'favicon.ico'));

  console.log('PWA icons created successfully in /public');
}

run().catch(console.error);
