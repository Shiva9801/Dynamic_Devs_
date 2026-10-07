import { Request } from 'express';
import { Medicine, OCRSource } from './ocr';

export interface PrescriptionRecord {
  id?: string;
  user_id: string;
  extracted_text: string;
  medicines: Medicine[];
  ocr_source: OCRSource;
  requires_confirmation: boolean;
  created_at?: string;
}

export interface PrescriptionResponseData {
  prescriptionId: string;
  ocrSource: OCRSource;
  requiresConfirmation: boolean;
  extractedText: string;
  medicines: Medicine[];
  message?: string;
}

export interface AuthenticatedUser {
  id: string;
  email?: string;
}

export interface AuthenticatedRequest extends Request {
  user?: AuthenticatedUser;
  file?: Express.Multer.File;
}
