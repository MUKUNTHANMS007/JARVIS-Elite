import { createClient } from '@supabase/supabase-js';

// JARVIS Sentinel Cloud Mirror: Credentials for global telemetry.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
