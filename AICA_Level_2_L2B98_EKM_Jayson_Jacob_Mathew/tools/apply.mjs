// Apply SQL files in order to an in-memory PostgreSQL (PGlite) and print any error with its location.
// usage: node tools/apply.mjs file1.sql file2.sql ...   (paths relative to the project root)
import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const db = new PGlite();
for (const f of process.argv.slice(2)) {
  const sql = readFileSync(resolve(root, f), "utf8");
  try {
    await db.exec(sql);
    console.log("ok   ", f);
  } catch (e) {
    console.log("FAIL ", f, "\n     ", e.message, e.position ? "(position " + e.position + ")" : "");
    if (e.position) {
      const p = Number(e.position);
      console.log("     near:", JSON.stringify(sql.slice(Math.max(0, p - 120), p + 80)));
    }
    process.exit(1);
  }
}
const r = await db.query("select count(*)::int n from information_schema.tables where table_schema='public'");
console.log("public tables:", r.rows[0].n);
