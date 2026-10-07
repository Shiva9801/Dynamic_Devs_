import { ApiResponse } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export async function uploadPrescription(
  file: File,
  accessToken: string
): Promise<ApiResponse> {
  const formData = new FormData();
  formData.append('prescription', file);

  const response = await fetch(`${API_URL}/api/ocr`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });

  const data: ApiResponse = await response.json();
  return data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/api/health`);
    const data = await response.json();
    return data.success === true;
  } catch {
    return false;
  }
}
