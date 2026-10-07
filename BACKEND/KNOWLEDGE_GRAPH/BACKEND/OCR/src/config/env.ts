import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env file
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

export const env = {
  PORT: process.env.PORT || '5000',
  CLIENT_ORIGIN: process.env.CLIENT_ORIGIN || 'http://localhost:5173',
  OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY || '',
  OPENROUTER_MODEL: process.env.OPENROUTER_MODEL || 'openai/gpt-4o-mini',
  GEMINI_API_KEY: process.env.GEMINI_API_KEY || '',
  SUPABASE_URL: process.env.SUPABASE_URL || '',
  SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY || '',
};

export const validateEnv = (): void => {
  const missingVars: string[] = [];

  if (!env.OPENROUTER_API_KEY || env.OPENROUTER_API_KEY === 'your_openrouter_api_key') {
    missingVars.push('OPENROUTER_API_KEY');
  }

  if (!env.SUPABASE_URL || env.SUPABASE_URL === 'https://your-supabase-project.supabase.co') {
    missingVars.push('SUPABASE_URL');
  }

  if (!env.SUPABASE_SERVICE_ROLE_KEY || env.SUPABASE_SERVICE_ROLE_KEY === 'your_supabase_service_role_key') {
    missingVars.push('SUPABASE_SERVICE_ROLE_KEY');
  }

  if (missingVars.length > 0) {
    console.warn(`[WARNING] The following environment variables are unset or using placeholder values: ${missingVars.join(', ')}`);
  }
};
