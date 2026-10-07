import React, { useState } from 'react';
import { supabase } from '../lib/supabase';

interface AuthPageProps {
  onAuth: () => void;
}

type Tab = 'signin' | 'signup';

export default function AuthPage({ onAuth }: AuthPageProps) {
  const [tab, setTab]         = useState<Tab>('signin');
  const [email, setEmail]     = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      if (tab === 'signin') {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        onAuth();
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMessage('Account created! Check your email for a confirmation link, then sign in.');
        setTab('signin');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card glass animate-fade-in-up">
        {/* Logo */}
        <div className="auth-logo">
          <div className="auth-logo-icon">💊</div>
          <h1 className="auth-title">MedScan<span style={{ color: 'var(--sky)' }}>AI</span></h1>
          <p className="auth-subtitle">Polypharmacy Drug Interaction Checker</p>
        </div>

        {/* Tabs */}
        <div className="auth-tabs">
          <button
            id="tab-signin"
            className={`auth-tab ${tab === 'signin' ? 'active' : ''}`}
            onClick={() => { setTab('signin'); setError(''); setMessage(''); }}
          >
            Sign In
          </button>
          <button
            id="tab-signup"
            className={`auth-tab ${tab === 'signup' ? 'active' : ''}`}
            onClick={() => { setTab('signup'); setError(''); setMessage(''); }}
          >
            Sign Up
          </button>
        </div>

        {/* Alerts */}
        {error   && <div className="alert alert-error"><span>⚠️</span><span>{error}</span></div>}
        {message && <div className="alert alert-success"><span>✅</span><span>{message}</span></div>}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="auth-email" className="form-label">Email Address</label>
            <input
              id="auth-email"
              type="email"
              className="form-input"
              placeholder="doctor@hospital.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="auth-password" className="form-label">Password</label>
            <input
              id="auth-password"
              type="password"
              className="form-input"
              placeholder={tab === 'signup' ? 'Min. 8 characters' : 'Enter your password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={tab === 'signup' ? 8 : 6}
              autoComplete={tab === 'signin' ? 'current-password' : 'new-password'}
            />
          </div>

          <button
            id="btn-auth-submit"
            type="submit"
            className="btn btn-primary btn-lg btn-block"
            disabled={loading}
            style={{ marginTop: 8 }}
          >
            {loading
              ? <><span className="spinner" /> {tab === 'signin' ? 'Signing in…' : 'Creating account…'}</>
              : tab === 'signin' ? '🔑 Sign In' : '🚀 Create Account'
            }
          </button>
        </form>

        <div className="divider" style={{ margin: '24px 0 16px' }} />

        <p style={{ textAlign: 'center', fontSize: '0.78rem', color: 'var(--gray-400)', lineHeight: 1.6 }}>
          🔒 Your prescription data is encrypted and protected.<br />
          This system is for healthcare professionals only.
        </p>
      </div>
    </div>
  );
}
