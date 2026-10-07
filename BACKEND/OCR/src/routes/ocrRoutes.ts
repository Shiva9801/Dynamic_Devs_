import { Router } from 'express';
import { authMiddleware } from '../middleware/authMiddleware';
import { uploadPrescription } from '../middleware/uploadMiddleware';
import { processPrescriptionHandler } from '../controllers/ocrController';

const router = Router();

// Protected OCR endpoint for processing prescription images
// Require authentication & handle multipart form-data upload
router.post('/', authMiddleware, uploadPrescription, processPrescriptionHandler);

export default router;
