import fs from 'fs';
import path from 'path';
import app from './app';
import { env, validateEnv } from './config/env';

// Validate environment variables on startup
validateEnv();

// Ensure uploads directory exists
const uploadsDir = path.join(__dirname, '../uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const PORT = parseInt(env.PORT, 10) || 5000;

app.listen(PORT, () => {
  console.log(`==================================================`);
  console.log(`🚀 Healthcare Backend Server running on port ${PORT}`);
  console.log(`📡 Health check: http://localhost:${PORT}/api/health`);
  console.log(`🔐 OCR endpoint: POST http://localhost:${PORT}/api/ocr`);
  console.log(`==================================================`);
});
