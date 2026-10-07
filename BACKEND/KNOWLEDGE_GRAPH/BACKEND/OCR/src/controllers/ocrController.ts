import { Response, NextFunction } from 'express';
import fs from 'fs';
import { AuthenticatedRequest, PrescriptionResponseData } from '../types/prescription';
import { processPrescriptionOCR } from '../services/ocrProcessor';
import { savePrescriptionRecord } from '../services/prescriptionService';

export const processPrescriptionHandler = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  const file = req.file;

  if (!file) {
    res.status(400).json({
      success: false,
      error: 'No prescription image file uploaded. Please attach a file under key "prescription".',
    });
    return;
  }

  const imagePath = file.path;
  const mimeType = file.mimetype;
  const userId = req.user?.id || 'anonymous-user';

  try {
    // 1. Execute OCR & Validation Pipeline (OpenRouter + Tesseract fallback)
    const ocrResult = await processPrescriptionOCR(imagePath, mimeType);

    // 2. Persist extracted results in Supabase PostgreSQL
    const savedRecord = await savePrescriptionRecord(userId, ocrResult);

    // 3. Format API Response
    const responseData: PrescriptionResponseData = {
      prescriptionId: savedRecord.id || 'unknown',
      ocrSource: ocrResult.ocrSource,
      requiresConfirmation: ocrResult.requiresConfirmation,
      extractedText: ocrResult.rawText,
      medicines: ocrResult.medicines,
    };

    if (ocrResult.message) {
      responseData.message = ocrResult.message;
    }

    res.status(200).json({
      success: true,
      data: responseData,
    });
  } catch (error) {
    next(error);
  } finally {
    // 4. CRITICAL REQUIREMENT: Always delete temporary uploaded image file
    if (imagePath && fs.existsSync(imagePath)) {
      try {
        await fs.promises.unlink(imagePath);
        console.log(`[File Cleanup] Successfully deleted temporary upload file: ${imagePath}`);
      } catch (cleanupError) {
        console.error(`[File Cleanup Error] Failed to delete file ${imagePath}:`, cleanupError);
      }
    }
  }
};
