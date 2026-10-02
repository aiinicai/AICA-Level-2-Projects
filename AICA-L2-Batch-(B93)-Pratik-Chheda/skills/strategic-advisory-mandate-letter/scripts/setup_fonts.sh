#!/usr/bin/env bash
# Maps "Book Antiqua" to a metric compatible Palatino clone for PDF rendering
# in Linux environments that do not ship Book Antiqua. The docx itself still
# names Book Antiqua, so Word renders the true font.
set -e
mkdir -p ~/.config/fontconfig
PAGELLA_DIR=$(fc-list | grep -i "TeX Gyre Pagella" | head -1 | cut -d: -f1 | xargs dirname 2>/dev/null || true)
if [ -n "$PAGELLA_DIR" ]; then
  mkdir -p ~/.fonts && cp "$PAGELLA_DIR"/texgyrepagella-*.otf ~/.fonts/ 2>/dev/null || true
fi
cat > ~/.config/fontconfig/fonts.conf << 'XML'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <alias binding="same">
    <family>Book Antiqua</family>
    <prefer><family>TeX Gyre Pagella</family><family>P052</family><family>URW Palladio L</family></prefer>
  </alias>
</fontconfig>
XML
fc-cache -f >/dev/null 2>&1 || true
fc-match "Book Antiqua"
