import { Request, Response, NextFunction } from 'express';
import multer from 'multer';

export interface AppError extends Error {
  statusCode?: number;
}

export const errorMiddleware = (
  err: AppError,
  _req: Request,
  res: Response,
  _next: NextFunction
): void => {
  console.error('[ERROR]', err);

  // Handle Multer errors
  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      res.status(400).json({
        success: false,
        error: 'File too large. Maximum allowed size is 5 MB.',
      });
      return;
    }

    res.status(400).json({
      success: false,
      error: `File upload error: ${err.message}`,
    });
    return;
  }

  // Handle standard app errors with custom status code or default to 500
  const statusCode = err.statusCode || 400;
  const message = err.message || 'An unexpected server error occurred.';

  res.status(statusCode).json({
    success: false,
    error: message,
  });
};
