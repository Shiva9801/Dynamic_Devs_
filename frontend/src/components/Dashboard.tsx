import React, { useState, useRef } from 'react';
import { supabase } from '../lib/supabase';
import { ApiResponse, PrescriptionResult } from '../types';
import { uploadPrescription } from '../services/api';

type UploadStep = 'idle' | 'uploading' | 'processing' | 'saving' | 'done' | 'error';

const STEPS = [
  { id: 'uploading',  label: 'Sending image to server'         },
  { id: 'processing', label: 'Running OpenRouter Vision OCR'   },
  { id: 'saving',     label: 'Saving prescription to Supabase' },
  { id: 'done',       label: 'Results ready'                   },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls = pct >= 85 ? 'confidence-high' : pct >= 65 ? 'confidence-medium' : 'confidence-low';
  return (
    <div className="confidence-bar-wrapper">
      <div className="confidence-label">
        <span>Confidence</span>
        <span>{pct}%</span>
      </div>
      <div className="confidence-bar">
        <div className={`confidence-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [step, setStep] = useState<UploadStep>('idle');
  const [result, setResult] = useState<PrescriptionResult | null>(null);
  const [error, setError] = useState<string>('');
  const [rawExpanded, setRawExpanded] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeStepIndex = STEPS.findIndex(s => s.id === step);

  // Drag & Drop handlers
  const onDragOver  = (e: React.DragEvent) => { e.preventDefault(); setDragActive(true); };
  const onDragLeave = () => setDragActive(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) selectFile(dropped);
  };

  function selectFile(f: File) {
    const allowed = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowed.includes(f.type)) {
      setError('Invalid file format. Please upload JPG, JPEG, PNG, or WEBP.');
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setError('File too large. Maximum size is 5 MB.');
      return;
    }
    setError('');
    setFile(f);
    setResult(null);
  }

  const handleSubmit = async () => {
    if (!file) return;

    setError('');
    setResult(null);

    try {
      // Get session token from Supabase
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        setError('Your session has expired. Please sign in again.');
        return;
      }

      setStep('uploading');
      await delay(400);
      setStep('processing');

      const response: ApiResponse = await uploadPrescription(file, session.access_token);

      setStep('saving');
      await delay(500);

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Processing failed. Please try again.');
      }

      setResult(response.data);
      setStep('done');
    } catch (err: any) {
      setStep('error');
      setError(err.message || 'Something went wrong. Please try again.');
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setStep('idle');
    setError('');
    setRawExpanded(false);
  };

  const isProcessing = ['uploading', 'processing', 'saving'].includes(step);

  return (
    <main className="main-page">
      <div className="container">

        {/* ── Page Header ── */}
        <div className="page-header animate-fade-in-up">
          <div className="page-badge">
            <span>🏥</span> Polypharmacy Safety System
          </div>
          <h1 className="page-title">
            AI Prescription <span className="highlight">OCR Scanner</span>
          </h1>
          <p className="page-description">
            Upload a prescription image to automatically extract medicine names, dosage, frequency, and duration using AI Vision OCR.
          </p>
        </div>

        {/* ── Upload Section ── */}
        {step === 'idle' || step === 'error' ? (
          <div className="upload-section animate-fade-in-up" style={{ animationDelay: '0.1s' }}>

            {error && (
              <div className="alert alert-error">
                <span>⚠️</span>
                <span>{error}</span>
              </div>
            )}

            {/* Drop Zone */}
            <div
              className={`glass upload-zone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              onClick={() => !file && fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.webp"
                className="upload-input"
                onChange={e => { const f = e.target.files?.[0]; if (f) selectFile(f); }}
              />

              {!file ? (
                <>
                  <div className="upload-icon">📋</div>
                  <div className="upload-title">Drop your prescription here</div>
                  <div className="upload-subtitle">or click to browse files</div>
                  <div className="upload-formats">
                    {['JPG', 'JPEG', 'PNG', 'WEBP'].map(fmt => (
                      <span key={fmt} className="format-tag">{fmt}</span>
                    ))}
                    <span style={{ fontSize: '0.75rem', color: 'var(--gray-400)' }}>· Max 5 MB</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="upload-icon" style={{ background: 'rgba(16,185,129,0.15)', borderColor: 'rgba(16,185,129,0.3)' }}>✅</div>
                  <div className="upload-title">Prescription ready</div>
                  <div className="upload-subtitle">Click "Analyze" to extract medicine information</div>
                </>
              )}
            </div>

            {/* File Preview */}
            {file && (
              <div className="file-preview">
                <div className="file-preview-icon">🖼️</div>
                <div className="file-preview-info">
                  <div className="file-preview-name">{file.name}</div>
                  <div className="file-preview-size">{formatBytes(file.size)}</div>
                </div>
                <button className="file-preview-remove" onClick={reset} title="Remove file">✕</button>
              </div>
            )}

            <div className="upload-actions">
              <button
                id="btn-analyze"
                className="btn btn-primary btn-lg btn-block"
                onClick={handleSubmit}
                disabled={!file}
              >
                🔬 Analyze Prescription
              </button>
              {file && (
                <button className="btn btn-ghost btn-block" onClick={reset}>
                  Clear
                </button>
              )}
            </div>
          </div>
        ) : null}

        {/* ── Processing Steps ── */}
        {isProcessing && (
          <div className="processing-card glass animate-fade-in" style={{ maxWidth: 700, margin: '0 auto 32px' }}>
            <div className="processing-header">
              <div className="spinner" />
              <div className="processing-title">Processing prescription…</div>
            </div>
            <div className="steps">
              {STEPS.map((s, i) => {
                const isDone   = i < activeStepIndex || step === 'done';
                const isActive = s.id === step;
                return (
                  <div key={s.id} className={`step ${isActive ? 'active' : isDone ? 'done' : ''}`}>
                    <div className="step-dot">
                      {isDone ? '✓' : isActive ? <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} /> : i + 1}
                    </div>
                    <span>{s.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Results Section ── */}
        {step === 'done' && result && (
          <div className="results-section animate-fade-in-up">

            {/* Header */}
            <div className="results-header">
              <h2 className="results-title">📄 Extraction Results</h2>
              <span className={`ocr-badge ${result.ocrSource === 'openrouter' ? 'badge-openrouter' : result.ocrSource === 'openrouter+tesseract' ? 'badge-fallback' : 'badge-uncertain'}`}>
                {result.ocrSource === 'openrouter' && '✦ OpenRouter AI'}
                {result.ocrSource === 'openrouter+tesseract' && '⚡ AI + Tesseract'}
                {result.ocrSource === 'uncertain' && '⚠ Manual Review Required'}
              </span>
            </div>

            {/* Confirmation Warning */}
            {result.requiresConfirmation && (
              <div className="confirmation-banner alert-warning" style={{ borderRadius: 12 }}>
                <div className="confirmation-icon">⚠️</div>
                <div className="confirmation-text" style={{ color: '#fcd34d' }}>
                  <strong>Manual Confirmation Required</strong>
                  <p>{result.message || 'Some medicines could not be identified reliably. Please review the extracted data below with a pharmacist or physician.'}</p>
                </div>
              </div>
            )}

            {/* Stats Row */}
            <div className="stats-row">
              <div className="stat-card glass">
                <div className="stat-value">{result.medicines.length}</div>
                <div className="stat-label">Medicines Found</div>
              </div>
              <div className="stat-card glass">
                <div className="stat-value" style={{ fontSize: '1rem', marginTop: 6, color: result.requiresConfirmation ? '#fcd34d' : '#6ee7b7' }}>
                  {result.requiresConfirmation ? 'Review' : 'Ready'}
                </div>
                <div className="stat-label">Status</div>
              </div>
              <div className="stat-card glass">
                <div className="stat-value" style={{ fontSize: '0.85rem', marginTop: 6 }}>
                  {result.ocrSource === 'openrouter' ? 'AI Vision' : 'AI + OCR'}
                </div>
                <div className="stat-label">Source</div>
              </div>
            </div>

            {/* Medicines Grid */}
            {result.medicines.length > 0 ? (
              <div className="medicines-grid">
                {result.medicines.map((med, idx) => (
                  <div
                    key={idx}
                    className={`medicine-card glass-solid animate-fade-in-up ${med.possibleMatches ? 'uncertain' : ''}`}
                    style={{ animationDelay: `${idx * 0.08}s` }}
                  >
                    <div className="medicine-name">
                      {med.possibleMatches ? '⚠️ ' : '💊 '}{med.name}
                    </div>
                    {[
                      { label: 'Dosage',     value: med.dosage    },
                      { label: 'Frequency',  value: med.frequency },
                      { label: 'Duration',   value: med.duration  },
                    ].map(d => (
                      <div key={d.label} className="medicine-detail">
                        <span className="medicine-detail-label">{d.label}</span>
                        <span className="medicine-detail-value">{d.value || 'Not specified'}</span>
                      </div>
                    ))}
                    {med.possibleMatches && med.possibleMatches.length > 0 && (
                      <div className="medicine-detail" style={{ marginTop: 4 }}>
                        <span className="medicine-detail-label">Possible</span>
                        <span className="medicine-detail-value" style={{ color: '#fcd34d' }}>
                          {med.possibleMatches.join(', ')}
                        </span>
                      </div>
                    )}
                    <ConfidenceBar value={med.confidence} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="glass empty-medicines" style={{ borderRadius: 16, marginBottom: 24 }}>
                <div className="empty-icon">🔍</div>
                <p>No medicines could be extracted from this prescription.</p>
                <p style={{ fontSize: '0.8rem', marginTop: 6 }}>Please try with a clearer image or consult your pharmacist.</p>
              </div>
            )}

            {/* Raw Extracted Text */}
            {result.extractedText && (
              <div className="raw-text-card glass">
                <div className="raw-text-header">
                  <span className="raw-text-label">📝 Raw Extracted Text</span>
                  <button className="btn btn-ghost btn-sm" onClick={() => setRawExpanded(v => !v)}>
                    {rawExpanded ? 'Hide' : 'Show'}
                  </button>
                </div>
                {rawExpanded && (
                  <div className="raw-text-content animate-fade-in">
                    {result.extractedText}
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="upload-actions" style={{ marginTop: 24 }}>
              <button className="btn btn-primary btn-lg btn-block" onClick={reset}>
                📋 Scan Another Prescription
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
