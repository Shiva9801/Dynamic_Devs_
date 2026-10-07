export interface Medicine {
  name: string;
  dosage: string;
  frequency: string;
  duration: string;
  confidence: number;
  possibleMatches?: string[];
}

export interface PrescriptionResult {
  prescriptionId: string;
  ocrSource: 'openrouter' | 'openrouter+tesseract' | 'uncertain';
  requiresConfirmation: boolean;
  extractedText: string;
  medicines: Medicine[];
  message?: string;
}

export interface ApiResponse {
  success: boolean;
  data?: PrescriptionResult;
  error?: string;
}

export interface AuthUser {
  id: string;
  email?: string;
}

// Runtime sentinel — keeps this module non-empty after TypeScript compilation
// so Vite's ESM module graph can resolve named exports correctly.
export const TYPES_VERSION = '1.0.0';
