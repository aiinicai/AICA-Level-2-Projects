const fs = require('fs');
const path = require('path');

const distPath = path.join(__dirname, 'dist');
const htmlPath = path.join(distPath, 'index.html');

let html = fs.readFileSync(htmlPath, 'utf8');

// Find CSS file in dist/assets
const assetsDir = path.join(distPath, 'assets');
const files = fs.readdirSync(assetsDir);

const cssFile = files.find(f => f.endsWith('.css'));
const jsFile = files.find(f => f.endsWith('.js'));

if (cssFile && jsFile) {
  const cssContent = fs.readFileSync(path.join(assetsDir, cssFile), 'utf8');
  let jsContent = fs.readFileSync(path.join(assetsDir, jsFile), 'utf8');

  // Safely escape </script> sequences inside JS string literals to avoid prematurely breaking HTML parser
  jsContent = jsContent.replace(/<\/script/gi, '<\\/script');

  // Replace CSS tag with inline <style> in <head>
  html = html.replace(/<link[^>]*stylesheet[^>]*>/i, () => `<style>${cssContent}</style>`);
  
  // Remove the script tag from <head>
  html = html.replace(/<script[^>]*src="[^"]*"[^>]*><\/script>/i, '');

  // Place inline script at the bottom of <body> AFTER <div id="root"></div>
  html = html.replace('</body>', () => `<script>${jsContent}</script>\n</body>`);

  const outputPath = path.join(__dirname, 'GrantSetu_Shareable_Offline.html');
  fs.writeFileSync(outputPath, html, 'utf8');

  console.log('Successfully created GrantSetu_Shareable_Offline.html');
  console.log('File Path:', outputPath);
  console.log('File Size:', (fs.statSync(outputPath).size / 1024).toFixed(1) + ' KB');
} else {
  console.error('CSS or JS bundle file not found in dist/assets');
}
