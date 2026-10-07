import express, { Application, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { env } from './config/env';
import ocrRoutes from './routes/ocrRoutes';
import authRoutes from './routes/authRoutes';
import { errorMiddleware } from './middleware/errorMiddleware';

const app: Application = express();

// Configure CORS for frontend origin
app.use(
  cors({
    origin: [env.CLIENT_ORIGIN, 'http://localhost:5173', 'http://localhost:3000'],
    credentials: true,
  })
);

// Express middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health Check Endpoint (Public)
app.get('/api/health', (_req: Request, res: Response) => {
  res.status(200).json({
    success: true,
    message: 'Backend is running',
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/ocr', ocrRoutes);

// Handle 404 - Not Found
app.use((_req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: 'API endpoint not found',
  });
});

// Central Error Handling Middleware
app.use(errorMiddleware);

export default app;
