import React from 'react';
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
} from 'lucide-react';

export function Sidebar() {
  const { user } = useAuth();
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
          roles: ['ANALYST', 'ADMIN'],
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
    <aside
      style={{
        width: '240px',
        background: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        padding: '1.25rem 0.75rem',
        flexShrink: 0,
      }}
    >
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
  );
}
