import { createClient, SupabaseClient } from '@supabase/supabase-js/dist/common';
import { env } from './env';

const supabaseUrl = env.SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseServiceRoleKey = env.SUPABASE_SERVICE_ROLE_KEY || 'placeholder_key';

export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseServiceRoleKey, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
  },
});
