const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

async function generate() {
  const publicDir = path.join(__dirname, "../public");
  const iconsDir = path.join(publicDir, "icons");

  if (!fs.existsSync(iconsDir)) {
    fs.mkdirSync(iconsDir, { recursive: true });
  }

  const logoSvgPath = path.join(publicDir, "logo.svg");
  const logoSvg = fs.readFileSync(logoSvgPath, "utf8");

  // Extract inner SVG content from public/logo.svg master
  const innerContent = logoSvg
    .replace(/<svg[^>]*>/, "")
    .replace(/<\/svg>/, "")
    .trim();

  // Normal icon SVG with navy #0F2744 rounded square background (rx=25)
  const normalSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" fill="none">
  <rect width="120" height="120" rx="25" fill="#0F2744"/>
  ${innerContent}
</svg>`.trim();

  // Maskable icon SVG with full bleed navy #0F2744 background and artwork centered in circular safe zone (64% scale, translate 21.6)
  const maskableSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" fill="none">
  <rect width="120" height="120" fill="#0F2744"/>
  <g transform="translate(21.6 21.6) scale(0.64)">
    ${innerContent}
  </g>
</svg>`.trim();

  // 1. Vector favicon.svg with navy rx25 background
  fs.writeFileSync(path.join(publicDir, "favicon.svg"), normalSvg);

  // 2. Favicon PNG (64x64)
  await sharp(Buffer.from(normalSvg))
    .resize(64, 64)
    .png()
    .toFile(path.join(publicDir, "favicon.png"));

  // 3. Apple Touch Icon (180x180)
  await sharp(Buffer.from(normalSvg))
    .resize(180, 180)
    .png()
    .toFile(path.join(iconsDir, "apple-touch-icon.png"));

  // 4. PWA Icon 192 (192x192)
  await sharp(Buffer.from(normalSvg))
    .resize(192, 192)
    .png()
    .toFile(path.join(iconsDir, "icon-192.png"));

  // 5. PWA Icon 512 (512x512)
  await sharp(Buffer.from(normalSvg))
    .resize(512, 512)
    .png()
    .toFile(path.join(iconsDir, "icon-512.png"));

  // 6. PWA Maskable Icon 512 (512x512)
  await sharp(Buffer.from(maskableSvg))
    .resize(512, 512)
    .png()
    .toFile(path.join(iconsDir, "icon-maskable-512.png"));

  console.log("All Fair Share icons generated successfully from master logo.svg!");
}

generate().catch((err) => {
  console.error(err);
  process.exit(1);
});
