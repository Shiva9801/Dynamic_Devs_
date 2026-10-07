import { Response, NextFunction } from 'express';
import { supabase } from '../config/supabase';
import { AuthenticatedRequest } from '../types/prescription';

export const authMiddleware = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({
        success: false,
        error: 'Unauthorized. Missing or invalid Authorization header format (expected: Bearer <token>).',
      });
      return;
    }

    const token = authHeader.split(' ')[1];

    if (!token) {
      res.status(401).json({
        success: false,
        error: 'Unauthorized. Access token is missing.',
      });
      return;
    }

    // Verify token with Supabase Auth
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      res.status(401).json({
        success: false,
        error: 'Unauthorized. Invalid or expired token.',
      });
      return;
    }

    // Attach user information to request
    req.user = {
      id: user.id,
      email: user.email,
    };

    next();
  } catch (error) {
    res.status(401).json({
      success: false,
      error: 'Unauthorized. Authentication check failed.',
    });
  }
};
