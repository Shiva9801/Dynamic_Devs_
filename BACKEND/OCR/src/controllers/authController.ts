import { Response } from 'express';
import { AuthenticatedRequest } from '../types/prescription';

export const getCurrentUserHandler = (req: AuthenticatedRequest, res: Response): void => {
  res.status(200).json({
    success: true,
    user: req.user,
  });
};
