import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  Terminal,
  History,
  AlertTriangle,
  Radio,
  ShieldAlert,
  Users,
  Menu,
  X,
} from 'lucide-react';

export function Sidebar() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const role = user?.role?.toUpperCase() || 'USER';

  const navItems = [
    {
      label: 'Monitoring',
      items: [
        {
          name: 'Analyst Dashboard',
          path: '/dashboard',
          icon: <LayoutDashboard size={18} />,
          roles: ['ANALYST', 'ADMIN', 'AUDITOR'],
        },
        {
          name: 'Transaction Simulator',
          path: '/simulator',
          icon: <Terminal size={18} />,
          roles: ['USER', 'ANALYST', 'ADMIN'],
        },
        {
          name: 'Transaction History',
          path: '/transactions',
          icon: <History size={18} />,
          roles: ['USER', 'ANALYST', 'ADMIN', 'AUDITOR'],
        },
        {
          name: 'Alerts Queue',
          path: '/alerts',
          icon: <AlertTriangle size={18} />,
          roles: ['ANALYST', 'ADMIN', 'AUDITOR'],
        },
      ],
    },
    {
      label: 'Edge & Hardware',
      items: [
        {
          name: 'IoT Terminal Fleet',
          path: '/devices',
          icon: <Radio size={18} />,
          roles: ['ANALYST', 'ADMIN', 'AUDITOR'],
        },
      ],
    },
    {
      label: 'Governance & Security',
      items: [
        {
          name: 'Security Audit',
          path: '/admin/audit',
          icon: <ShieldAlert size={18} />,
          roles: ['ADMIN', 'AUDITOR'],
        },
        {
          name: 'User Management',
          path: '/admin/users',
          icon: <Users size={18} />,
          roles: ['ADMIN'],
        },
      ],
    },
  ];

  return (
    <>
      <button className="mobile-nav-toggle" onClick={() => setOpen((value) => !value)} aria-label={open ? 'Close navigation' : 'Open navigation'}>
        {open ? <X size={20} /> : <Menu size={20} />}
      </button>
      {open && <button className="mobile-nav-backdrop" onClick={() => setOpen(false)} aria-label="Close navigation" />}
      <aside className={`app-sidebar${open ? ' is-open' : ''}`}>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {navItems.map((group) => {
          const visibleItems = group.items.filter((item) => item.roles.includes(role));
          if (visibleItems.length === 0) return null;

          return (
            <div key={group.label} style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: 'var(--text-muted)',
                  paddingLeft: '0.75rem',
                  marginBottom: '0.2rem',
                }}
              >
                {group.label}
              </span>
              {visibleItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setOpen(false)}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.6rem 0.85rem',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.88rem',
                    fontWeight: 500,
                    color: isActive ? '#FFFFFF' : 'var(--text-secondary)',
                    background: isActive ? 'var(--color-primary)' : 'transparent',
                    boxShadow: isActive ? '0 0 12px var(--color-primary-glow)' : 'none',
                    transition: 'all var(--transition-fast)',
                  })}
                >
                  {item.icon}
                  <span>{item.name}</span>
                </NavLink>
              ))}
            </div>
          );
        })}
      </nav>
      </aside>
    </>
  );
}
