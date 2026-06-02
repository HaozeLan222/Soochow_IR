import fs from "fs";
import path from "path";

const src = path.resolve("dist");
const dest = path.resolve("../backend/static");

if (!fs.existsSync(src)) {
  console.error("Build output not found. Run 'npm run build' first.");
  process.exit(1);
}

if (fs.existsSync(dest)) {
  fs.rmSync(dest, { recursive: true });
}

fs.cpSync(src, dest, { recursive: true });
console.log(`Copied ${src} → ${dest}`);
