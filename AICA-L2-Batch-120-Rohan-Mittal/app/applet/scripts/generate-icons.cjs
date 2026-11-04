const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

async function generate() {
  const svgBuffer = fs.readFileSync(path.join(__dirname, "../public/logo.svg"));

  const iconsDir = path.join(__dirname, "../public/icons");
  if (!fs.existsSync(iconsDir)) {
    fs.mkdirSync(iconsDir, { recursive: true });
  }

  await sharp(svgBuffer).resize(192, 192).png().toFile(path.join(iconsDir, "icon-192.png"));

  await sharp(svgBuffer).resize(512, 512).png().toFile(path.join(iconsDir, "icon-512.png"));

  await sharp(svgBuffer).resize(180, 180).png().toFile(path.join(iconsDir, "apple-touch-icon.png"));

  await sharp(svgBuffer).resize(64, 64).png().toFile(path.join(__dirname, "../public/favicon.png"));

  await sharp(svgBuffer).resize(512, 512).png().toFile(path.join(__dirname, "../public/logo.png"));

  console.log("Successfully generated all PNG icons (CommonJS)!");
}

generate().catch((err) => {
  console.error("Error generating icons:", err);
  process.exit(1);
});
