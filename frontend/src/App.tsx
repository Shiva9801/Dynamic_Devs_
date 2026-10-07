import { useEffect, useState } from 'react';
import { supabase } from './lib/supabase';
import { AuthUser } from './types';
import AuthPage from './components/AuthPage';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import './index.css';

function App() {
  const [user, setUser]       = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session on page load
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser({ id: session.user.id, email: session.user.email });
      }
      setLoading(false);
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser({ id: session.user.id, email: session.user.email });
      } else {
        setUser(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 16,
      }}>
        <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
        <span style={{ color: 'var(--light)', fontSize: '0.9rem' }}>Loading MedScanAI…</span>
      </div>
    );
  }

  if (!user) {
    return <AuthPage onAuth={() => {}} />;
  }

  return (
    <>
      <Navbar user={user} onSignOut={() => setUser(null)} />
      <Dashboard />
      <footer className="footer">
        <p>⚕️ MedScanAI · Polypharmacy Drug Interaction Checker · For healthcare professionals only</p>
      </footer>
    </>
  );
}

export default App;
