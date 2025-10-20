/* Updated to use environment variables for security */

// Extract project ID from Supabase URL
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const urlMatch = supabaseUrl.match(/https:\/\/([^.]+)\.supabase\.co/);

export const projectId = import.meta.env.VITE_SUPABASE_PROJECT_ID;
export const publicAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
