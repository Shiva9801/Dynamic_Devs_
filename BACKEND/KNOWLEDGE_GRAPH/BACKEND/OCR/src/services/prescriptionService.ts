import { supabase } from '../config/supabase';
import { OCRResult } from '../types/ocr';
import { PrescriptionRecord } from '../types/prescription';

export async function savePrescriptionRecord(
  userId: string,
  ocrResult: OCRResult
): Promise<PrescriptionRecord> {
  const newRecord: PrescriptionRecord = {
    user_id: userId,
    extracted_text: ocrResult.rawText,
    medicines: ocrResult.medicines,
    ocr_source: ocrResult.ocrSource,
    requires_confirmation: ocrResult.requiresConfirmation,
  };

  try {
    const { data, error } = await supabase
      .from('prescriptions')
      .insert([newRecord])
      .select()
      .single();

    if (error) {
      console.error('[Supabase DB Error] Failed to insert prescription record:', error.message);
      // Fallback with client generated timestamp / fallback ID if DB schema is pending execution
      return {
        ...newRecord,
        id: `local-temp-${Date.now()}`,
        created_at: new Date().toISOString(),
      };
    }

    return data as PrescriptionRecord;
  } catch (err: any) {
    console.error('[Prescription Service Error]', err.message || err);
    return {
      ...newRecord,
      id: `local-temp-${Date.now()}`,
      created_at: new Date().toISOString(),
    };
  }
}
