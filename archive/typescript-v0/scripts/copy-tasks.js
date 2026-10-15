const fs = require("node:fs");
const path = require("node:path");

// Copy task JSON files from src/tasks/ to dist/tasks/ so the runtime
// loader (which reads from disk) finds them after `tsc`.
const src = path.join(__dirname, "..", "src", "tasks");
const dest = path.join(__dirname, "..", "dist", "tasks");
fs.mkdirSync(dest, { recursive: true });
for (const f of fs.readdirSync(src)) {
  if (!f.endsWith(".json")) continue;
  fs.copyFileSync(path.join(src, f), path.join(dest, f));
  console.log(`copied task ${f} -> dist/tasks/`);
}

// Also copy the Teach Mode prompt from src/prompts/ to dist/prompts/.
const promptsSrc = path.join(__dirname, "..", "src", "prompts");
const promptsDest = path.join(__dirname, "..", "dist", "prompts");
if (fs.existsSync(promptsSrc)) {
  fs.mkdirSync(promptsDest, { recursive: true });
  for (const f of fs.readdirSync(promptsSrc)) {
    if (!f.endsWith(".md")) continue;
    fs.copyFileSync(path.join(promptsSrc, f), path.join(promptsDest, f));
    console.log(`copied prompt ${f} -> dist/prompts/`);
  }
}
