// Write the deck colors and the theme name into ppt/theme/*.xml. pptxgenjs writes the stock Office palette,
// and the slides use scheme colors (accent1, dk2, ...), so without this step the deck shows Office colors.
const fs = require("fs");
const JSZip = require("jszip");

const KEYS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

async function applyTheme(file, theme) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const parts = Object.keys(zip.files).filter((n) => /^ppt\/theme\/theme\d+\.xml$/.test(n));
  if (!parts.length) throw new Error(`${file}: no theme part`);
  for (const part of parts) {
    let xml = await zip.file(part).async("string");
    for (const k of KEYS) {
      const v = theme.colors[k];
      if (!/^[0-9A-Fa-f]{6}$/.test(v || "")) throw new Error(`theme color ${k} must be 6 hex digits, got ${v}`);
      const rx = new RegExp(`<a:${k}>[\\s\\S]*?</a:${k}>`);
      if (!rx.test(xml)) throw new Error(`${part}: no <a:${k}>`);
      xml = xml.replace(rx, `<a:${k}><a:srgbClr val="${v.toUpperCase()}"/></a:${k}>`);
    }
    const name = esc(theme.name);
    xml = xml.replace(/(<a:theme\b[^>]*\bname=")[^"]*"/, `$1${name}"`)
      .replace(/(<a:clrScheme\b[^>]*\bname=")[^"]*"/, `$1${name}"`)
      .replace(/(<a:fontScheme\b[^>]*\bname=")[^"]*"/, `$1${name}"`);
    zip.file(part, xml);
  }
  // repack files only: folder entries in a .pptx make some cloud viewers refuse the file
  const out = new JSZip();
  for (const [name, entry] of Object.entries(zip.files)) {
    if (!entry.dir) out.file(name, await entry.async("uint8array"), { date: entry.date, createFolders: false });
  }
  fs.writeFileSync(file, await out.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

module.exports = { applyTheme };
