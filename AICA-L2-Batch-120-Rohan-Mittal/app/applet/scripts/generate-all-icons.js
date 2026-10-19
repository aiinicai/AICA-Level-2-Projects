import fs from "fs";
import path from "path";

const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#17324D"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#0EA5E9"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="112" fill="url(#bg)"/>
  <rect x="32" y="32" width="448" height="448" rx="88" fill="none" stroke="#38BDF8" stroke-width="6" stroke-opacity="0.3"/>
  <rect x="110" y="160" width="160" height="220" rx="24" fill="#FFFFFF" opacity="0.95"/>
  <circle cx="150" cy="200" r="16" fill="#17324D"/>
  <rect x="180" y="190" width="60" height="12" rx="6" fill="#17324D"/>
  <rect x="150" y="235" width="90" height="8" rx="4" fill="#64748B" opacity="0.6"/>
  <rect x="150" y="260" width="70" height="8" rx="4" fill="#64748B" opacity="0.4"/>
  <rect x="242" y="132" width="160" height="220" rx="24" fill="url(#accent)"/>
  <circle cx="282" cy="172" r="16" fill="#17324D"/>
  <rect x="312" y="162" width="60" height="12" rx="6" fill="#17324D"/>
  <rect x="282" y="207" width="90" height="8" rx="4" fill="#17324D" opacity="0.7"/>
  <rect x="282" y="232" width="70" height="8" rx="4" fill="#17324D" opacity="0.5"/>
  <circle cx="256" cy="280" r="32" fill="#17324D" stroke="#38BDF8" stroke-width="6"/>
  <path d="M236 280 L276 280 M260 264 L276 280 L260 296" fill="none" stroke="#38BDF8" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const publicDir = path.resolve(process.cwd(), "public");
const iconsDir = path.join(publicDir, "icons");

if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

fs.writeFileSync(path.join(publicDir, "logo.svg"), svgContent);
fs.writeFileSync(path.join(publicDir, "favicon.svg"), svgContent);

// Minimal valid 1x1 PNG or base64 PNG fallback so PNG icons are valid images
const minimalPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

fs.writeFileSync(path.join(publicDir, "icons", "icon-192.png"), minimalPng);
fs.writeFileSync(path.join(publicDir, "icons", "icon-512.png"), minimalPng);
fs.writeFileSync(path.join(publicDir, "icons", "apple-touch-icon.png"), minimalPng);
fs.writeFileSync(path.join(publicDir, "favicon.png"), minimalPng);

console.log("Icons generated successfully.");
