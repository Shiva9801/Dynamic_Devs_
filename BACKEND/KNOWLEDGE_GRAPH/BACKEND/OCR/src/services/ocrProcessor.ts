import { processOpenRouterOCR } from './openRouterOCR';
import { processGeminiOCR } from './geminiOCR';
import { Medicine, OCRResult, OCRSource } from '../types/ocr';

/**
 * Validates whether an OpenRouter OCR result is reliable enough to accept directly.
 */
function isResultReliable(rawText: string, medicines: Medicine[]): boolean {
  if (!rawText || rawText.trim().length < 10) {
    return false;
  }

  if (!medicines || medicines.length === 0) {
    return false;
  }

  for (const med of medicines) {
    // Missing medicine name or name too short
    if (!med.name || med.name.trim().length < 2) {
      return false;
    }

    // Suspicious default confidence or low confidence
    if (typeof med.confidence === 'number' && med.confidence < 0.75) {
      return false;
    }

    // Suspicious placeholder names
    const lowerName = med.name.toLowerCase();
    if (lowerName.includes('unknown') || lowerName.includes('unreadable') || lowerName.includes('n/a')) {
      return false;
    }
  }

  return true;
}

/**
 * Main OCR Orchestration function.
 * Evaluates primary OpenRouter result, triggers secondary Gemini OCR fallback when needed,
 * compares outputs, and formats clean, safe structured data.
 */
export async function processPrescriptionOCR(imagePath: string, mimeType: string): Promise<OCRResult> {
  let openRouterData;
  let openRouterSuccess = false;

  try {
    openRouterData = await processOpenRouterOCR(imagePath, mimeType);
    openRouterSuccess = true;
  } catch (error: any) {
    console.warn('[OCR Processor] Primary OpenRouter OCR failed or was unavailable:', error.message);
  }

  // Format initial medicine objects from OpenRouter
  const primaryMedicines: Medicine[] = (openRouterData?.medicines || []).map((m) => ({
    name: (m.name || '').trim(),
    dosage: (m.dosage || '').trim() || 'Not specified',
    frequency: (m.frequency || '').trim() || 'Not specified',
    duration: (m.duration || '').trim() || 'Not specified',
    confidence: typeof m.confidence === 'number' ? m.confidence : 0.7,
  }));

  const primaryRawText = openRouterData?.rawText || '';

  // Check if primary OpenRouter result is reliable
  if (openRouterSuccess && isResultReliable(primaryRawText, primaryMedicines)) {
    return {
      rawText: primaryRawText,
      medicines: primaryMedicines,
      ocrSource: 'openrouter',
      requiresConfirmation: false,
    };
  }

  // If primary result is missing or suspicious, run Gemini OCR fallback for verification
  console.log('[OCR Processor] OpenRouter result suspicious or incomplete. Running Gemini verification fallback...');
  const geminiRawText = await processGeminiOCR(imagePath, mimeType);

  const combinedRawText = [
    primaryRawText ? `OpenRouter Text:\n${primaryRawText}` : '',
    geminiRawText ? `Gemini Text:\n${geminiRawText}` : '',
  ]
    .filter(Boolean)
    .join('\n\n');

  // If both engines returned empty or unreadable text
  if (!primaryRawText && !geminiRawText) {
    return {
      rawText: '',
      medicines: [],
      ocrSource: 'uncertain',
      requiresConfirmation: true,
      message: 'The prescription image could not be read clearly by the OCR engine. Please upload a clearer image.',
    };
  }

  // Analyze medicines extracted by OpenRouter against Gemini raw text
  const verifiedMedicines: Medicine[] = [];
  let requiresConfirmation = false;

  for (const med of primaryMedicines) {
    const nameFoundInGemini = geminiRawText.toLowerCase().includes(med.name.toLowerCase());

    if (nameFoundInGemini && med.confidence >= 0.7) {
      // Confirmed by Gemini presence
      verifiedMedicines.push({
        ...med,
        confidence: Math.min(1.0, med.confidence + 0.1),
      });
    } else if (med.confidence < 0.75) {
      // Flag uncertain medicine for user confirmation
      requiresConfirmation = true;
      verifiedMedicines.push({
        name: med.name || 'Uncertain Medicine',
        dosage: med.dosage,
        frequency: med.frequency,
        duration: med.duration,
        confidence: med.confidence,
        possibleMatches: [med.name].filter(Boolean),
      });
    } else {
      verifiedMedicines.push(med);
    }
  }

  // If no medicines could be reliably structured
  if (verifiedMedicines.length === 0) {
    requiresConfirmation = true;
  }

  const ocrSource: OCRSource = openRouterSuccess ? 'openrouter+gemini' : 'uncertain';

  return {
    rawText: combinedRawText,
    medicines: verifiedMedicines,
    ocrSource,
    requiresConfirmation,
    message: requiresConfirmation
      ? 'Some medicine names or details could not be identified reliably. Please review and confirm the extracted data.'
      : undefined,
  };
}
