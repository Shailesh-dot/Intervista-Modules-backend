import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { supabase, initDb } from "./lib/db";

// Load environment variables from .env.local
dotenv.config({ path: ".env.local" });

const app = express();
const port = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Initialize database
initDb();

app.post("/api/submit", async (req, res) => {
  try {
    const { name, email, answers } = req.body;

    const { data, error } = await supabase
      .from('candidate_evaluations')
      .insert([
        { name, email, answers }
      ])
      .select();

    if (error) {
      console.error("Supabase insert error:", error);
      return res.status(500).json({ message: "Error saving data to Supabase" });
    }

    console.log("Registered candidate evaluation in Supabase:", data[0]);

    res.json({ message: "Saved", data: data[0] });
  } catch (error) {
    console.error("Error saving to Supabase:", error);
    res.status(500).json({ message: "Error saving data" });
  }
});

app.get("/api/responses", async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('candidate_evaluations')
      .select('*')
      .order('submitted_at', { ascending: false });

    if (error) {
       console.error("Supabase fetch error:", error);
       return res.status(500).json({ message: "Error fetching data from Supabase" });
    }
    
    res.json(data);
  } catch (error) {
    console.error("Error fetching responses:", error);
    res.status(500).json({ message: "Error fetching data" });
  }
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
