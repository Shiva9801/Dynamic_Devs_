import axios from 'axios';
import fs from 'fs';
import { env } from '../config/env';

export async function processGeminiOCR(imagePath: string, mimeType: string): Promise<string> {
  if (!env.GEMINI_API_KEY || env.GEMINI_API_KEY === 'your_gemini_api_key') {
    console.warn('[Gemini OCR] GEMINI_API_KEY is not configured. Returning empty string.');
    return '';
  }

  try {
    const imageBuffer = await fs.promises.readFile(imagePath);
    const base64Image = imageBuffer.toString('base64');

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${env.GEMINI_API_KEY}`,
      {
        contents: [
          {
            parts: [
              { text: "Extract all readable text from this prescription image. Return only the raw text." },
              {
                inline_data: {
                  mime_type: mimeType,
                  data: base64Image
                }
              }
            ]
          }
        ]
      },
      {
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 30000 // 30s timeout
      }
    );

    const text = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
    return text ? text.trim() : '';
  } catch (error: any) {
    console.error('[Gemini OCR Error]', error.response?.data || error.message);
    return '';
  }
}
