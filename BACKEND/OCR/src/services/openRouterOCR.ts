import axios from 'axios';
import fs from 'fs';
import { env } from '../config/env';
import { OpenRouterExtractedData } from '../types/ocr';

const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

export async function processOpenRouterOCR(imagePath: string, mimeType: string): Promise<OpenRouterExtractedData> {
  if (!env.OPENROUTER_API_KEY || env.OPENROUTER_API_KEY === 'your_openrouter_api_key') {
    throw new Error('OpenRouter API key is not configured on the backend server.');
  }

  // Read local image file and convert to base64
  const imageBuffer = await fs.promises.readFile(imagePath);
  const base64Image = imageBuffer.toString('base64');
  const dataUrl = `data:${mimeType};base64,${base64Image}`;

  const prompt = `
You are a specialized medical prescription OCR system.
Examine this prescription image carefully and extract all readable text and medication details.

RULES:
1. Carefully read the entire prescription image.
2. Extract all medicine names, dosage, frequency, and duration.
3. NEVER invent or hallucinate medicine names, dosages, or instructions.
4. Mark uncertain information as uncertain (confidence score below 0.70).
5. If a medicine name is partially illegible, provide your best readable guess and assign a lower confidence score.
6. Preserve the full raw extracted text in the "rawText" field.
7. Return ONLY a valid, raw JSON object (no markdown, no backticks, no markdown fence).

Expected JSON Schema:
{
  "rawText": "full raw text extracted from prescription image",
  "medicines": [
    {
      "name": "Medicine Name",
      "dosage": "500 mg",
      "frequency": "Twice daily",
      "duration": "5 days",
      "confidence": 0.95
    }
  ]
}
`.trim();

  try {
    const response = await axios.post(
      OPENROUTER_URL,
      {
        model: env.OPENROUTER_MODEL,
        messages: [
          {
            role: 'user',
            content: [
              { type: 'text', text: prompt },
              {
                type: 'image_url',
                image_url: {
                  url: dataUrl,
                },
              },
            ],
          },
        ],
        temperature: 0.1,
        response_format: { type: 'json_object' },
      },
      {
        headers: {
          Authorization: `Bearer ${env.OPENROUTER_API_KEY}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': env.CLIENT_ORIGIN,
          'X-Title': 'Polypharmacy Prescription OCR',
        },
        timeout: 30000, // 30s timeout
      }
    );

    const content = response.data?.choices?.[0]?.message?.content;

    if (!content) {
      throw new Error('Received an empty response from OpenRouter OCR model.');
    }

    // Clean potential markdown code blocks if the model wrapped output
    const cleanedContent = content.replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/\s*```$/, '').trim();

    const parsedData: OpenRouterExtractedData = JSON.parse(cleanedContent);

    return {
      rawText: parsedData.rawText || '',
      medicines: Array.isArray(parsedData.medicines) ? parsedData.medicines : [],
    };
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const message = error.response?.data?.error?.message || error.message;
      console.error(`[OpenRouter OCR Error] HTTP ${status}:`, message);
      throw new Error(`OpenRouter OCR service failure: ${message}`);
    }

    if (error instanceof SyntaxError) {
      console.error('[OpenRouter OCR Error] Failed to parse JSON response:', error.message);
      throw new Error('OpenRouter OCR model returned invalid JSON output.');
    }

    console.error('[OpenRouter OCR Error]', error);
    throw new Error(error.message || 'OpenRouter OCR processing failed.');
  }
}
