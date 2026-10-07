export type OCRSource = 'openrouter' | 'openrouter+gemini' | 'uncertain';

export interface Medicine {
  name: string;
  dosage: string;
  frequency: string;
  duration: string;
  confidence: number;
  possibleMatches?: string[];
}

export interface OCRResult {
  rawText: string;
  medicines: Medicine[];
  ocrSource: OCRSource;
  requiresConfirmation: boolean;
  message?: string;
}

export interface OpenRouterExtractedData {
  rawText: string;
  medicines: Array<{
    name?: string;
    dosage?: string;
    frequency?: string;
    duration?: string;
    confidence?: number;
  }>;
}
