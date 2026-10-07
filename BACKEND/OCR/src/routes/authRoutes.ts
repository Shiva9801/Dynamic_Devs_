import { Router } from 'express';
import { authMiddleware } from '../middleware/authMiddleware';
import { getCurrentUserHandler } from '../controllers/authController';

const router = Router();

// Endpoint to verify authentication status and get current user profile
router.get('/me', authMiddleware, getCurrentUserHandler);

export default router;
