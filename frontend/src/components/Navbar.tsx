import React from 'react';
import { AuthUser } from '../types';
import { supabase } from '../lib/supabase';

interface NavbarProps {
  user: AuthUser | null;
  onSignOut: () => void;
}

export default function Navbar({ user, onSignOut }: NavbarProps) {
  const initials = user?.email ? user.email[0].toUpperCase() : '?';

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    onSignOut();
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <a href="/" className="navbar-brand">
          <div className="brand-icon">💊</div>
          <span className="brand-name">
            MedScan<span>AI</span>
          </span>
        </a>

        {/* Actions */}
        <div className="navbar-actions">
          {user && (
            <>
              <div className="navbar-user">
                <div className="avatar">{initials}</div>
                <span style={{ display: 'none' }} id="user-email">{user.email}</span>
              </div>
              <button
                id="btn-signout"
                className="btn btn-ghost btn-sm"
                onClick={handleSignOut}
              >
                Sign Out
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
