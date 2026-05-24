import { query } from "./lib/db";

async function check() {
  try {
    const res = await query("SELECT COUNT(*) FROM candidate_evaluations");
    console.log("Total responses in DB:", res.rows[0].count);
    
    const sample = await query("SELECT * FROM candidate_evaluations LIMIT 5");
    console.log("Sample rows:", JSON.stringify(sample.rows, null, 2));
  } catch (err) {
    console.error("Error checking DB:", err);
  }
}

check();
