import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, Activity, LogOut, User as UserIcon } from 'lucide-react';
import { getReadiness } from '../../api/health';

export function Navbar() {
  const { user, logout } = useAuth();
  const [systemReady, setSystemReady] = useState(null);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await getReadiness();
        setSystemReady(res.status === 'ready');
      } catch (e) {
        setSystemReady(false);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header
      style={{
        height: '64px',
        background: 'var(--bg-sidebar)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        <div
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 12px var(--color-primary-glow)',
          }}
        >
          <Shield size={20} color="#FFFFFF" />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: '1.05rem', letterSpacing: '0.04em', color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            A.R.G.U.S.
            <span style={{ fontSize: '0.65rem', background: 'rgba(59, 130, 246, 0.2)', color: '#93C5FD', padding: '0.1rem 0.4rem', borderRadius: '4px', fontWeight: 700 }}>
              PBL 2026
            </span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Real-Time Fraud Detection & Risk Monitoring
          </div>
        </div>
      </div>

      {/* Right controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        {/* System Readiness Status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.75rem',
            padding: '0.25rem 0.65rem',
            borderRadius: 'var(--radius-full)',
            background: systemReady ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${systemReady ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            color: systemReady ? '#10B981' : '#EF4444',
            fontWeight: 600,
          }}
          title={systemReady ? 'ML Models and PostgreSQL are loaded and serving traffic' : 'Checking readiness...'}
        >
          <Activity size={13} />
          <span>{systemReady === null ? 'CONNECTING' : systemReady ? 'SYSTEM READY' : 'OFFLINE'}</span>
        </div>

        {/* User profile & Role */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'var(--bg-card-hover)',
                  border: '1px solid var(--border-medium)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-secondary)',
                }}
              >
                <UserIcon size={16} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {user.username}
                </span>
                <span className="badge badge-role" style={{ fontSize: '0.65rem', padding: '0.05rem 0.35rem', width: 'fit-content' }}>
                  {user.role}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              className="btn btn-secondary btn-sm"
              title="Sign Out"
              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-muted)' }}
            >
              <LogOut size={14} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
