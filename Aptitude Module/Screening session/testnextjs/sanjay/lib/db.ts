import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

const supabaseUrl = process.env.SUPABASE_URL || '';
const supabaseKey = process.env.SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseKey);

// Disabling initDb because Supabase tables must be managed through migrations or the dashboard SQL editor
export const initDb = async () => {
  console.log("Using Supabase. Ensure 'candidate_evaluations' table is created via the Supabase SQL editor.");
};

export default supabase;
