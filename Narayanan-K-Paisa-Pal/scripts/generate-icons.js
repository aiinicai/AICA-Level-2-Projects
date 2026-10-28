import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

const publicDir = path.resolve('public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

// Crisp vector SVG for Paisa Pal
const svgStandard = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <rect width="512" height="512" rx="112" fill="#0E7C86" />
  <circle cx="256" cy="256" r="160" fill="#FFFFFF" />
  <!-- Rupee Symbol -->
  <path d="M190 184h132M190 232h132M198 184c60 0 60 72 0 72h-8l90 92" fill="none" stroke="#0E7C86" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" />
  <!-- Notification / Coin spark -->
  <circle cx="392" cy="120" r="48" fill="#F5B15A" stroke="#FFFFFF" stroke-width="12" />
</svg>
`.trim();

// Maskable icon with 15% safe padding
const svgMaskable = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <rect width="512" height="512" fill="#0E7C86" />
  <g transform="translate(64, 64) scale(0.75)">
    <circle cx="256" cy="256" r="170" fill="#FFFFFF" />
    <path d="M190 184h132M190 232h132M198 184c60 0 60 72 0 72h-8l90 92" fill="none" stroke="#0E7C86" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx="392" cy="120" r="48" fill="#F5B15A" stroke="#FFFFFF" stroke-width="12" />
  </g>
</svg>
`.trim();

fs.writeFileSync(path.join(publicDir, 'icon.svg'), svgStandard, 'utf8');

async function buildIcons() {
  const stdBuffer = Buffer.from(svgStandard);
  const maskBuffer = Buffer.from(svgMaskable);

  // 192x192
  await sharp(stdBuffer)
    .resize(192, 192)
    .png()
    .toFile(path.join(publicDir, 'pwa-192x192.png'));

  // 512x512
  await sharp(stdBuffer)
    .resize(512, 512)
    .png()
    .toFile(path.join(publicDir, 'pwa-512x512.png'));

  // 512x512 Maskable
  await sharp(maskBuffer)
    .resize(512, 512)
    .png()
    .toFile(path.join(publicDir, 'pwa-maskable-512x512.png'));

  // Apple touch icon 180x180
  await sharp(stdBuffer)
    .resize(180, 180)
    .png()
    .toFile(path.join(publicDir, 'apple-touch-icon.png'));

  // Favicon 64x64 PNG
  await sharp(stdBuffer)
    .resize(64, 64)
    .png()
    .toFile(path.join(publicDir, 'favicon.png'));

  console.log('All PWA icons successfully generated in /public');
}

buildIcons().catch((err) => {
  console.error(err);
  process.exit(1);
});
